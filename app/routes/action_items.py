"""
Action Items and Memos routes
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.forms.action_item_forms import ActionItemCreateForm, ActionItemEditForm, ActionItemFilterForm
from app.models import ActionItem
from app.services.action_item_service import ActionItemService

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

    # Active view (table or timeline)
    view = request.args.get("view", "table")

    # Serialize items for the timeline view (JSON blob injected into template)
    timeline_items = []
    for item in items:
        timeline_items.append({
            "id": item.id,
            "title_text": item.title,
            "description": (item.description or "")[:200],
            "status": item.status,
            "priority": item.priority,
            "type": item.type,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "created_at": item.created_at.strftime("%Y-%m-%d"),
            "is_overdue": item.is_overdue,
            "owner": item.owner_user.display_name or item.owner_user.login if item.owner_user else "Unknown",
            "gbs": [gb.name for gb in item.governance_bodies],
            "mentions": [m.mention_text for m in item.mentions],
            "can_edit": item.owner_user_id == current_user.id,
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
        timeline_items=timeline_items,
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

    return render_template(
        "action_items/edit.html",
        form=form,
        item=item,
        governance_bodies=governance_bodies,
        current_gb_ids=current_gb_ids,
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
