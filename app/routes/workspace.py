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
    KPIValueTypeConfig, Contribution, KPISnapshot, RollupSnapshot, CellComment, User,
    UserOrganizationMembership, InitiativeSystemLink, GovernanceBody
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


@bp.route('/dashboard')
@login_required
@organization_required
def dashboard():
    """Dashboard with overview, charts, and recent activity"""
    org_id = session.get('organization_id')
    org_name = session.get('organization_name')

    # Get statistics
    stats = {
        'spaces': Space.query.filter_by(organization_id=org_id).count(),
        'challenges': Challenge.query.join(Space).filter(Space.organization_id == org_id).count(),
        'initiatives': Initiative.query.filter_by(organization_id=org_id).count(),
        'systems': System.query.filter_by(organization_id=org_id).count(),
        'kpis': db.session.query(KPI).join(
            InitiativeSystemLink
        ).join(Initiative).filter(Initiative.organization_id == org_id).count(),
        'value_types': ValueType.query.filter_by(organization_id=org_id, is_active=True).count()
    }

    # Get recent snapshots (last 5) - now with full snapshot info
    recent_snapshots = SnapshotService.get_all_snapshots(
        org_id,
        user_id=current_user.id,
        limit=5
    )

    # Get recent comments (last 10)
    recent_comments = db.session.query(CellComment).join(
        KPIValueTypeConfig
    ).join(KPI).join(
        InitiativeSystemLink
    ).join(Initiative).filter(
        Initiative.organization_id == org_id
    ).order_by(CellComment.created_at.desc()).limit(10).all()

    # Get unread mentions count
    unread_mentions = CommentService.get_unread_mentions_count(current_user.id)

    return render_template('workspace/dashboard.html',
                         org_name=org_name,
                         stats=stats,
                         recent_snapshots=recent_snapshots,
                         recent_comments=recent_comments,
                         unread_mentions=unread_mentions)


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

    # Get active governance bodies for filter
    from app.models import GovernanceBody
    governance_bodies = GovernanceBody.query.filter_by(
        organization_id=org_id,
        is_active=True
    ).order_by(GovernanceBody.display_order).all()

    # Get selected governance body IDs from query params
    selected_governance_body_ids = request.args.getlist('gb')

    # Smart default: if no governance bodies selected and some exist, select all
    # This fixes the bug where unchecking all filters still shows KPIs
    if not selected_governance_body_ids and governance_bodies:
        selected_governance_body_ids = [str(gb.id) for gb in governance_bodies]

    # Get show_archived flag
    show_archived = request.args.get('show_archived') == '1'

    # Get level visibility controls (default all visible)
    show_levels = {
        'spaces': request.args.get('show_spaces', '1') == '1',
        'challenges': request.args.get('show_challenges', '1') == '1',
        'initiatives': request.args.get('show_initiatives', '1') == '1',
        'systems': request.args.get('show_systems', '1') == '1',
        'kpis': request.args.get('show_kpis', '1') == '1',
    }

    return render_template('workspace/index.html',
                          org_name=org_name,
                          spaces=spaces,
                          value_types=value_types,
                          governance_bodies=governance_bodies,
                          selected_governance_body_ids=selected_governance_body_ids,
                          show_archived=show_archived,
                          show_levels=show_levels)


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
        elif value_type.kind == 'level':
            form.qualitative_level.choices = [
                ('', 'Select...'),
                ('1', '● (Low)'),
                ('2', '●● (Medium)'),
                ('3', '●●● (High)')
            ]
        elif value_type.kind == 'sentiment':
            form.qualitative_level.choices = [
                ('', 'Select...'),
                ('1', '☹️ (Negative)'),
                ('2', '😐 (Neutral)'),
                ('3', '😊 (Positive)')
            ]

    # Check if KPI is archived
    if kpi.is_archived:
        flash('This KPI is archived and cannot accept new contributions. Please unarchive it first if you need to add data.', 'warning')
        return redirect(url_for('workspace.index'))

    if form.validate_on_submit():
        contributor_name = form.contributor_name.data
        entry_mode = request.form.get('entry_mode', 'contributing')  # 'new_data' or 'contributing'

        # Check if this is "new data" mode (time evolved)
        if entry_mode == 'new_data':
            # Auto-create snapshot before replacing data
            try:
                from datetime import datetime, date
                snapshot_label = f"Auto: Before update by {contributor_name}"

                # Create snapshot for this specific KPI cell
                # Use allow_duplicates=True so multiple snapshots can be created on same day
                snapshot = SnapshotService.create_kpi_snapshot(
                    config_id=config.id,
                    snapshot_date=date.today(),
                    label=snapshot_label,
                    user_id=current_user.id,
                    allow_duplicates=True  # Always create new snapshot for auto-snapshots
                )

                if snapshot:
                    flash(f'Snapshot created: {snapshot.snapshot_label} (value: {snapshot.get_value()})', 'info')

                # Delete ALL existing contributions for this cell
                Contribution.query.filter_by(
                    kpi_value_type_config_id=config.id
                ).delete()

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
                db.session.commit()

                flash(f'Previous value saved in snapshot. New value entered by {contributor_name}', 'success')
                return redirect(url_for('workspace.kpi_cell_detail', kpi_id=kpi_id, vt_id=vt_id))

            except Exception as e:
                db.session.rollback()
                flash(f'Error creating snapshot: {str(e)}', 'danger')
                return redirect(url_for('workspace.kpi_cell_detail', kpi_id=kpi_id, vt_id=vt_id))

        # Normal mode: contributing to current period
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
    is_public = request.form.get('is_public') == 'true'

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
            user_id=current_user.id,
            is_public=is_public
        )

        visibility = "Public" if is_public else "Private"
        flash(f'{visibility} snapshot created: {result["kpi_snapshots"]} KPI values, '
              f'{result["rollup_snapshots"]} rollup values captured for {snapshot_date.isoformat()}',
              'success')

        if result['skipped'] > 0:
            flash(f'{result["skipped"]} KPIs skipped (no consensus data)', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating snapshot: {str(e)}', 'danger')

    return redirect(url_for('workspace.list_snapshots'))


@bp.route('/snapshots/list')
@login_required
@organization_required
def list_snapshots():
    """List all available snapshots for the organization"""
    org_id = session.get('organization_id')

    # Get filter parameters
    show_private = request.args.get('show_private', '1') == '1'
    show_public = request.args.get('show_public', '1') == '1'

    try:
        # Get all snapshots with full details
        snapshots = SnapshotService.get_all_snapshots(
            org_id,
            user_id=current_user.id,
            show_private=show_private,
            show_public=show_public
        )

        # Format for template
        snapshots_info = []
        for snap in snapshots:
            snapshots_info.append({
                'batch_id': snap['snapshot_batch_id'],
                'date': snap['snapshot_date'].isoformat(),
                'created_at': snap['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp': snap['created_at'].isoformat(),
                'label': snap['snapshot_label'],
                'kpi_count': snap['kpi_count'],
                'formatted_date': snap['snapshot_date'].strftime('%Y-%m-%d (%A)'),
                'formatted_time': snap['created_at'].strftime('%H:%M:%S'),
                'is_public': snap['is_public'],
                'owner_user_id': snap['owner_user_id'],
                'owner_name': snap['owner_name'],
                'is_owner': snap['owner_user_id'] == current_user.id
            })

        return render_template('workspace/snapshots.html',
                             snapshots=snapshots_info,
                             organization_name=session.get('organization_name'),
                             show_private=show_private,
                             show_public=show_public,
                             current_user_id=current_user.id)

    except Exception as e:
        flash(f'Error loading snapshots: {str(e)}', 'danger')
        return redirect(url_for('workspace.index'))


@bp.route('/snapshots/view/<batch_id>')
@login_required
@organization_required
def view_snapshot(batch_id):
    """
    View workspace state as of a specific snapshot batch.

    Shows historical values instead of current values.
    """
    org_id = session.get('organization_id')

    # Get snapshot info from batch
    sample = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()
    if not sample:
        flash('Snapshot not found', 'danger')
        return redirect(url_for('workspace.list_snapshots'))

    view_date = sample.snapshot_date

    # Get spaces and value types (current structure)
    spaces = Space.query.filter_by(organization_id=org_id).order_by(
        Space.display_order, Space.name
    ).all()

    value_types = ValueType.query.filter_by(
        organization_id=org_id,
        is_active=True
    ).order_by(ValueType.display_order).all()

    # Get governance bodies for filtering
    governance_bodies = GovernanceBody.query.filter_by(
        organization_id=org_id,
        is_active=True
    ).order_by(GovernanceBody.display_order).all()

    # Get level visibility controls (default all visible)
    show_levels = {
        'spaces': request.args.get('show_spaces', '1') == '1',
        'challenges': request.args.get('show_challenges', '1') == '1',
        'initiatives': request.args.get('show_initiatives', '1') == '1',
        'systems': request.args.get('show_systems', '1') == '1',
        'kpis': request.args.get('show_kpis', '1') == '1',
    }

    return render_template('workspace/index.html',
                         spaces=spaces,
                         value_types=value_types,
                         governance_bodies=governance_bodies,
                         selected_governance_body_ids=[],
                         show_archived=False,
                         show_levels=show_levels,
                         organization_name=session.get('organization_name'),
                         snapshot_date=view_date,
                         is_historical_view=True)


@bp.route('/snapshots/compare')
@login_required
@organization_required
def compare_snapshots():
    """Compare two snapshots side-by-side"""
    org_id = session.get('organization_id')

    # Get batch_id parameters
    batch_id1 = request.args.get('batch_id1')
    batch_id2 = request.args.get('batch_id2', 'current')

    if not batch_id1:
        flash('Please select a snapshot to compare', 'warning')
        return redirect(url_for('workspace.list_snapshots'))

    # Get first snapshot info
    sample1 = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id1).first()
    if not sample1:
        flash('Snapshot not found', 'danger')
        return redirect(url_for('workspace.list_snapshots'))

    date1 = sample1.snapshot_date
    datetime1 = sample1.created_at
    label1 = sample1.snapshot_label

    # Get second snapshot info (or use current)
    if batch_id2 != 'current':
        sample2 = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id2).first()
        if not sample2:
            flash('Second snapshot not found', 'danger')
            return redirect(url_for('workspace.list_snapshots'))
        date2 = sample2.snapshot_date
        datetime2 = sample2.created_at
        label2 = sample2.snapshot_label
    else:
        date2 = None
        datetime2 = None
        label2 = "Current"

    # Get all KPI configs for this organization
    configs = db.session.query(KPIValueTypeConfig).join(
        KPI
    ).join(
        InitiativeSystemLink
    ).join(Initiative).filter(
        Initiative.organization_id == org_id
    ).all()

    # Build comparison data
    comparisons = []
    for config in configs:
        # Get snapshot 1 value - match by batch_id
        snapshot1 = KPISnapshot.query.filter_by(
            kpi_value_type_config_id=config.id,
            snapshot_batch_id=batch_id1
        ).first()

        # Get snapshot 2 value (or current consensus)
        if batch_id2 != 'current':
            snapshot2 = KPISnapshot.query.filter_by(
                kpi_value_type_config_id=config.id,
                snapshot_batch_id=batch_id2
            ).first()
            value2 = snapshot2.get_value() if snapshot2 else None
        else:
            # Use current consensus - get contributions for this config
            contributions = Contribution.query.filter_by(
                kpi_value_type_config_id=config.id
            ).all()
            consensus = ConsensusService.calculate_consensus(contributions)
            value2 = consensus.get('value')

        value1 = snapshot1.get_value() if snapshot1 else None

        # Calculate change
        change = None
        percent_change = None
        if value1 is not None and value2 is not None:
            change = float(value2) - float(value1)
            if value1 != 0:
                percent_change = (change / float(value1)) * 100

        comparisons.append({
            'config': config,
            'kpi': config.kpi,
            'value_type': config.value_type,
            'value1': value1,
            'value2': value2,
            'change': change,
            'percent_change': percent_change
        })

    return render_template('workspace/compare_snapshots.html',
                         comparisons=comparisons,
                         date1=date1,
                         datetime1=datetime1,
                         date2=date2,
                         datetime2=datetime2,
                         label1=label1,
                         label2=label2,
                         organization_name=session.get('organization_name'))


