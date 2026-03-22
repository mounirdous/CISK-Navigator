"""
Action Items and Memos routes
"""

import json
from io import BytesIO

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.forms.action_item_forms import ActionItemCreateForm, ActionItemEditForm, ActionItemFilterForm
from app.models import ActionItem, EntityLink, EntityTypeDefault
from app.models.user_filter_preset import UserFilterPreset
from app.services.action_item_service import ActionItemService


def _hex_to_rgba(hex_color, alpha=0.12):
    """Convert #RRGGBB to rgba(r,g,b,alpha) string"""
    h = hex_color.lstrip('#')
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    except (ValueError, IndexError):
        return f"rgba(108,117,125,{alpha})"

bp = Blueprint("action_items", __name__, url_prefix="/toolbox/actions")


def organization_required(f):
    """Decorator to require organization context"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if session.get("organization_id") is None:
            flash("Please select an organization first.", "warning")
            return redirect(url_for("auth.select_organization"))
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/")
@login_required
@organization_required
def index():
    """Main action items page with list and filters"""
    from app.models import GovernanceBody

    org_id = session.get("organization_id")

    # Get filter parameters
    item_type = request.args.get("type_filter", "all")
    status_filters = request.args.getlist("status_filter")  # multi-select
    visibility_filter = request.args.get("visibility_filter", "all")
    gb_ids = request.args.getlist("gb_filter", type=int)

    # Convert 'all' to None for service
    type_param = None if item_type == "all" else item_type

    # Get items
    items = ActionItemService.get_items_for_user(
        user=current_user,
        organization_id=org_id,
        item_type=type_param,
        statuses=status_filters or None,
        visibility_filter=visibility_filter,
        governance_body_ids=gb_ids or None,
    )

    # Compute stats from the filtered items so cards match what's displayed
    stats = {
        "total_actions": sum(1 for i in items if i.type == "action"),
        "open_actions": sum(1 for i in items if i.type == "action" and i.status == "active"),
        "overdue_actions": sum(1 for i in items if i.is_overdue),
        "completed_actions": sum(1 for i in items if i.type == "action" and i.status == "completed"),
        "total_memos": sum(1 for i in items if i.type == "memo"),
    }

    # Filter form for persistence
    filter_form = ActionItemFilterForm(
        type_filter=item_type, visibility_filter=visibility_filter
    )

    # Governance bodies for filter
    governance_bodies = GovernanceBody.query.filter_by(organization_id=org_id, is_active=True).order_by(
        GovernanceBody.display_order
    ).all()

    # Check if user is admin
    is_admin = current_user.is_super_admin or current_user.is_global_admin

    # Priority colors from branding (for timeline CSS variables)
    hardcoded = EntityTypeDefault.get_hardcoded_defaults()
    priority_colors = {}
    for level in ('urgent', 'high', 'medium', 'low'):
        key = f'action_{level}'
        db_default = EntityTypeDefault.query.filter_by(organization_id=org_id, entity_type=key).first()
        color = db_default.default_color if db_default else hardcoded[key]['color']
        priority_colors[level] = {'color': color, 'bg': _hex_to_rgba(color)}

    # Active view (table or timeline)
    view = request.args.get("view", "table")

    # Timeline group-by (saved in presets)
    group_by = request.args.get("group_by", "priority")

    # Saved views for this user
    action_presets = (
        UserFilterPreset.query.filter_by(user_id=current_user.id, organization_id=org_id, feature="action_items")
        .order_by(UserFilterPreset.name)
        .all()
    )

    # Build full CISK hierarchy map for the Entity timeline view.
    # entity_parents[entity_type][entity_id] = {"challenge": {id, name}, "initiative": {id, name} | None, "system": {id, name} | None}
    from app.models import Challenge, ChallengeInitiativeLink, Initiative
    from app.models.system import InitiativeSystemLink, System
    from app.models.kpi import KPI

    # Collect mentioned entity ids by type
    mentioned: dict = {"initiative": set(), "system": set(), "kpi": set()}
    for item in items:
        for m in item.mentions:
            if m.entity_type in mentioned:
                mentioned[m.entity_type].add(m.entity_id)

    # initiative_id → challenge info
    _init_challenge: dict = {}
    all_initiative_ids = set(mentioned["initiative"])

    # For systems: system_id → initiative_id(s) via InitiativeSystemLink
    _sys_initiative: dict = {}  # system_id → initiative_id (first found)
    if mentioned["system"]:
        isl_rows = (
            db.session.query(InitiativeSystemLink)
            .filter(InitiativeSystemLink.system_id.in_(list(mentioned["system"])))
            .all()
        )
        for isl in isl_rows:
            if isl.system_id not in _sys_initiative:
                _sys_initiative[isl.system_id] = isl.initiative_id
                all_initiative_ids.add(isl.initiative_id)

    # For KPIs: kpi_id → initiative_id via InitiativeSystemLink
    _kpi_initiative: dict = {}  # kpi_id → initiative_id
    _kpi_system: dict = {}       # kpi_id → system_id
    if mentioned["kpi"]:
        kpi_rows = (
            db.session.query(KPI, InitiativeSystemLink)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .filter(KPI.id.in_(list(mentioned["kpi"])))
            .all()
        )
        for kpi, isl in kpi_rows:
            _kpi_initiative[kpi.id] = isl.initiative_id
            _kpi_system[kpi.id] = isl.system_id
            all_initiative_ids.add(isl.initiative_id)

    # Resolve all needed initiative → challenge
    if all_initiative_ids:
        ch_links = (
            db.session.query(ChallengeInitiativeLink, Challenge)
            .join(Challenge, ChallengeInitiativeLink.challenge_id == Challenge.id)
            .filter(ChallengeInitiativeLink.initiative_id.in_(list(all_initiative_ids)))
            .all()
        )
        for link, challenge in ch_links:
            if link.initiative_id not in _init_challenge:
                _init_challenge[link.initiative_id] = {"id": challenge.id, "name": challenge.name}

    # Resolve initiative names
    _initiative_names: dict = {}
    if all_initiative_ids:
        init_rows = Initiative.query.filter(Initiative.id.in_(list(all_initiative_ids))).all()
        for init in init_rows:
            _initiative_names[init.id] = init.name

    # Resolve system names for KPI parents
    all_system_ids = set(_kpi_system.values()) | set(_sys_initiative.keys())
    _system_names: dict = {}
    if all_system_ids:
        sys_rows = System.query.filter(System.id.in_(list(all_system_ids))).all()
        for sys in sys_rows:
            _system_names[sys.id] = sys.name

    # Build entity_parents: {entity_type: {entity_id: {challenge, initiative, system}}}
    # Used by JS to place each mention under the correct challenge bucket.
    entity_parents: dict = {}

    for init_id in mentioned["initiative"]:
        ch = _init_challenge.get(init_id)
        entity_parents[f"initiative__{init_id}"] = {"challenge": ch}

    for sys_id in mentioned["system"]:
        init_id = _sys_initiative.get(sys_id)
        ch = _init_challenge.get(init_id) if init_id else None
        init_name = _initiative_names.get(init_id) if init_id else None
        entity_parents[f"system__{sys_id}"] = {
            "challenge": ch,
            "initiative": {"id": init_id, "name": init_name} if init_id else None,
        }

    for kpi_id in mentioned["kpi"]:
        init_id = _kpi_initiative.get(kpi_id)
        sys_id = _kpi_system.get(kpi_id)
        ch = _init_challenge.get(init_id) if init_id else None
        init_name = _initiative_names.get(init_id) if init_id else None
        sys_name = _system_names.get(sys_id) if sys_id else None
        entity_parents[f"kpi__{kpi_id}"] = {
            "challenge": ch,
            "initiative": {"id": init_id, "name": init_name} if init_id else None,
            "system": {"id": sys_id, "name": sys_name} if sys_id else None,
        }

    # keep backward-compat alias
    initiative_challenge_map = {str(init_id): ch for init_id, ch in _init_challenge.items()}

    # Serialize items — include entity_id in mentions so JS can look up the challenge map
    timeline_items = []
    for item in items:
        timeline_items.append({
            "id": item.id,
            "title_text": item.title,
            "description": (item.description or "")[:200],
            "status": item.status,
            "priority": item.priority,
            "type": item.type,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "created_at": item.created_at.strftime("%Y-%m-%d"),
            "is_overdue": item.is_overdue,
            "owner": item.owner_user.display_name or item.owner_user.login if item.owner_user else "Unknown",
            "gbs": [gb.name for gb in item.governance_bodies],
            "mentions": [{"type": m.entity_type, "text": m.mention_text, "entity_id": m.entity_id} for m in item.mentions],
            "can_edit": item.owner_user_id == current_user.id,
            "view_url": url_for("action_items.view", item_id=item.id),
            "edit_url": url_for("action_items.edit", item_id=item.id),
            "delete_url": url_for("action_items.delete", item_id=item.id),
        })

    return render_template(
        "action_items/index.html",
        items=items,
        stats=stats,
        filter_form=filter_form,
        current_filters={
            "type": item_type,
            "statuses": status_filters,
            "visibility": visibility_filter,
            "gb_ids": gb_ids,
        },
        governance_bodies=governance_bodies,
        can_contribute=current_user.can_contribute(org_id),
        is_admin=is_admin,
        view=view,
        group_by=group_by,
        timeline_items=timeline_items,
        priority_colors=priority_colors,
        initiative_challenge_map=initiative_challenge_map,
        entity_parents=entity_parents,
        action_presets=[p.to_dict() for p in action_presets],
        csrf_token=generate_csrf,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@organization_required
def create():
    """Create new action item or memo"""
    from app.models import GovernanceBody, User, UserOrganizationMembership

    org_id = session.get("organization_id")

    # Check permission
    if not current_user.can_contribute(org_id):
        flash("You do not have permission to create action items", "danger")
        return redirect(url_for("action_items.index"))

    form = ActionItemCreateForm()

    # Populate owner choices with organization users
    org_users = (
        db.session.query(User)
        .join(UserOrganizationMembership)
        .filter(UserOrganizationMembership.organization_id == org_id, User.is_active.is_(True))
        .order_by(User.display_name)
        .all()
    )
    form.owner_user_id.choices = [(u.id, u.display_name or u.login) for u in org_users]

    governance_bodies = GovernanceBody.query.filter_by(organization_id=org_id, is_active=True).order_by(
        GovernanceBody.display_order
    ).all()

    # Default to current user
    if request.method == "GET":
        form.owner_user_id.data = current_user.id

    if form.validate_on_submit():
        try:
            gb_ids = request.form.getlist("governance_body_ids", type=int)
            item = ActionItemService.create_item(
                organization_id=org_id,
                owner_user_id=form.owner_user_id.data,
                created_by_user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                item_type=form.type.data,
                status=form.status.data if form.type.data == "action" else "active",
                priority=form.priority.data if form.type.data == "action" else "medium",
                start_date=form.start_date.data if form.type.data == "action" else None,
                due_date=form.due_date.data,
                visibility=form.visibility.data,
                governance_body_ids=gb_ids,
            )

            flash(f"{'Action' if item.type == 'action' else 'Memo'} created successfully!", "success")
            return redirect(url_for("action_items.index"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating item: {str(e)}", "danger")

    return render_template("action_items/create.html", form=form, governance_bodies=governance_bodies, csrf_token=generate_csrf)


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
def edit(item_id):
    """Edit action item or memo"""
    from app.models import GovernanceBody, User, UserOrganizationMembership

    item = ActionItem.query.get_or_404(item_id)

    # Check permission
    if not current_user.can_contribute(item.organization_id):
        flash("You do not have permission to edit action items", "danger")
        return redirect(url_for("action_items.index"))

    # Check ownership
    if item.owner_user_id != current_user.id:
        flash("You can only edit your own items", "danger")
        return redirect(url_for("action_items.index"))

    form = ActionItemEditForm(obj=item)

    org_users = (
        db.session.query(User)
        .join(UserOrganizationMembership)
        .filter(UserOrganizationMembership.organization_id == item.organization_id, User.is_active.is_(True))
        .order_by(User.display_name)
        .all()
    )
    form.owner_user_id.choices = [(u.id, u.display_name or u.login) for u in org_users]

    governance_bodies = GovernanceBody.query.filter_by(
        organization_id=item.organization_id, is_active=True
    ).order_by(GovernanceBody.display_order).all()
    current_gb_ids = {gb.id for gb in item.governance_bodies}

    if form.validate_on_submit():
        try:
            gb_ids = request.form.getlist("governance_body_ids", type=int)
            updated_item = ActionItemService.update_item(
                item_id=item.id,
                user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                status=form.status.data if item.type == "action" else None,
                priority=form.priority.data if item.type == "action" else None,
                start_date=form.start_date.data if item.type == "action" else None,
                due_date=form.due_date.data,
                owner_user_id=form.owner_user_id.data,
                visibility=form.visibility.data,
                governance_body_ids=gb_ids,
            )

            if updated_item:
                flash("Item updated successfully!", "success")
                return redirect(url_for("action_items.index"))
            else:
                flash("Error updating item", "danger")

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating item: {str(e)}", "danger")

    entity_links = EntityLink.get_links_for_entity("action_item", item.id, user_id=current_user.id)

    return render_template(
        "action_items/edit.html",
        form=form,
        item=item,
        governance_bodies=governance_bodies,
        current_gb_ids=current_gb_ids,
        entity_links=entity_links,
        csrf_token=generate_csrf,
    )


@bp.route("/<int:item_id>/delete", methods=["POST"])
@login_required
@organization_required
def delete(item_id):
    """Delete action item or memo"""
    org_id = session.get("organization_id")

    # Check permission - admins can delete any item, contributors can delete their own
    is_admin = current_user.is_super_admin or current_user.is_global_admin
    if not is_admin and not current_user.can_contribute(org_id):
        flash("You do not have permission to delete action items", "danger")
        return redirect(url_for("action_items.index"))

    if ActionItemService.delete_item(item_id, current_user.id, is_admin=is_admin):
        flash("Item deleted successfully", "success")
    else:
        flash("Error deleting item (not found or unauthorized)", "danger")

    return redirect(url_for("action_items.index"))


@bp.route("/bulk-delete", methods=["POST"])
@login_required
@organization_required
def bulk_delete():
    """Bulk delete action items or memos"""
    org_id = session.get("organization_id")

    # Check permission - admins can delete any items
    is_admin = current_user.is_super_admin or current_user.is_global_admin
    if not is_admin and not current_user.can_contribute(org_id):
        flash("You do not have permission to delete action items", "danger")
        return redirect(url_for("action_items.index"))

    # Get item IDs from form
    item_ids = request.form.getlist("item_ids", type=int)
    if not item_ids:
        flash("No items selected", "warning")
        return redirect(url_for("action_items.index"))

    # Delete items
    deleted_count = ActionItemService.bulk_delete_items(item_ids, current_user.id, is_admin=is_admin)

    if deleted_count > 0:
        flash(f"Successfully deleted {deleted_count} item(s)", "success")
    else:
        flash("No items were deleted (not found or unauthorized)", "danger")

    return redirect(url_for("action_items.index"))


@bp.route("/<int:item_id>/toggle-status", methods=["POST"])
@login_required
@organization_required
def toggle_status(item_id):
    """Quick toggle between active and completed"""
    item = ActionItem.query.get_or_404(item_id)

    # Check permission
    if not current_user.can_contribute(item.organization_id):
        return jsonify({"error": "Permission denied"}), 403

    if item.owner_user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    if item.type != "action":
        return jsonify({"error": "Only actions have status"}), 400

    # Toggle between active and completed
    new_status = "completed" if item.status == "active" else "active"

    ActionItemService.update_item(item_id=item.id, user_id=current_user.id, status=new_status)

    return jsonify({"success": True, "new_status": new_status})


@bp.route("/bulk-set-start-date", methods=["POST"])
@login_required
@organization_required
def bulk_set_start_date():
    """Bulk-set start_date on multiple action items (owner or admin only)."""
    from datetime import date as date_type

    org_id = session.get("organization_id")
    is_admin = current_user.is_super_admin or current_user.is_global_admin
    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "No items provided"}), 400

    updated = 0
    for entry in data["items"]:
        item = ActionItem.query.filter_by(id=entry.get("id"), organization_id=org_id).first()
        if not item:
            continue
        if not is_admin and item.owner_user_id != current_user.id:
            continue
        raw = entry.get("start_date", "")
        try:
            item.start_date = date_type.fromisoformat(raw) if raw else None
            updated += 1
        except ValueError:
            pass

    from app.extensions import db
    db.session.commit()
    return jsonify({"updated": updated})


@bp.route("/api/search-entities")
@login_required
@organization_required
def api_search_entities():
    """API endpoint for entity mention autocomplete"""
    org_id = session.get("organization_id")
    search_query = request.args.get("q", "")

    if not search_query or len(search_query) < 2:
        return jsonify([])

    results = ActionItemService.search_entities_for_mention(search_query, org_id, limit=10)

    return jsonify(results)


@bp.route("/<int:item_id>/view")
@login_required
@organization_required
def view(item_id):
    """Read-only view of an action item or memo"""
    item = ActionItem.query.get_or_404(item_id)

    # Respect private visibility
    is_admin = current_user.is_super_admin or current_user.is_global_admin
    if item.visibility == "private" and item.owner_user_id != current_user.id and not is_admin:
        flash("You do not have permission to view this item.", "danger")
        return redirect(url_for("action_items.index"))

    entity_links = EntityLink.get_links_for_entity(
        "action_item", item.id, user_id=current_user.id
    )
    can_edit = item.owner_user_id == current_user.id

    return render_template(
        "action_items/view.html",
        item=item,
        entity_links=entity_links,
        can_edit=can_edit,
        is_admin=is_admin,
        csrf_token=generate_csrf,
    )


@bp.route("/export.json")
@login_required
@organization_required
def export_json():
    """Export all visible action items as JSON"""
    from datetime import date as date_type

    org_id = session.get("organization_id")
    items = ActionItemService.get_items_for_user(user=current_user, organization_id=org_id)

    data = []
    for item in items:
        links = EntityLink.get_links_for_entity("action_item", item.id, user_id=current_user.id)
        data.append({
            "title": item.title,
            "description": item.description or "",
            "type": item.type,
            "status": item.status,
            "priority": item.priority,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "visibility": item.visibility,
            "owner": item.owner_user.display_name or item.owner_user.login if item.owner_user else None,
            "governance_bodies": [gb.name for gb in item.governance_bodies],
            "urls": [{"url": l.url, "title": l.title or "", "is_public": l.is_public} for l in links],
        })

    payload = json.dumps(data, indent=2, ensure_ascii=False)
    bio = BytesIO(payload.encode("utf-8"))
    bio.seek(0)
    filename = f"action_items_{org_id}_{date_type.today().isoformat()}.json"
    return send_file(bio, mimetype="application/json", as_attachment=True, download_name=filename)


@bp.route("/template.json")
@login_required
@organization_required
def template_json():
    """Download a blank import template"""
    template = [
        {
            "title": "Example action title",
            "description": "Optional description. Use @mentions to link entities (e.g. @\"Initiative Name\").",
            "type": "action",
            "status": "active",
            "priority": "medium",
            "start_date": "2026-04-01",
            "due_date": "2026-04-30",
            "visibility": "shared",
            "governance_bodies": ["Governance Body Name"],
            "urls": [{"url": "https://example.com/doc", "title": "Reference document", "is_public": True}],
        },
        {
            "title": "Example memo title",
            "description": "A memo is a note — no deadline or priority tracking.",
            "type": "memo",
            "status": "active",
            "priority": "medium",
            "start_date": None,
            "due_date": None,
            "visibility": "shared",
            "governance_bodies": [],
            "urls": [],
        },
    ]
    payload = json.dumps(template, indent=2)
    bio = BytesIO(payload.encode("utf-8"))
    bio.seek(0)
    return send_file(bio, mimetype="application/json", as_attachment=True, download_name="action_items_template.json")


@bp.route("/import", methods=["POST"])
@login_required
@organization_required
def import_json():
    """Import action items from a JSON file"""
    from datetime import date as date_type
    from app.models import GovernanceBody

    org_id = session.get("organization_id")

    if not current_user.can_contribute(org_id):
        flash("You do not have permission to import action items.", "danger")
        return redirect(url_for("action_items.index"))

    uploaded = request.files.get("json_file")
    if not uploaded or not uploaded.filename.lower().endswith(".json"):
        flash("Please upload a .json file.", "danger")
        return redirect(url_for("action_items.index"))

    try:
        data = json.loads(uploaded.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        flash(f"Invalid JSON: {e}", "danger")
        return redirect(url_for("action_items.index"))

    if not isinstance(data, list):
        flash("JSON must be an array of action item objects.", "danger")
        return redirect(url_for("action_items.index"))

    created_count = 0
    row_errors = []

    for i, row in enumerate(data, start=1):
        try:
            title = (row.get("title") or "").strip()
            if not title:
                row_errors.append(f"Row {i}: missing title")
                continue

            start_date = None
            due_date = None
            if row.get("start_date"):
                start_date = date_type.fromisoformat(row["start_date"])
            if row.get("due_date"):
                due_date = date_type.fromisoformat(row["due_date"])

            gb_names = row.get("governance_bodies") or []
            gb_ids = []
            if gb_names:
                gbs = GovernanceBody.query.filter(
                    GovernanceBody.organization_id == org_id,
                    GovernanceBody.name.in_(gb_names),
                ).all()
                gb_ids = [gb.id for gb in gbs]

            item = ActionItemService.create_item(
                organization_id=org_id,
                owner_user_id=current_user.id,
                created_by_user_id=current_user.id,
                title=title,
                description=row.get("description") or "",
                item_type=row.get("type", "action"),
                status=row.get("status", "active"),
                priority=row.get("priority", "medium"),
                start_date=start_date,
                due_date=due_date,
                visibility=row.get("visibility", "shared"),
                governance_body_ids=gb_ids,
            )

            for url_entry in (row.get("urls") or []):
                url = (url_entry.get("url") or "").strip()
                is_valid, _ = EntityLink.validate_url(url)
                if is_valid:
                    db.session.add(EntityLink(
                        entity_type="action_item",
                        entity_id=item.id,
                        url=url,
                        title=url_entry.get("title") or None,
                        is_public=bool(url_entry.get("is_public", True)),
                        created_by=current_user.id,
                    ))
            db.session.commit()
            created_count += 1

        except Exception as e:
            db.session.rollback()
            row_errors.append(f"Row {i}: {e}")

    if created_count:
        flash(f"Imported {created_count} item(s) successfully.", "success")
    if row_errors:
        flash("Errors: " + "; ".join(row_errors[:5]), "warning")

    return redirect(url_for("action_items.index"))


# ---------------------------------------------------------------------------
# Saved Views (presets) API
# ---------------------------------------------------------------------------

@bp.route("/api/presets")
@login_required
@organization_required
def get_presets():
    """List all saved views for current user"""
    org_id = session.get("organization_id")
    presets = (
        UserFilterPreset.query.filter_by(user_id=current_user.id, organization_id=org_id, feature="action_items")
        .order_by(UserFilterPreset.name)
        .all()
    )
    return jsonify([p.to_dict() for p in presets])


@bp.route("/api/presets", methods=["POST"])
@login_required
@organization_required
def save_preset():
    """Save or overwrite a view preset"""
    org_id = session.get("organization_id")
    data = request.get_json()
    name = (data.get("name") or "").strip()
    filters = data.get("filters", {})
    overwrite = bool(data.get("overwrite", False))

    if not name:
        return jsonify({"error": "View name is required"}), 400

    existing = UserFilterPreset.query.filter_by(
        user_id=current_user.id, organization_id=org_id, feature="action_items", name=name
    ).first()

    if existing:
        if not overwrite:
            return jsonify({"error": f"A view named '{name}' already exists", "exists": True}), 409
        existing.filters = filters
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    preset = UserFilterPreset(
        user_id=current_user.id, organization_id=org_id, feature="action_items", name=name, filters=filters
    )
    db.session.add(preset)
    db.session.commit()
    return jsonify(preset.to_dict()), 201


@bp.route("/api/presets/<int:preset_id>", methods=["DELETE"])
@login_required
@organization_required
def delete_preset(preset_id):
    """Delete a saved view"""
    org_id = session.get("organization_id")
    preset = UserFilterPreset.query.get(preset_id)
    if not preset:
        return jsonify({"error": "Not found"}), 404
    if preset.user_id != current_user.id or preset.organization_id != org_id:
        return jsonify({"error": "Access denied"}), 403
    db.session.delete(preset)
    db.session.commit()
    return jsonify({"success": True})
