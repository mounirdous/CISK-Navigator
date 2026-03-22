"""
Entity Links routes for managing URLs attached to entities
"""

from flask import Blueprint, flash, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import EntityLink

bp = Blueprint("entity_links", __name__, url_prefix="/entity-links")


@bp.route("/add", methods=["POST"])
@login_required
def add_link():
    """Add a new link to an entity"""
    entity_type = request.form.get("entity_type")
    entity_id = int(request.form.get("entity_id"))
    url = request.form.get("url", "").strip()
    title = request.form.get("title", "").strip()
    is_public = request.form.get("is_public") == "true"

    # Validate
    if not entity_type or not entity_id:
        flash("Entity type and ID required", "danger")
        return redirect(request.referrer or url_for("workspace.index"))

    if entity_type not in ["space", "challenge", "initiative", "system", "kpi", "action_item"]:
        flash("Invalid entity type", "danger")
        return redirect(request.referrer or url_for("workspace.index"))

    # Validate URL
    is_valid, error_msg = EntityLink.validate_url(url)
    if not is_valid:
        flash(error_msg, "danger")
        return redirect(request.referrer or url_for("workspace.index"))

    # Get next display_order
    max_order = (
        db.session.query(db.func.max(EntityLink.display_order))
        .filter_by(entity_type=entity_type, entity_id=entity_id)
        .scalar()
    )
    next_order = (max_order or 0) + 1

    # Create link
    link = EntityLink(
        entity_type=entity_type,
        entity_id=entity_id,
        url=url,
        title=title or None,
        is_public=is_public,
        display_order=next_order,
        created_by=current_user.id,
    )

    db.session.add(link)
    db.session.commit()

    flash("Link added successfully", "success")
    return redirect(request.referrer or url_for("workspace.index"))


@bp.route("/update", methods=["POST"])
@login_required
def update_link():
    """Update an existing link"""
    data = request.get_json()

    link_id = data.get("link_id")
    url = data.get("url", "").strip()
    title = data.get("title", "").strip()
    is_public = data.get("is_public", False)

    if not link_id:
        return jsonify({"success": False, "message": "Link ID required"}), 400

    link = EntityLink.query.get_or_404(link_id)

    # Check permission (creator or public link)
    if link.created_by != current_user.id and not link.is_public:
        return jsonify({"success": False, "message": "Permission denied"}), 403

    # Validate URL
    is_valid, error_msg = EntityLink.validate_url(url)
    if not is_valid:
        return jsonify({"success": False, "message": error_msg}), 400

    # Update
    link.url = url
    link.title = title or None
    link.is_public = is_public

    db.session.commit()

    return jsonify({"success": True, "message": "Link updated successfully"})


@bp.route("/delete", methods=["POST"])
@login_required
def delete_link():
    """Delete a link"""
    link_id = request.form.get("link_id")

    if not link_id:
        flash("Link ID required", "danger")
        return redirect(request.referrer or url_for("workspace.index"))

    link = EntityLink.query.get_or_404(int(link_id))

    # Check permission: creator or org admin
    org_id = session.get("organization_id")
    membership = next((m for m in current_user.organization_memberships if m.organization_id == org_id), None) if org_id else None
    is_org_admin = membership and membership.is_org_admin
    if link.created_by != current_user.id and not is_org_admin and not current_user.is_global_admin:
        flash("Permission denied. Only the creator or an org admin can delete this link.", "danger")
        return redirect(request.referrer or url_for("workspace.index"))

    db.session.delete(link)
    db.session.commit()

    flash("Link deleted successfully", "success")
    return redirect(request.referrer or url_for("workspace.index"))


@bp.route("/reorder", methods=["POST"])
@login_required
def reorder_links():
    """Reorder links"""
    data = request.get_json()

    link_ids = data.get("link_ids", [])

    if not link_ids:
        return jsonify({"success": False, "message": "Link IDs required"}), 400

    # Update display_order
    for index, link_id in enumerate(link_ids):
        link = EntityLink.query.get(link_id)
        if link:
            link.display_order = index
            db.session.add(link)

    db.session.commit()

    return jsonify({"success": True, "message": "Links reordered successfully"})
