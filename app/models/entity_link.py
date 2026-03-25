"""
Entity Links model for URLs/resources attached to entities
"""

from datetime import datetime

from app.extensions import db


# Bootstrap icon class + color + label per detected file type
TYPE_INFO = {
    "pdf":         {"bs_icon": "bi-file-earmark-pdf-fill",    "color": "#dc3545", "label": "PDF Document",           "emoji": "📕"},
    "word":        {"bs_icon": "bi-file-earmark-word-fill",   "color": "#2b579a", "label": "Word Document",          "emoji": "📝"},
    "excel":       {"bs_icon": "bi-file-earmark-excel-fill",  "color": "#217346", "label": "Excel Spreadsheet",      "emoji": "📊"},
    "powerpoint":  {"bs_icon": "bi-file-earmark-ppt-fill",    "color": "#d24726", "label": "PowerPoint",             "emoji": "📐"},
    "image":       {"bs_icon": "bi-file-earmark-image-fill",  "color": "#0dcaf0", "label": "Image",                  "emoji": "🖼️"},
    "video":       {"bs_icon": "bi-camera-video-fill",        "color": "#6f42c1", "label": "Video",                  "emoji": "🎥"},
    "archive":     {"bs_icon": "bi-file-earmark-zip-fill",    "color": "#6c757d", "label": "Archive",                "emoji": "📦"},
    "code":        {"bs_icon": "bi-file-earmark-code-fill",   "color": "#198754", "label": "Code / Script",          "emoji": "💻"},
    "web":         {"bs_icon": "bi-globe2",                   "color": "#0d6efd", "label": "Web Page",               "emoji": "🌐"},
    "folder":      {"bs_icon": "bi-folder-fill",              "color": "#ffc107", "label": "Folder",                 "emoji": "📁"},
}

STATUS_INFO = {
    "valid":          {"bg": "success",   "color": "#198754", "icon": "bi-check-circle-fill", "label": "Valid"},
    "auth_required":  {"bg": "warning",   "color": "#fd7e14", "icon": "bi-lock-fill",         "label": "Login required"},
    "invalid":        {"bg": "danger",    "color": "#dc3545", "icon": "bi-x-circle-fill",     "label": "Broken link"},
    "unreachable":    {"bg": "danger",    "color": "#dc3545", "icon": "bi-wifi-off",          "label": "Unreachable"},
    "unknown":        {"bg": "secondary", "color": "#6c757d", "icon": "bi-question-circle",   "label": "Not checked"},
}

# SharePoint/OneDrive Business URL type codes (/:w:/, /:x:/, etc. in path)
_SP_CODES = {
    "/:w:/": "word",
    "/:x:/": "excel",
    "/:b:/": "pdf",
    "/:p:/": "powerpoint",
    "/:i:/": "image",
    "/:v:/": "video",
    "/:f:/": "folder",
    "/:o:/": "excel",
}

# 1drv.ms shortened OneDrive Personal links: type encoded as first path segment
# e.g. https://1drv.ms/b/s!AbcXyz → /b/ = PDF
_ONEDRIVE_SHORT_CODES = {
    "b": "pdf",
    "w": "word",
    "x": "excel",
    "p": "powerpoint",
    "i": "image",
    "v": "video",
    "f": "folder",
}

# Office Online app subdomains (detected from final URL after redirect)
_OFFICE_APP_SUBDOMAINS = {
    "word.": "word",
    "excel.": "excel",
    "powerpoint.": "powerpoint",
    "onenote.": "word",
}

# Microsoft cloud storage domains — suppress generic "web" label for these
_MS_CLOUD_DOMAINS = (
    "sharepoint.com", "onedrive.live.com", "1drv.ms",
    "office.com", "officeapps.live.com", "docs.live.net",
    "microsoft.com",
)

