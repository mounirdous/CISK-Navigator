"""
Standalone HTML Export Service — captures the LIVE workspace page and turns
it into a single self-contained .html file.

Strategy:
  1. Invoke workspace.index() in the current request context — same template,
     same Alpine.js wiring, same look as the live app.
  2. Inline all `/static/...` CSS and JS into <style> / <script> blocks so the
     file does not need access to the Flask static server.
  3. Embed the workspace data (the dict returned by /workspace/data) and
     install a fetch() interceptor that serves it on first AJAX call — so
     Alpine.js initialises identically without ever hitting the network.
  4. Stub other backend AJAX calls (saved searches, mentions, preferences,
     action-items count, etc.) with empty JSON so the page renders without
     console errors.
  5. CDN-hosted libraries (Bootstrap, Bootstrap Icons, Alpine) stay as CDN
     links — recipients online get the exact same look; offline they would
     fall back gracefully (Bootstrap absent → still readable, just unstyled).
  6. Form submissions are intercepted and prevented; "edit" / "contribute"
     interactions are visually present but no-op.
"""

import json
import os
import re
from io import BytesIO


def _render_panel(template, **ctx):
    """Render a live page template and return ONLY its <style> blocks (from
    {% block extra_css %}) concatenated with the {% block content %} body —
    suitable for dropping straight into a modal via innerHTML.

    Strategy: render the full page, then string-slice it to keep only the
    pieces we want, dropping <html>/<head>/<nav>/<footer>/<script>. The
    rendered styles inside <head> stay with us so the panel keeps its
    bespoke colors / icons / list bullets.
    """
    from flask import render_template

    full = render_template(template, **ctx)

    # 1. Pull every <style> block out of <head>.
    styles = ""
    head_match = re.search(r"<head[^>]*>(.*?)</head>", full, re.DOTALL | re.IGNORECASE)
    head_blob = head_match.group(1) if head_match else ""
    for m in re.finditer(r"<style\b[^>]*>.*?</style>", head_blob, re.DOTALL | re.IGNORECASE):
        styles += m.group(0) + "\n"

    # 2. Find the content wrapper. base.html wraps {% block content %} in
    #    <div class="container-fluid mt-4">.
    marker = '<div class="container-fluid mt-4">'
    start = full.find(marker)
    if start < 0:
        return styles + full

    # Walk forward to find the matching </div> by counting depth.
    depth = 0
    i = start
    n = len(full)
    end = -1
    div_open = re.compile(r"<div\b", re.IGNORECASE)
    div_close = re.compile(r"</div>", re.IGNORECASE)
    pos = start
    while pos < n:
        next_open = div_open.search(full, pos)
        next_close = div_close.search(full, pos)
        if not next_close:
            break
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
            if depth == 0:
                end = pos
                break
    if end < 0:
        return styles + full[start:]

    content = full[start:end]
    # Strip any inline <script> tags inside content — we want pure markup, not
    # the page's JS (it would not work anyway, fetched data isn't there).
    content = re.sub(r"<script\b[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    return styles + content


def _read_static(rel_path):
    """Read a file under app/static. rel_path may have leading /static/ or not."""
    from flask import current_app
    static_root = current_app.static_folder
    if not static_root:
        return None
    rel = rel_path
    for prefix in ("/static/", "static/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
    full = os.path.normpath(os.path.join(static_root, rel))
    if not full.startswith(os.path.normpath(static_root)):
        return None
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _inline_local_assets(html):
    """Replace <link href=/static/...> and <script src=/static/...> with inline blocks."""
    def inline_css(match):
        href = match.group("href")
        contents = _read_static(href)
        if contents is None:
            return match.group(0)
        return f'<style data-from="{href}">\n{contents}\n</style>'

    def inline_js(match):
        src = match.group("src")
        contents = _read_static(src)
        if contents is None:
            return match.group(0)
        return f'<script data-from="{src}">\n{contents}\n</script>'

    # Match <link rel="stylesheet" href="/static/...">  or  href first then rel — both common
    css_re = re.compile(
        r'<link\b(?=[^>]*rel=["\']stylesheet["\'])(?=[^>]*href=["\'](?P<href>/static/[^"\']+)["\'])[^>]*/?>',
        re.IGNORECASE,
    )
    # Sometimes attribute order is different — second pass with relaxed matcher
    css_re_alt = re.compile(
        r'<link\b[^>]*href=["\'](?P<href>/static/[^"\']+)["\'][^>]*rel=["\']stylesheet["\'][^>]*/?>',
        re.IGNORECASE,
    )
    html = css_re.sub(inline_css, html)
    html = css_re_alt.sub(inline_css, html)

    js_re = re.compile(
        r'<script\b[^>]*\bsrc=["\'](?P<src>/static/[^"\']+)["\'][^>]*></script>',
        re.IGNORECASE,
    )
    html = js_re.sub(inline_js, html)
    return html


def _inject_shim(html, workspace_data, *, snapshot_meta=None, base_url=None, extras=None):
    """Inject an early <script> that fakes the network for /workspace/data and friends."""
    blob = json.dumps(workspace_data, default=str, ensure_ascii=False).replace("</", "<\\/")
    meta = json.dumps(snapshot_meta or {}, default=str, ensure_ascii=False).replace("</", "<\\/")
    extras_blob = json.dumps(extras or {}, default=str, ensure_ascii=False).replace("</", "<\\/")

    # <base href> makes every relative href / src in the rendered page resolve
    # against the live deployment, so clicking "Porter's", "SWOT", "Strategy",
    # "Lenses (dimensions)", entity edit links etc. opens them in the live app.
    base_tag = ""
    if base_url:
        base_tag = '<base href="' + base_url.rstrip('/') + '/">\n'

    # Hide chrome that doesn't make sense in a static snapshot.
    snapshot_css = """<style data-snapshot-css="1">
/* Top app navbar — irrelevant in a static snapshot */
.navbar, nav.navbar, .ga-subnav { display: none !important; }
body { padding-top: 0 !important; }
/* Filter / saved-view preset bar (load/save presets) */
.preset-bar, .preset-bar-inner, [class*="preset-bar"], #ws-presets-bar { display: none !important; }
/* Edit-mode toggle (and the entire edit-mode-only UI is also hidden by
   forcing editMode=false on the Alpine root in the shim below). */
#wsEditModeBtn, .ws-edit-mode-toggle { display: none !important; }
/* Snapshot floating controls (export buttons, snapshot creator) */
.snapshot-controls { display: none !important; }
/* Inline quick-add value modal (server write) — never let it open */
.ws-iadd-overlay, .ws-iadd-modal, [class*="ws-iadd"] { display: none !important; }
/* Comments / mentions UI is server-bound */
.comments-panel, #commentsPanel, [class*="comments-section"] { display: none !important; }
/* Maintenance / feedback banners that depend on backend state */
.maintenance-banner, #maintenanceBanner { display: none !important; }
/* Live search results (search box dropdown, mentions, link health) */
.live-search-results, .global-search-dropdown { display: none !important; }
</style>
"""

    shim = """<script data-snapshot-shim="1">
window.__SNAPSHOT_MODE__ = true;
window.__SNAPSHOT_DATA__ = """ + blob + """;
window.__SNAPSHOT_META__ = """ + meta + """;
window.__SNAPSHOT_EXTRAS__ = """ + extras_blob + """;
(function() {
  // Intercept fetch — workspace/data returns the embedded snapshot, all other
  // /api/ /workspace/api/ /global-admin/api/ endpoints return empty 200 JSON
  // so the page can boot without backend errors.
  var _origFetch = window.fetch;
  function snapshotResponse(body) {
    return new Response(typeof body === 'string' ? body : JSON.stringify(body),
      { status: 200, headers: { 'Content-Type': 'application/json' } });
  }
  window.fetch = function(input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    try {
      if (/\\/workspace\\/data(?:\\?|$)/.test(url)) {
        return Promise.resolve(snapshotResponse(window.__SNAPSHOT_DATA__));
      }
      // Stub all GET-shaped read APIs and writes
      if (/\\/(workspace|global-admin|org-admin|auth|presets)\\/api\\b/.test(url)
          || /\\/api\\b/.test(url)
          || /\\/workspace\\/contribute/.test(url)
          || /\\/workspace\\/api\\b/.test(url)) {
        return Promise.resolve(snapshotResponse('{}'));
      }
    } catch (e) { /* fall through */ }
    return _origFetch.apply(this, arguments);
  };
  // Block form submissions — this is a snapshot, no writes go anywhere.
  document.addEventListener('submit', function(e) {
    var form = e.target;
    if (form && form.tagName === 'FORM') {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  }, true);
  // Suppress unload prompts (some pages ask before navigating away)
  window.addEventListener('beforeunload', function(e) { e.stopImmediatePropagation(); }, true);
  // ── In-page modals for Porter / Strategy / Lenses / SWOT ─────────────
  // Intercepts clicks on the corresponding live-app links and renders the
  // content from the embedded data instead of navigating away.
  function _esc(s) { return (s == null ? '' : String(s))
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;'); }
  function _findSpace(spaceId) {
    var ws = window.__SNAPSHOT_DATA__ || {};
    spaceId = String(spaceId);
    for (var i = 0; i < (ws.spaces||[]).length; i++) {
      if (String(ws.spaces[i].id) === spaceId) return ws.spaces[i];
    }
    return null;
  }
  function _modal(title, bodyHtml) {
    var existing = document.getElementById('__snap_modal__');
    if (existing) existing.remove();
    var bk = document.createElement('div');
    bk.id = '__snap_modal__';
    bk.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.55);'
      + 'z-index:100000;display:flex;align-items:center;justify-content:center;padding:24px;';
    bk.innerHTML = ''
      + '<div style="background:#fff;color:#0f172a;border-radius:12px;'
      +              'box-shadow:0 20px 60px rgba(0,0,0,.35);max-width:1100px;width:96%;'
      +              'max-height:90vh;overflow:auto;padding:22px 26px;'
      +              'font:14px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;">'
      +   '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
      +     '<h3 style="margin:0;font-size:18px;flex:1 1 auto">' + _esc(title) + '</h3>'
      +     '<button id="__snap_modal_close__" style="background:transparent;border:0;'
      +             'font-size:22px;color:#64748b;cursor:pointer;line-height:1;">&times;</button>'
      +   '</div>'
      +   '<div id="__snap_modal_body__">' + bodyHtml + '</div>'
      + '</div>';
    document.body.appendChild(bk);
    function close() { bk.remove(); document.removeEventListener('keydown', keyClose); }
    function keyClose(e) { if (e.key === 'Escape') close(); }
    bk.addEventListener('click', function(e) { if (e.target === bk) close(); });
    document.getElementById('__snap_modal_close__').addEventListener('click', close);
    document.addEventListener('keydown', keyClose);
  }
  // Each of these prefers the server-pre-rendered panel HTML (which mirrors
  // the live page exactly — same colors, gradients, icons, list bullets).
  // Falls back to a hand-built minimal version only if the panel was missing.
  function _panel(key) { return ((window.__SNAPSHOT_EXTRAS__ || {}).panels || {})[key]; }
  function _portersHtml() {
    var rendered = _panel('porters');
    if (rendered) return rendered;
    var p = (window.__SNAPSHOT_EXTRAS__ || {}).porters || {};
    var sec = function(label, val) {
      return '<div style="margin-bottom:14px"><div style="font-size:11px;'
        + 'text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:4px">'
        + _esc(label) + '</div><div style="white-space:pre-wrap">'
        + (val ? _esc(val) : '<em style="color:#94a3b8">Not configured.</em>')
        + '</div></div>';
    };
    return sec('Threat of new entrants',           p.new_entrants)
         + sec('Bargaining power of suppliers',    p.suppliers)
         + sec('Bargaining power of buyers',       p.buyers)
         + sec('Threat of substitutes',            p.substitutes)
         + sec('Competitive rivalry',              p.rivalry);
  }
  function _strategyHtml() {
    var rendered = _panel('strategy');
    if (rendered) return rendered;
    var pillars = (window.__SNAPSHOT_EXTRAS__ || {}).pillars || [];
    if (!pillars.length) return '<p style="color:#64748b">No strategic pillars defined.</p>';
    return pillars.map(function(p) {
      var c = p.accent_color || '#0d6efd';
      return '<div style="border-left:4px solid ' + _esc(c) + ';padding:6px 12px;margin-bottom:12px">'
        + '<div style="font-weight:700;color:' + _esc(c) + '">' + _esc(p.name) + '</div>'
        + '<div style="white-space:pre-wrap">' + _esc(p.description || '') + '</div>'
        + '</div>';
    }).join('');
  }
  function _lensesHtml() {
    var rendered = _panel('dimensions');
    if (rendered) return rendered;
    var vts = ((window.__SNAPSHOT_DATA__ || {}).valueTypes || []);
    if (!vts.length) return '<p style="color:#64748b">No lenses configured.</p>';
    return vts.map(function(v) {
      return '<div style="padding:8px 10px;border-bottom:1px solid #e5e7eb">'
        + '<strong>' + _esc(v.name) + '</strong> '
        + '<span style="color:#64748b">' + _esc(v.kind || '') + '</span>'
        + (v.unit_label ? ' · ' + _esc(v.unit_label) : '')
        + '</div>';
    }).join('');
  }
  function _swotHtml(spaceId) {
    var rendered = (((window.__SNAPSHOT_EXTRAS__ || {}).panels || {}).swot || {})[spaceId]
                || (((window.__SNAPSHOT_EXTRAS__ || {}).panels || {}).swot || {})[String(spaceId)];
    if (rendered) return rendered;
    // Fallback: minimal hand-built layout from the SWOT extras dict.
    var sw = (((window.__SNAPSHOT_EXTRAS__ || {}).swot) || {})[spaceId]
          || (((window.__SNAPSHOT_EXTRAS__ || {}).swot) || {})[String(spaceId)];
    if (!sw) {
      var sp = _findSpace(spaceId);
      if (!sp) return '<p style="color:#64748b">Space not found in snapshot.</p>';
      sw = {
        name: sp.name,
        strengths:     sp.swot_strengths,
        weaknesses:    sp.swot_weaknesses,
        opportunities: sp.swot_opportunities,
        threats:       sp.swot_threats,
      };
    }
    var cell = function(h, v, bg, fg) {
      return '<div style="background:' + bg + ';color:' + fg + ';border-radius:8px;'
        + 'padding:10px 12px;white-space:pre-wrap;font-size:13px">'
        + '<div style="font-size:10px;font-weight:700;letter-spacing:.06em;'
        + 'text-transform:uppercase;opacity:.85;margin-bottom:4px">' + h + '</div>'
        + (v ? _esc(v) : '<em style="opacity:.7">—</em>') + '</div>';
    };
    return (sw.name ? '<div style="font-weight:600;margin-bottom:10px">' + _esc(sw.name) + '</div>' : '')
      + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
      + cell('Strengths',     sw.strengths,     '#dcfce7', '#14532d')
      + cell('Weaknesses',    sw.weaknesses,    '#fee2e2', '#7f1d1d')
      + cell('Opportunities', sw.opportunities, '#dbeafe', '#1e3a8a')
      + cell('Threats',       sw.threats,       '#fef3c7', '#78350f')
      + '</div>';
  }
  document.addEventListener('click', function(e) {
    var a = e.target.closest('a');
    if (!a) return;
    var raw = a.getAttribute('href') || '';
    if (!raw) return;
    var swotMatch = raw.match(/\\/spaces\\/(\\d+)\\/swot/);
    if (/\\/org-admin\\/(?:porters|porter)/.test(raw)) {
      e.preventDefault(); _modal("Porter's Five Forces", _portersHtml()); return;
    }
    if (/\\/(?:workspace\\/)?strategy(?:\\b|\\/)/.test(raw)) {
      e.preventDefault(); _modal('Strategic Pillars', _strategyHtml()); return;
    }
    if (/\\/(?:workspace\\/)?dimensions(?:\\b|\\/)/.test(raw)) {
      e.preventDefault(); _modal('Lenses', _lensesHtml()); return;
    }
    if (swotMatch) {
      e.preventDefault(); _modal('SWOT', _swotHtml(swotMatch[1])); return;
    }
  }, true);

  // Force Alpine's workspace state out of edit-mode on every boot; if the page
  // restored editMode=true from localStorage we override it.
  document.addEventListener('alpine:init', function() {
    try {
      // No-op — we'll patch the root after init
    } catch (e) {}
  });
  document.addEventListener('DOMContentLoaded', function() {
    try {
      // Walk Alpine roots and force editMode = false on workspaceV2 components.
      document.querySelectorAll('[x-data]').forEach(function(el) {
        if (el.__x && el.__x.$data && 'editMode' in el.__x.$data) {
          el.__x.$data.editMode = false;
        }
      });
    } catch (e) {}
  });
})();
</script>
"""
    # Inject everything as early in <head> as possible. base_tag must come
    # FIRST so all subsequent relative URLs resolve against base_url.
    payload = base_tag + snapshot_css + shim
    if "<head>" in html:
        return html.replace("<head>", "<head>\n" + payload, 1)
    return payload + html


class StandaloneHtmlExportService:

    @staticmethod
    def export_workspace(organization_id, *, base_url=None, generated_by=None):
        """
        Render the live workspace page, inline its local assets, install a
        fetch interceptor seeded with the workspace data, and return the
        resulting single HTML file as BytesIO.

        Must be called from within a Flask request context with a logged-in
        user whose session.organization_id == organization_id.
        """
        from datetime import datetime

        from app import __version__ as app_version
        from app.models import Organization
        from app.routes.workspace import _build_workspace_data, index

        org = Organization.query.get(organization_id)
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        # 1. Build the workspace data dict (the JSON the live page consumes).
        ws_response = _build_workspace_data(organization_id)
        ws_data = ws_response.get_json()

        # 2. Render the live page.
        rendered = index()
        if hasattr(rendered, "get_data"):
            html = rendered.get_data(as_text=True)
        else:
            html = str(rendered)

        # 3. Inline local /static/ CSS and JS so the file is self-contained.
        html = _inline_local_assets(html)

        # 4. Build the "extras" dict: data needed by the in-page Porter /
        #    Strategy / Lenses / SWOT modals so those clicks never go to the
        #    server. SWOT is per-space and already lives inside ws_data.spaces;
        #    Lenses / value types live on ws_data.valueTypes; we add Porters
        #    and Strategic Pillars here.
        from app.models import Space, StrategicPillar
        pillars = []
        for p in (StrategicPillar.query.filter_by(organization_id=organization_id)
                  .order_by(StrategicPillar.display_order).all()):
            pillars.append({
                "name": p.name,
                "description": p.description,
                "accent_color": p.accent_color,
                "bs_icon": p.bs_icon,
            })

        # SWOT per space — _build_workspace_data exposes only `swot_completion`,
        # not the actual S/W/O/T text fields. Pull them straight from the model.
        swot_by_space = {}
        spaces_for_swot = Space.query.filter_by(organization_id=organization_id).all()
        for sp in spaces_for_swot:
            swot_by_space[sp.id] = {
                "name":          sp.name,
                "strengths":     sp.swot_strengths,
                "weaknesses":    sp.swot_weaknesses,
                "opportunities": sp.swot_opportunities,
                "threats":       sp.swot_threats,
            }

        # Pre-render the live SWOT / Strategy / Lenses / Porter pages so the
        # snapshot's modals look identical to the live ones — same icons, same
        # bullet glyphs (✓/✗/→/⚠), same gradient headers, same pillar cards.
        from app.models import ValueType
        value_types_active = (ValueType.query.filter_by(organization_id=organization_id, is_active=True)
                              .order_by(ValueType.display_order, ValueType.name).all())
        panels = {
            "porters":    _render_panel("organization_admin/organization_porters.html",
                                         organization=org, csrf_token=lambda: ""),
            "strategy":   _render_panel("workspace/strategy.html", pillars=[
                                         _p for _p in (StrategicPillar.query
                                                       .filter_by(organization_id=organization_id)
                                                       .order_by(StrategicPillar.display_order).all())
                                       ]),
            "dimensions": _render_panel("workspace/dimensions.html", value_types=value_types_active),
            "swot":       {sp.id: _render_panel("organization_admin/space_swot.html",
                                                space=sp, csrf_token=lambda: "")
                           for sp in spaces_for_swot},
        }

        extras = {
            "porters": {
                "new_entrants": org.porters_new_entrants,
                "suppliers":    org.porters_suppliers,
                "buyers":       org.porters_buyers,
                "substitutes":  org.porters_substitutes,
                "rivalry":      org.porters_rivalry,
            },
            "pillars": pillars,
            "strategy_enabled": bool(getattr(org, "strategy_enabled", False)),
            "swot": swot_by_space,
            "panels": panels,
        }

        # 5. Inject the data + fetch shim (must run before Alpine boots).
        meta = {
            "org_name": org.name,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generated_by": generated_by,
            "app_version": app_version,
        }
        html = _inject_shim(html, ws_data, snapshot_meta=meta, base_url=base_url, extras=extras)

        return BytesIO(html.encode("utf-8"))
