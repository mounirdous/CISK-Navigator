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
    org_id = session.get("organization_id")

    # Get filter parameters
    item_type = request.args.get("type_filter", "all")
    status_filter = request.args.get("status_filter", "all")
    visibility_filter = request.args.get("visibility_filter", "all")

    # Convert 'all' to None for service
    type_param = None if item_type == "all" else item_type
    status_param = None if status_filter == "all" else status_filter

    # Get items
    items = ActionItemService.get_items_for_user(
        user=current_user,
        organization_id=org_id,
        item_type=type_param,
        status=status_param,
        visibility_filter=visibility_filter,
    )

    # Get stats
    stats = ActionItemService.get_stats_for_user(current_user, org_id)

    # Filter form for persistence
    filter_form = ActionItemFilterForm(
        type_filter=item_type, status_filter=status_filter, visibility_filter=visibility_filter
    )

    return render_template(
        "action_items/index.html",
        items=items,
        stats=stats,
        filter_form=filter_form,
        current_filters={"type": item_type, "status": status_filter, "visibility": visibility_filter},
        csrf_token=generate_csrf,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@organization_required
def create():
    """Create new action item or memo"""
    org_id = session.get("organization_id")
    form = ActionItemCreateForm()

    if form.validate_on_submit():
        try:
            item = ActionItemService.create_item(
                organization_id=org_id,
                owner_user_id=current_user.id,
                created_by_user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                item_type=form.type.data,
                status=form.status.data if form.type.data == "action" else "active",
                priority=form.priority.data if form.type.data == "action" else "medium",
                due_date=form.due_date.data,
                visibility=form.visibility.data,
            )

            flash(f"{'Action' if item.type == 'action' else 'Memo'} created successfully!", "success")
            return redirect(url_for("action_items.index"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating item: {str(e)}", "danger")

    return render_template("action_items/create.html", form=form, csrf_token=generate_csrf)


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@organization_required
def edit(item_id):
    """Edit action item or memo"""
    item = ActionItem.query.get_or_404(item_id)

    # Check ownership
    if item.owner_user_id != current_user.id:
        flash("You can only edit your own items", "danger")
        return redirect(url_for("action_items.index"))

    form = ActionItemEditForm(obj=item)

    if form.validate_on_submit():
        try:
            updated_item = ActionItemService.update_item(
                item_id=item.id,
                user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                status=form.status.data if item.type == "action" else None,
                priority=form.priority.data if item.type == "action" else None,
                due_date=form.due_date.data,
                visibility=form.visibility.data,
            )

            if updated_item:
                flash("Item updated successfully!", "success")
                return redirect(url_for("action_items.index"))
            else:
                flash("Error updating item", "danger")

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating item: {str(e)}", "danger")

    return render_template("action_items/edit.html", form=form, item=item, csrf_token=generate_csrf)


@bp.route("/<int:item_id>/delete", methods=["POST"])
@login_required
@organization_required
def delete(item_id):
    """Delete action item or memo"""
    if ActionItemService.delete_item(item_id, current_user.id):
        flash("Item deleted successfully", "success")
    else:
        flash("Error deleting item (not found or unauthorized)", "danger")

    return redirect(url_for("action_items.index"))


@bp.route("/<int:item_id>/toggle-status", methods=["POST"])
@login_required
@organization_required
def toggle_status(item_id):
    """Quick toggle between active and completed"""
    item = ActionItem.query.get_or_404(item_id)

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