# File extension → detected_type
_EXT_MAP = {
    ".pdf": "pdf",
    ".docx": "word",   ".doc": "word",
    ".xlsx": "excel",  ".xls": "excel",  ".csv": "excel",
    ".pptx": "powerpoint", ".ppt": "powerpoint",
    ".jpg": "image",   ".jpeg": "image", ".png": "image",
    ".gif": "image",   ".svg": "image",  ".webp": "image",
    ".mp4": "video",   ".mov": "video",  ".avi": "video",  ".mkv": "video",
    ".zip": "archive", ".tar": "archive", ".gz": "archive", ".rar": "archive",
    ".py": "code",     ".js": "code",    ".ts": "code",    ".json": "code",
    ".xml": "code",    ".md": "code",    ".sh": "code",
}


def _type_from_ext(path_lower):
    """Detect type from a file-path string (checks extension). Returns type or None."""
    clean = path_lower.split("?")[0].split("#")[0]
    for ext, dtype in _EXT_MAP.items():
        if clean.endswith(ext):
            return dtype
    return None


def _detect_type_from_url(url_lower):
    """Detect file type from URL patterns alone (no network). Returns type string or None."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url_lower)
    netloc = parsed.netloc
    path = parsed.path

    # 1. SharePoint/OneDrive Business: /:w:/, /:x:/, /:b:/, /:p:/ etc. in path
    for code, dtype in _SP_CODES.items():
        if code in url_lower:
            return dtype

    # 2. 1drv.ms shortened personal OneDrive links — type is the first path segment
    #    https://1drv.ms/b/s!AbcXyz  →  path=/b/s!...  →  first segment "b" = pdf
    if "1drv.ms" in netloc:
        first_seg = path.strip("/").split("/")[0]
        if first_seg in _ONEDRIVE_SHORT_CODES:
            return _ONEDRIVE_SHORT_CODES[first_seg]

    # 3. Google Docs / Sheets / Slides
    if "docs.google.com/document" in url_lower:
        return "word"
    if "docs.google.com/spreadsheets" in url_lower:
        return "excel"
    if "docs.google.com/presentation" in url_lower:
        return "powerpoint"

    # 4. Office Online file viewer — extract source URL and parse its extension
    #    https://view.officeapps.live.com/op/view.aspx?src=https://...file.docx
    if "view.officeapps.live.com" in netloc or "office.com/launch" in url_lower:
        qs = parse_qs(parsed.query)
        src = (qs.get("src") or qs.get("url") or [None])[0]
        if src:
            return _detect_type_from_url(src.lower()) or _type_from_ext(src.lower())

    # 5. File extension in path
    return _type_from_ext(path)


class EntityLink(db.Model):
    """
    Links/URLs attached to entities (spaces, challenges, initiatives, systems, KPIs).

    Can be public (shared across organization) or private (visible only to creator).
    """

    __tablename__ = "entity_links"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(
        db.String(20), nullable=False, comment="Type: space, challenge, initiative, system, kpi"
    )
    entity_id = db.Column(db.Integer, nullable=False, comment="ID of the entity")
    url = db.Column(db.Text, nullable=False, comment="The URL/link")
    title = db.Column(db.String(200), nullable=True, comment="Optional description")
    is_public = db.Column(
        db.Boolean, nullable=False, default=False, comment="Public (shared) or private link"
    )
    display_order = db.Column(db.Integer, nullable=False, default=0, comment="Sort order")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Link health fields
    link_status = db.Column(db.String(20), nullable=False, default="unknown",
                            comment="valid|auth_required|invalid|unreachable|unknown")
    detected_type = db.Column(db.String(100), nullable=True,
                              comment="pdf|word|excel|powerpoint|image|video|archive|code|web|folder")
    last_checked_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<EntityLink {self.entity_type}:{self.entity_id} - {self.title or self.url[:50]}>"

    @staticmethod
    def get_links_for_entity(entity_type, entity_id, user_id=None, include_private=True):
        """
        Get all links for an entity.

        Args:
            entity_type: Type of entity (space, challenge, initiative, system, kpi)
            entity_id: ID of the entity
            user_id: Current user ID (to include their private links)
            include_private: Whether to include private links (default True)

        Returns:
            List of EntityLink objects ordered by display_order
        """
        query = EntityLink.query.filter_by(entity_type=entity_type, entity_id=entity_id)

        if include_private and user_id:
            query = query.filter(
                db.or_(EntityLink.is_public == True, EntityLink.created_by == user_id)
            )
        else:
            query = query.filter_by(is_public=True)

        return query.order_by(EntityLink.display_order, EntityLink.created_at).all()

    @staticmethod
    def validate_url(url):
        """
        Basic URL validation.

        Returns:
            (is_valid, error_message)
        """
        import re

        if not url or not url.strip():
            return False, "URL is required"

        url = url.strip()

        url_pattern = re.compile(
            r"^(https?|ftp)://"
            r"([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+"
            r"(:[0-9]{1,5})?"
            r"(/.*)?$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            return False, "Invalid URL format. Must start with http://, https://, or ftp://"

        if len(url) > 2000:
            return False, "URL is too long (max 2000 characters)"

        return True, None

    @staticmethod
    def probe_url(url):
        """
        Probe a URL synchronously to check validity and detect file type.

        Returns a dict with:
            status:       valid | auth_required | invalid | unreachable | unknown
            detected_type: pdf | word | excel | powerpoint | image | video | archive | code | web | folder | None
            status_code:  HTTP status code or None
            bs_icon:      Bootstrap icon class for the detected type
            icon_color:   CSS color for the type icon
            type_label:   Human-readable type label
            status_label: Human-readable status
            status_color: CSS color for the status
            status_bg:    Bootstrap badge bg class
            status_icon:  Bootstrap icon class for the status
            error:        Error message if any
        """
        import requests as req

        result = {
            "status": "unknown",
            "detected_type": None,
            "status_code": None,
            "error": None,
        }

        url_lower = url.lower()

        # Try to detect type from URL patterns (no network needed)
        result["detected_type"] = _detect_type_from_url(url_lower)

        # Probe the URL with a HEAD request
        try:
            resp = req.head(
                url,
                timeout=5,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 CISK-Navigator LinkChecker/1.0"},
            )
            result["status_code"] = resp.status_code

            if resp.status_code < 300:
                result["status"] = "valid"
            elif resp.status_code in (401, 403):
                result["status"] = "auth_required"
            elif resp.status_code in (404, 410):
                result["status"] = "invalid"
            else:
                # Some servers don't support HEAD — try GET with no body
                result["status"] = "valid" if resp.status_code < 500 else "invalid"

            final_url = resp.url or url
            final_lower = final_url.lower()

            if not result["detected_type"]:
                # (a) Content-Type header
                ct = resp.headers.get("Content-Type", "").lower()
                if "pdf" in ct:
                    result["detected_type"] = "pdf"
                elif "wordprocessing" in ct or "msword" in ct:
                    result["detected_type"] = "word"
                elif "spreadsheet" in ct or "ms-excel" in ct or "excel" in ct:
                    result["detected_type"] = "excel"
                elif "presentation" in ct or "powerpoint" in ct or "ms-powerpoint" in ct:
                    result["detected_type"] = "powerpoint"
                elif ct.startswith("image/"):
                    result["detected_type"] = "image"
                elif ct.startswith("video/"):
                    result["detected_type"] = "video"
                elif "zip" in ct or "x-tar" in ct or "compressed" in ct or "x-rar" in ct:
                    result["detected_type"] = "archive"
                elif "text/html" in ct or "text/plain" in ct:
                    result["detected_type"] = "web"

            if not result["detected_type"]:
                # (b) Content-Disposition: attachment; filename="report.docx"
                import re as _re
                cd = resp.headers.get("Content-Disposition", "")
                if cd:
                    m = _re.search(r'filename[^;=\n]*=["\']?([^;\n"\']+)', cd, _re.IGNORECASE)
                    if m:
                        fname = m.group(1).strip().strip("\"'")
                        result["detected_type"] = _type_from_ext(fname.lower())

            if not result["detected_type"]:
                # (c) Final URL after redirect — catches 1drv.ms → SharePoint with /:w:/
                result["detected_type"] = _detect_type_from_url(final_lower)

            if not result["detected_type"]:
                # (d) Office Online app subdomain in final URL
                #     e.g. word.office.com, excel.office.com after redirect
                from urllib.parse import urlparse as _up
                final_netloc = _up(final_lower).netloc
                for prefix, dtype in _OFFICE_APP_SUBDOMAINS.items():
                    if final_netloc.startswith(prefix):
                        result["detected_type"] = dtype
                        break

            # Suppress generic "web" for Microsoft cloud domains —
            # the HTML is a document viewer, not a web page per se
            if result["detected_type"] == "web":
                if any(domain in url_lower for domain in _MS_CLOUD_DOMAINS):
                    result["detected_type"] = None

        except req.exceptions.Timeout:
            result["status"] = "unreachable"
            result["error"] = "Connection timed out"
        except req.exceptions.ConnectionError:
            result["status"] = "unreachable"
            result["error"] = "Connection failed"
        except Exception as e:
            result["status"] = "unknown"
            result["error"] = str(e)[:100]

        # Enrich with display info
        type_info = TYPE_INFO.get(result["detected_type"], {})
        result["bs_icon"] = type_info.get("bs_icon", "bi-link-45deg")
        result["icon_color"] = type_info.get("color", "#6c757d")
        result["type_label"] = type_info.get("label", "")

        status_info = STATUS_INFO.get(result["status"], STATUS_INFO["unknown"])
        result["status_label"] = status_info["label"]
        result["status_color"] = status_info["color"]
        result["status_bg"] = status_info["bg"]
        result["status_icon"] = status_info["icon"]

        return result

    def probe_and_save(self):
        """Probe this link's URL and persist the result. Returns the probe result dict."""
        result = EntityLink.probe_url(self.url)
        self.link_status = result["status"]
        self.detected_type = result.get("detected_type")
        self.last_checked_at = datetime.utcnow()
        return result

    def get_display_icon(self):
        """Get emoji icon — checks detected_type first, then URL patterns."""
        # Use detected type if available
        if self.detected_type and self.detected_type in TYPE_INFO:
            return TYPE_INFO[self.detected_type]["emoji"]

        url_lower = self.url.lower()

        # URL-pattern type detection (free, no network)
        detected = _detect_type_from_url(url_lower)
        if detected and detected in TYPE_INFO:
            return TYPE_INFO[detected]["emoji"]

        # Domain-based fallback
        if "docs.google" in url_lower or "drive.google" in url_lower:
            return "📄"
        if "sharepoint" in url_lower or "onedrive" in url_lower:
            return "📁"
        if "github" in url_lower or "gitlab" in url_lower:
            return "💻"
        if "confluence" in url_lower or "wiki" in url_lower:
            return "📖"
        if "youtube" in url_lower or "vimeo" in url_lower:
            return "🎥"
        if "slack" in url_lower or "teams.microsoft" in url_lower:
            return "💬"
        if "jira" in url_lower or "trello" in url_lower:
            return "📋"

        return "🔗"

    def get_type_info(self):
        """Return Bootstrap icon info dict for the detected type (or defaults)."""
        if self.detected_type and self.detected_type in TYPE_INFO:
            return TYPE_INFO[self.detected_type]
        # Try URL-based detection
        detected = _detect_type_from_url(self.url.lower())
        if detected and detected in TYPE_INFO:
            return TYPE_INFO[detected]
        return {"bs_icon": "bi-link-45deg", "color": "#6c757d", "label": "Link"}

    def get_status_info(self):
        """Return status display info dict."""
        return STATUS_INFO.get(self.link_status, STATUS_INFO["unknown"])
