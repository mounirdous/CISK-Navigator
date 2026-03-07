"""
Workspace routes

Main tree/grid navigation and data entry.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models import (
    Space, Challenge, Initiative, System, KPI, ValueType,
    KPIValueTypeConfig, Contribution, KPISnapshot, CellComment, User,
    UserOrganizationMembership
)
from app.forms import ContributionForm
from app.services import ConsensusService, AggregationService, ExcelExportService
from app.services.snapshot_service import SnapshotService
from app.services.comment_service import CommentService
from datetime import date

bp = Blueprint('workspace', __name__, url_prefix='/workspace')


def organization_required(f):
    """Decorator to require organization context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if session.get('organization_id') is None:
            flash('Please log in to an organization', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@login_required
@organization_required
def index():
    """
    Main workspace view: tree/grid navigation.

    Shows spaces (collapsed by default) with roll-up values visible.
    """
    org_id = session.get('organization_id')
    org_name = session.get('organization_name')

    # Get all spaces for this organization
    spaces = Space.query.filter_by(organization_id=org_id).order_by(Space.display_order, Space.name).all()

    # Get active value types
    value_types = ValueType.query.filter_by(
        organization_id=org_id,
        is_active=True
    ).order_by(ValueType.display_order).all()

    return render_template('workspace/index.html',
                          org_name=org_name,
                          spaces=spaces,
                          value_types=value_types)


@bp.route('/export-excel')
@login_required
@organization_required
def export_excel():
    """Export workspace to Excel file"""
    org_id = session.get('organization_id')
    org_name = session.get('organization_name')

    # Generate Excel file
    excel_file = ExcelExportService.export_workspace(org_id)

    # Create safe filename
    safe_org_name = "".join(c for c in org_name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"Workspace_{safe_org_name}.xlsx"

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/kpi/<int:kpi_id>/value-type/<int:vt_id>', methods=['GET', 'POST'])
@login_required
@organization_required
def kpi_cell_detail(kpi_id, vt_id):
    """
    Detail page for one KPI cell (KPI + value type).

    Shows:
    - Breadcrumb (org > space > challenge > initiative > system > kpi)
    - Current consensus status
    - List of contributions
    - Form to add/edit contribution
    """
    org_id = session.get('organization_id')

    # Get KPI and value type
    kpi = KPI.query.get_or_404(kpi_id)
    value_type = ValueType.query.get_or_404(vt_id)

    # Security check: ensure KPI belongs to current organization
    is_link = kpi.initiative_system_link
    initiative = is_link.initiative
    if initiative.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('workspace.index'))

    # Get KPI-ValueType config
    config = KPIValueTypeConfig.query.filter_by(kpi_id=kpi_id, value_type_id=vt_id).first()
    if not config:
        flash('This KPI does not use this value type', 'warning')
        return redirect(url_for('workspace.index'))

    # Get consensus status
    consensus = ConsensusService.get_cell_value(config)

    # Get all contributions
    contributions = config.contributions

    # Handle contribution form
    form = ContributionForm()

    # Customize qualitative level choices based on value type kind
    if value_type.is_qualitative():
        if value_type.kind == 'risk':
            form.qualitative_level.choices = [
                ('', 'Select...'),
                ('1', '! (Low)'),
                ('2', '!! (Medium)'),
                ('3', '!!! (High)')
            ]
        elif value_type.kind == 'positive_impact':
            form.qualitative_level.choices = [
                ('', 'Select...'),
                ('1', '★ (Low)'),
                ('2', '★★ (Medium)'),
                ('3', '★★★ (High)')
            ]
        elif value_type.kind == 'negative_impact':
            form.qualitative_level.choices = [
                ('', 'Select...'),
                ('1', '▼ (Low)'),
                ('2', '▼▼ (Medium)'),
                ('3', '▼▼▼ (High)')
            ]

    if form.validate_on_submit():
        contributor_name = form.contributor_name.data

        # Check if this contributor already has a contribution for this cell
        existing = Contribution.query.filter_by(
            kpi_value_type_config_id=config.id,
            contributor_name=contributor_name
        ).first()

        if existing:
            # Update existing contribution
            if value_type.is_numeric():
                existing.numeric_value = form.numeric_value.data
                existing.qualitative_level = None
            else:
                existing.numeric_value = None
                existing.qualitative_level = form.qualitative_level.data
            existing.comment = form.comment.data
            flash(f'Contribution from {contributor_name} updated', 'success')
        else:
            # Create new contribution
            contribution = Contribution(
                kpi_value_type_config_id=config.id,
                contributor_name=contributor_name,
                comment=form.comment.data
            )
            if value_type.is_numeric():
                contribution.numeric_value = form.numeric_value.data
            else:
                contribution.qualitative_level = form.qualitative_level.data

            db.session.add(contribution)
            flash(f'Contribution from {contributor_name} added', 'success')

        db.session.commit()
        return redirect(url_for('workspace.kpi_cell_detail', kpi_id=kpi_id, vt_id=vt_id))

    # Build breadcrumb
    system = is_link.system
    challenge_names = [ci.challenge.name for ci in initiative.challenge_links]
    space_names = [ci.challenge.space.name for ci in initiative.challenge_links]

    breadcrumb = {
        'organization': session.get('organization_name'),
        'space': space_names[0] if space_names else 'N/A',
        'challenge': challenge_names[0] if challenge_names else 'N/A',
        'initiative': initiative.name,
        'system': system.name,
        'kpi': kpi.name,
        'value_type': value_type.name
    }

    return render_template('workspace/kpi_cell_detail.html',
                          kpi=kpi,
                          value_type=value_type,
                          config=config,
                          consensus=consensus,
                          contributions=contributions,
                          form=form,
                          breadcrumb=breadcrumb)


@bp.route('/kpi/<int:kpi_id>/value-type/<int:vt_id>/delete-contribution', methods=['POST'])
@login_required
@organization_required
def delete_contribution(kpi_id, vt_id):
    """
    Delete a contribution from a KPI cell.
    """
    org_id = session.get('organization_id')
    contribution_id = request.form.get('contribution_id')

    if not contribution_id:
        flash('Invalid request', 'danger')
        return redirect(url_for('workspace.kpi_cell_detail', kpi_id=kpi_id, vt_id=vt_id))

    # Get contribution and verify ownership
    contribution = Contribution.query.get_or_404(contribution_id)
    config = contribution.kpi_value_type_config
    kpi = config.kpi
    initiative = kpi.initiative_system_link.initiative

    if initiative.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('workspace.index'))

    contributor_name = contribution.contributor_name
    db.session.delete(contribution)
    db.session.commit()

    flash(f'Contribution from "{contributor_name}" has been deleted', 'success')
    return redirect(url_for('workspace.kpi_cell_detail', kpi_id=kpi_id, vt_id=vt_id))