@bp.route('/snapshots/<batch_id>/toggle-privacy', methods=['POST'])
@login_required
@organization_required
def toggle_snapshot_privacy(batch_id):
    """Toggle privacy status of a snapshot batch (private <-> public)"""
    org_id = session.get('organization_id')

    try:
        print(f"[DEBUG] Toggling privacy for batch_id: {batch_id}")

        # Get one snapshot from this batch to check ownership
        sample_snapshot = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()

        if not sample_snapshot:
            print(f"[DEBUG] Snapshot not found for batch_id: {batch_id}")
            return jsonify({'error': 'Snapshot not found'}), 404

        print(f"[DEBUG] Current is_public: {sample_snapshot.is_public}, owner: {sample_snapshot.owner_user_id}, current_user: {current_user.id}")

        # Check ownership
        if sample_snapshot.owner_user_id != current_user.id:
            print(f"[DEBUG] Ownership check failed: {sample_snapshot.owner_user_id} != {current_user.id}")
            return jsonify({'error': 'Only the snapshot owner can change privacy settings'}), 403

        # Toggle all KPI snapshots in this batch
        new_status = not sample_snapshot.is_public
        kpi_count = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).update({
            'is_public': new_status
        })

        # Toggle all rollup snapshots in this batch
        rollup_count = RollupSnapshot.query.filter_by(snapshot_batch_id=batch_id).update({
            'is_public': new_status
        })

        db.session.commit()

        print(f"[DEBUG] Toggled {kpi_count} KPI snapshots and {rollup_count} rollup snapshots to is_public={new_status}")

        return jsonify({
            'success': True,
            'is_public': new_status,
            'message': f'Snapshot is now {"public" if new_status else "private"}'
        })

    except Exception as e:
        db.session.rollback()


