"""
Workspace routes

Main tree/grid navigation and data entry.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models import (
    Space, Challenge, Initiative, System, KPI, ValueType,
    KPIValueTypeConfig, Contribution
)
from app.forms import ContributionForm
from app.services import ConsensusService, AggregationService

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