@bp.route('/api/rollup/<string:entity_type>/<int:entity_id>/<int:value_type_id>')
@login_required
@organization_required
def api_rollup(entity_type, entity_id, value_type_id):
    """
    API endpoint to get roll-up value for a specific entity and value type.

    Used by the tree/grid to display rolled-up values.
    """
    try:
        if entity_type == 'system':
            # KPI → System rollup
            from app.models import InitiativeSystemLink
            is_link = InitiativeSystemLink.query.get(entity_id)
            if not is_link:
                return jsonify({'error': 'Not found'}), 404

            result = AggregationService.get_kpi_to_system_rollup(is_link, value_type_id)
            return jsonify(result)

        elif entity_type == 'initiative':
            result = AggregationService.get_system_to_initiative_rollup(entity_id, value_type_id)
            return jsonify(result)

        elif entity_type == 'challenge':
            result = AggregationService.get_initiative_to_challenge_rollup(entity_id, value_type_id)
            return jsonify(result)

        elif entity_type == 'space':
            result = AggregationService.get_challenge_to_space_rollup(entity_id, value_type_id)
            return jsonify(result)

        else:
            return jsonify({'error': 'Invalid entity type'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SNAPSHOT MANAGEMENT ROUTES (Time-Series Tracking)
# ============================================================================

@bp.route('/snapshots/create', methods=['POST'])
@login_required
@organization_required
def create_snapshot():
    """
    Create a snapshot of current workspace state.

    Captures all KPI values and rollups for the organization.
    """
    org_id = session.get('organization_id')
    snapshot_date_str = request.form.get('snapshot_date')
    label = request.form.get('label', '').strip()

    # Parse date
    if snapshot_date_str:
        try:
            snapshot_date = date.fromisoformat(snapshot_date_str)
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('workspace.index'))
    else:
        snapshot_date = date.today()

    # Create snapshots
    try:
        result = SnapshotService.create_organization_snapshot(
            org_id,
            snapshot_date=snapshot_date,
            label=label or None,
            user_id=current_user.id
        )

        flash(f'Snapshot created: {result["kpi_snapshots"]} KPI values, '
              f'{result["rollup_snapshots"]} rollup values captured for {snapshot_date.isoformat()}',
              'success')

        if result['skipped'] > 0:
            flash(f'{result["skipped"]} KPIs skipped (no consensus data)', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating snapshot: {str(e)}', 'danger')

    return redirect(url_for('workspace.index'))


@bp.route('/snapshots/list')
@login_required
@organization_required
def list_snapshots():
    """List all available snapshots for the organization"""
    org_id = session.get('organization_id')

    try:
        snapshot_dates = SnapshotService.get_available_snapshot_dates(org_id)

        # Get labels for each date
        snapshots_info = []
        for snap_date in snapshot_dates:
            # Get a sample snapshot to find the label
            sample = KPISnapshot.query.filter_by(
                snapshot_date=snap_date
            ).first()

            snapshots_info.append({
                'date': snap_date.isoformat(),
                'label': sample.snapshot_label if sample else None,
                'formatted_date': snap_date.strftime('%Y-%m-%d (%A)')
            })

        return render_template('workspace/snapshots.html',
                             snapshots=snapshots_info,
                             organization_name=session.get('organization_name'))

    except Exception as e:
        flash(f'Error loading snapshots: {str(e)}', 'danger')
        return redirect(url_for('workspace.index'))


@bp.route('/snapshots/view/<snapshot_date>')
@login_required
@organization_required
def view_snapshot(snapshot_date):
    """
    View workspace state as of a specific snapshot date.

    Shows historical values instead of current values.
    """
    org_id = session.get('organization_id')

    try:
        view_date = date.fromisoformat(snapshot_date)
    except ValueError:
        flash('Invalid date format', 'danger')
        return redirect(url_for('workspace.index'))

    # Get spaces and value types (current structure)
    spaces = Space.query.filter_by(organization_id=org_id).order_by(
        Space.display_order, Space.name
    ).all()

    value_types = ValueType.query.filter_by(
        organization_id=org_id,
        is_active=True
    ).order_by(ValueType.display_order).all()

    return render_template('workspace/index.html',
                         spaces=spaces,
                         value_types=value_types,
                         organization_name=session.get('organization_name'),
                         snapshot_date=view_date,
                         is_historical_view=True)


@bp.route('/api/kpi/<int:config_id>/trend')
@login_required
@organization_required
def get_kpi_trend(config_id):
    """
    Get trend information for a KPI.

    Returns: {'direction': 'up'|'down'|'stable', 'change': value, 'percent_change': percent}
    """
    try:
        trend = SnapshotService.calculate_trend(config_id, periods=2)

        if trend is None:
            return jsonify({'error': 'Insufficient historical data'}), 404

        return jsonify(trend)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/kpi/<int:config_id>/history')
@login_required
@organization_required
def get_kpi_history(config_id):
    """
    Get historical snapshots for a KPI.

    Returns array of snapshots with dates and values.
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        snapshots = SnapshotService.get_kpi_history(config_id, limit=limit)

        return jsonify({
            'snapshots': [s.to_dict() for s in snapshots],
            'count': len(snapshots)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# COMMENTS & COLLABORATION ROUTES (@mentions support)
# ============================================================================

@bp.route('/api/cell/<int:config_id>/comments', methods=['GET'])
@login_required
@organization_required
def get_cell_comments(config_id):
    """Get all comments for a KPI cell"""
    try:
        include_resolved = request.args.get('include_resolved', 'true').lower() == 'true'
        comments = CommentService.get_comments_for_cell(config_id, include_resolved=include_resolved)

        org_id = session.get('organization_id')

        def render_comment_tree(comment):
            """Recursively render comment with replies"""
            result = {
                **comment.to_dict(),
                'rendered_text': CommentService.render_comment_with_mentions(comment.comment_text, org_id),
                'replies': []
            }

            # Add replies
            for reply in comment.replies:
                result['replies'].append(render_comment_tree(reply))

            return result

        return jsonify({
            'comments': [c.to_dict() for c in comments],
            'count': len(comments),
            'rendered_comments': [render_comment_tree(c) for c in comments]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/cell/<int:config_id>/comments', methods=['POST'])
@login_required
@organization_required
def create_cell_comment(config_id):
    """Create a new comment on a KPI cell"""
    try:
        data = request.get_json()
        comment_text = data.get('comment_text', '').strip()
        parent_comment_id = data.get('parent_comment_id')

        if not comment_text:
            return jsonify({'error': 'Comment text is required'}), 400

        org_id = session.get('organization_id')

        comment = CommentService.create_comment(
            config_id=config_id,
            user_id=current_user.id,
            comment_text=comment_text,
            parent_comment_id=parent_comment_id,
            organization_id=org_id
        )

        return jsonify({
            'success': True,
            'comment': comment.to_dict(),
            'rendered_text': CommentService.render_comment_with_mentions(comment.comment_text, org_id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/comments/<int:comment_id>', methods=['PUT'])
@login_required
@organization_required
def update_cell_comment(comment_id):
    """Update an existing comment"""
    try:
        comment = CellComment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404

        # Check ownership
        if comment.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        comment_text = data.get('comment_text', '').strip()

        if not comment_text:
            return jsonify({'error': 'Comment text is required'}), 400

        org_id = session.get('organization_id')

        updated_comment = CommentService.update_comment(
            comment_id=comment_id,
            comment_text=comment_text,
            organization_id=org_id
        )

        return jsonify({
            'success': True,
            'comment': updated_comment.to_dict(),
            'rendered_text': CommentService.render_comment_with_mentions(updated_comment.comment_text, org_id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
@organization_required
def delete_cell_comment(comment_id):
    """Delete a comment"""
    try:
        comment = CellComment.query.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404

        # Check ownership or admin
        if comment.user_id != current_user.id and not current_user.is_global_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        success = CommentService.delete_comment(comment_id)

        return jsonify({'success': success})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/comments/<int:comment_id>/resolve', methods=['POST'])
@login_required
@organization_required
def resolve_comment(comment_id):
    """Mark a comment as resolved"""
    try:
        comment = CommentService.resolve_comment(comment_id, current_user.id)

        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/comments/<int:comment_id>/unresolve', methods=['POST'])
@login_required
@organization_required
def unresolve_comment(comment_id):
    """Mark a comment as unresolved"""
    try:
        comment = CommentService.unresolve_comment(comment_id)

        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/mentions/unread')
@login_required
@organization_required
def get_unread_mentions():
    """Get unread mentions for current user"""
    try:
        limit = request.args.get('limit', 20, type=int)
        mentions = CommentService.get_unread_mentions(current_user.id, limit=limit)

        return jsonify({
            'mentions': [m.to_dict() for m in mentions],
            'count': len(mentions)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/mentions/<int:notification_id>/read', methods=['POST'])
@login_required
@organization_required
def mark_mention_read(notification_id):
    """Mark a mention as read"""
    try:
        notification = CommentService.mark_mention_read(notification_id)

        return jsonify({
            'success': True,
            'notification': notification.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/mentions/mark-all-read', methods=['POST'])
@login_required
@organization_required
def mark_all_mentions_read():
    """Mark all mentions as read for current user"""
    try:
        count = CommentService.mark_all_mentions_read(current_user.id)

        return jsonify({
            'success': True,
            'count': count
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/org/users/search')
@login_required
@organization_required
def search_org_users():
    """
    Search users in current organization for @mention autocomplete.

    Query param: q=search_term
    """
    try:
        org_id = session.get('organization_id')
        search_term = request.args.get('q', '').strip().lower()

        if not search_term or len(search_term) < 2:
            return jsonify({'users': []})

        # Search users in organization by login or display_name
        users = db.session.query(User).join(
            UserOrganizationMembership
        ).filter(
            UserOrganizationMembership.organization_id == org_id,
            db.or_(
                User.login.ilike(f'%{search_term}%'),
                User.display_name.ilike(f'%{search_term}%')
            )
        ).limit(10).all()

        return jsonify({
            'users': [
                {
                    'id': u.id,
                    'login': u.login,
                    'display_name': u.display_name,
                    'email': u.email
                }
                for u in users
            ]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