@bp.route('/snapshots/<batch_id>/delete', methods=['POST'])
@login_required
@organization_required
def delete_snapshot(batch_id):
    """Delete all snapshots in a batch"""
    try:
        # Get one snapshot from this batch to check ownership
        sample_snapshot = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).first()

        if not sample_snapshot:
            return jsonify({'error': 'Snapshot not found'}), 404

        # Check ownership
        if sample_snapshot.owner_user_id != current_user.id:
            return jsonify({'error': 'Only the snapshot owner can delete snapshots'}), 403

        # Delete all KPI snapshots in this batch
        kpi_count = KPISnapshot.query.filter_by(snapshot_batch_id=batch_id).delete()

        # Delete all rollup snapshots in this batch
        rollup_count = RollupSnapshot.query.filter_by(snapshot_batch_id=batch_id).delete()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Deleted snapshot batch ({kpi_count} KPI snapshots, {rollup_count} rollup snapshots)'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
        print(f"[DEBUG] Error toggling privacy: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
        from datetime import date
        limit = request.args.get('limit', 50, type=int)
        snapshots = SnapshotService.get_kpi_history(config_id, limit=limit)

        # Get the config and current consensus value
        config = KPIValueTypeConfig.query.get_or_404(config_id)
        consensus = ConsensusService.get_cell_value(config)

        # Format for chart: array of {date, value} objects
        # Reverse so oldest is first (better for chart display)
        # Use created_at timestamp to distinguish snapshots on the same day
        history = []
        for snapshot in reversed(snapshots):
            value = snapshot.get_value()
            if value is not None:  # Only include snapshots with actual values
                # Use full timestamp for snapshots on same day
                date_label = snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S')
                history.append({
                    'date': date_label,
                    'value': float(value),
                    'label': snapshot.snapshot_label
                })

        # Add current value as the latest point (if it exists and differs from last snapshot)
        if consensus and consensus.get('status') != 'no_data':
            current_value = consensus.get('value')
            if current_value is not None:
                # Use current timestamp for current value
                from datetime import datetime
                current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                history.append({
                    'date': current_time,
                    'value': float(current_value),
                    'label': 'Current'
                })

        return jsonify({
            'history': history,
            'count': len(history)
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
        org_id = session.get('organization_id')

        # Check permission to view comments
        if not current_user.can_view_comments(org_id):
            return jsonify({'error': 'You do not have permission to view comments'}), 403

        include_resolved = request.args.get('include_resolved', 'true').lower() == 'true'
        comments = CommentService.get_comments_for_cell(config_id, include_resolved=include_resolved)

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
        org_id = session.get('organization_id')

        # Check permission to add comments
        if not current_user.can_add_comments(org_id):
            return jsonify({'error': 'You do not have permission to add comments'}), 403

        data = request.get_json()
        comment_text = data.get('comment_text', '').strip()
        parent_comment_id = data.get('parent_comment_id')

        if not comment_text:
            return jsonify({'error': 'Comment text is required'}), 400

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
        total_count = CommentService.get_unread_mentions_count(current_user.id)

        return jsonify({
            'mentions': [m.to_dict() for m in mentions],
            'count': len(mentions),  # Number of mentions returned (limited)
            'total_count': total_count  # Total unread mentions count
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

        # Build query
        query = db.session.query(User).join(
            UserOrganizationMembership
        ).filter(
            UserOrganizationMembership.organization_id == org_id
        )

        # Filter by search term if provided
        if search_term:
            query = query.filter(
                db.or_(
                    User.login.ilike(f'%{search_term}%'),
                    User.display_name.ilike(f'%{search_term}%')
                )
            )

        # Get results (limit 10)
        users = query.order_by(User.display_name).limit(10).all()

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


@bp.route('/search')
@login_required
@organization_required
def search_page():
    """Search results page"""
    org_id = session.get('organization_id')
    org_name = session.get('organization_name')
    query = request.args.get('q', '').strip()

    if not query:
        return render_template('workspace/search.html',
                             organization_name=org_name,
                             query='',
                             results={})

    # Search across all entities
    results = {
        'spaces': [],
        'challenges': [],
        'initiatives': [],
        'systems': [],
        'kpis': [],
        'value_types': [],
        'comments': []
    }

    search_pattern = f'%{query}%'

    # Search Spaces
    spaces = Space.query.filter(
        Space.organization_id == org_id,
        db.or_(
            Space.name.ilike(search_pattern),
            Space.description.ilike(search_pattern)
        )
    ).all()
    results['spaces'] = [{'id': s.id, 'name': s.name, 'description': s.description} for s in spaces]

    # Search Challenges
    challenges = Challenge.query.join(Space).filter(
        Space.organization_id == org_id,
        db.or_(
            Challenge.name.ilike(search_pattern),
            Challenge.description.ilike(search_pattern)
        )
    ).all()
    results['challenges'] = [{'id': c.id, 'name': c.name, 'description': c.description, 'space': c.space.name} for c in challenges]

    # Search Initiatives
    initiatives = Initiative.query.filter(
        Initiative.organization_id == org_id,
        db.or_(
            Initiative.name.ilike(search_pattern),
            Initiative.description.ilike(search_pattern)
        )
    ).all()
    results['initiatives'] = [{'id': i.id, 'name': i.name, 'description': i.description} for i in initiatives]

    # Search Systems
    systems = System.query.filter(
        System.organization_id == org_id,
        db.or_(
            System.name.ilike(search_pattern),
            System.description.ilike(search_pattern)
        )
    ).all()
    results['systems'] = [{'id': s.id, 'name': s.name, 'description': s.description} for s in systems]

    # Search KPIs
    kpis = db.session.query(KPI).join(
        InitiativeSystemLink
    ).join(Initiative).filter(
        Initiative.organization_id == org_id,
        db.or_(
            KPI.name.ilike(search_pattern),
            KPI.description.ilike(search_pattern)
        )
    ).all()
    results['kpis'] = [{
        'id': k.id,
        'name': k.name,
        'description': k.description,
        'initiative': k.initiative_system_link.initiative.name if k.initiative_system_link else '',
        'system': k.initiative_system_link.system.name if k.initiative_system_link else ''
    } for k in kpis]

    # Search Value Types
    value_types = ValueType.query.filter(
        ValueType.organization_id == org_id,
        db.or_(
            ValueType.name.ilike(search_pattern),
            ValueType.unit_label.ilike(search_pattern)
        )
    ).all()
    results['value_types'] = [{'id': v.id, 'name': v.name, 'unit_label': v.unit_label, 'kind': v.kind} for v in value_types]

    # Search Comments
    comments = db.session.query(CellComment).join(
        KPIValueTypeConfig
    ).join(KPI).join(
        InitiativeSystemLink
    ).join(Initiative).filter(
        Initiative.organization_id == org_id,
        CellComment.comment_text.ilike(search_pattern)
    ).limit(50).all()
    results['comments'] = [{
        'id': c.id,
        'text': c.comment_text[:200],
        'user': c.user.display_name if c.user else 'Unknown',
        'kpi': c.config.kpi.name if c.config and c.config.kpi else 'Unknown',
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''
    } for c in comments]

    # Count totals
    total = sum(len(results[key]) for key in results)

    return render_template('workspace/search.html',
                         organization_name=org_name,
                         query=query,
                         results=results,
                         total=total)
