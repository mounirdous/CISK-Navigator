"""
Entity Links routes for managing URLs attached to entities
"""

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required

from app.extensions import db
from app.models import EntityLink

bp = Blueprint("entity_links", __name__, url_prefix="/entity-links")


@bp.route("/add", methods=["POST"])
@login_required
def add_link():
    """Add a new link to an entity"""
    data = request.get_json()

    entity_type = data.get("entity_type")
    entity_id = data.get("entity_id")
    url = data.get("url", "").strip()
    title = data.get("title", "").strip()
    is_public = data.get("is_public", False)

    # Validate
    if not entity_type or not entity_id:
        return jsonify({"success": False, "message": "Entity type and ID required"}), 400

    if entity_type not in ["space", "challenge", "initiative", "system", "kpi"]:
        return jsonify({"success": False, "message": "Invalid entity type"}), 400

    # Validate URL
    is_valid, error_msg = EntityLink.validate_url(url)
    if not is_valid:
        return jsonify({"success": False, "message": error_msg}), 400

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

    return jsonify(
        {
            "success": True,
            "message": "Link added successfully",
            "link_id": link.id,
        }
    )


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
    data = request.get_json()

    link_id = data.get("link_id")

    if not link_id:
        return jsonify({"success": False, "message": "Link ID required"}), 400

    link = EntityLink.query.get_or_404(link_id)

    # Check permission (creator only)
    if link.created_by != current_user.id:
        return jsonify({"success": False, "message": "Permission denied. Only the creator can delete this link."}), 403

    db.session.delete(link)
    db.session.commit()

    return jsonify({"success": True, "message": "Link deleted successfully"})


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
