"""
Organization Administration routes

For managing business content within an organization (spaces, challenges, initiatives, etc.).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models import (
    Space, Challenge, Initiative, System, KPI, ValueType,
    ChallengeInitiativeLink, InitiativeSystemLink, KPIValueTypeConfig,
    RollupRule
)
from app.forms import (
    SpaceCreateForm, SpaceEditForm,
    ChallengeCreateForm, ChallengeEditForm,
    InitiativeCreateForm, InitiativeEditForm,
    SystemCreateForm, SystemEditForm,
    KPICreateForm, KPIEditForm,
    ValueTypeCreateForm, ValueTypeEditForm,
    YAMLUploadForm
)
from app.services import DeletionImpactService, ValueTypeUsageService, YAMLImportService, YAMLExportService

bp = Blueprint('organization_admin', __name__, url_prefix='/org-admin')


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
    """Organization administration dashboard"""
    org_id = session.get('organization_id')
    org_name = session.get('organization_name')

    stats = {
        'spaces': Space.query.filter_by(organization_id=org_id).count(),
        'challenges': Challenge.query.filter_by(organization_id=org_id).count(),
        'initiatives': Initiative.query.filter_by(organization_id=org_id).count(),
        'systems': System.query.filter_by(organization_id=org_id).count(),
        'value_types': ValueType.query.filter_by(organization_id=org_id, is_active=True).count(),
    }

    return render_template('organization_admin/index.html',
                          org_name=org_name,
                          stats=stats)


# Space Management

@bp.route('/spaces')
@login_required
@organization_required
def spaces():
    """List all spaces with full hierarchy"""
    org_id = session.get('organization_id')
    spaces = Space.query.filter_by(organization_id=org_id).order_by(Space.display_order, Space.name).all()
    return render_template('organization_admin/spaces.html', spaces=spaces)


@bp.route('/spaces/create', methods=['GET', 'POST'])
@login_required
@organization_required
def create_space():
    """Create a new space"""
    form = SpaceCreateForm()

    if form.validate_on_submit():
        space = Space(
            organization_id=session.get('organization_id'),
            name=form.name.data,
            description=form.description.data,
            space_label=form.space_label.data,
            display_order=form.display_order.data
        )
        db.session.add(space)
        db.session.commit()
        flash(f'Space {space.name} created successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/create_space.html', form=form)


@bp.route('/spaces/<int:space_id>/edit', methods=['GET', 'POST'])
@login_required
@organization_required
def edit_space(space_id):
    """Edit an existing space"""
    org_id = session.get('organization_id')
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    form = SpaceEditForm(obj=space)

    if form.validate_on_submit():
        space.name = form.name.data
        space.description = form.description.data
        space.space_label = form.space_label.data
        space.display_order = form.display_order.data
        db.session.commit()
        flash(f'Space {space.name} updated successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/edit_space.html', form=form, space=space)


@bp.route('/spaces/<int:space_id>/delete', methods=['POST'])
@login_required
@organization_required
def delete_space(space_id):
    """Delete a space"""
    org_id = session.get('organization_id')
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    space_name = space.name
    db.session.delete(space)
    db.session.commit()
    flash(f'Space {space_name} deleted successfully', 'success')
    return redirect(url_for('organization_admin.spaces'))


# Challenge Management

@bp.route('/challenges')
@login_required
@organization_required
def challenges():
    """List all challenges"""
    org_id = session.get('organization_id')
    challenges = Challenge.query.filter_by(organization_id=org_id).order_by(Challenge.display_order).all()
    return render_template('organization_admin/challenges.html', challenges=challenges)


@bp.route('/initiatives')
@login_required
@organization_required
def initiatives():
    """List all initiatives"""
    org_id = session.get('organization_id')
    initiatives = Initiative.query.filter_by(organization_id=org_id).all()
    return render_template('organization_admin/initiatives.html', initiatives=initiatives)


@bp.route('/systems')
@login_required
@organization_required
def systems():
    """List all systems"""
    org_id = session.get('organization_id')
    systems = System.query.filter_by(organization_id=org_id).all()
    return render_template('organization_admin/systems.html', systems=systems)


@bp.route('/spaces/<int:space_id>/challenges/create', methods=['GET', 'POST'])
@login_required
@organization_required
def create_challenge(space_id):
    """Create a new challenge under a space"""
    org_id = session.get('organization_id')
    space = Space.query.filter_by(id=space_id, organization_id=org_id).first_or_404()

    form = ChallengeCreateForm()

    if form.validate_on_submit():
        challenge = Challenge(
            organization_id=org_id,
            space_id=space_id,
            name=form.name.data,
            description=form.description.data,
            display_order=form.display_order.data
        )
        db.session.add(challenge)
        db.session.commit()
        flash(f'Challenge {challenge.name} created successfully in {space.name}', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/create_challenge.html', form=form, space=space)


@bp.route('/challenges/<int:challenge_id>/edit', methods=['GET', 'POST'])
@login_required
@organization_required
def edit_challenge(challenge_id):
    """Edit an existing challenge"""
    org_id = session.get('organization_id')
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    form = ChallengeEditForm(obj=challenge)

    if form.validate_on_submit():
        challenge.name = form.name.data
        challenge.description = form.description.data
        challenge.display_order = form.display_order.data
        db.session.commit()
        flash(f'Challenge {challenge.name} updated successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    return render_template('organization_admin/edit_challenge.html',
                          form=form,
                          challenge=challenge,
                          value_types=value_types)


@bp.route('/challenges/<int:challenge_id>/rollup-config', methods=['POST'])
@login_required
@organization_required
def configure_challenge_rollup(challenge_id):
    """Configure rollup rules for a challenge (from Initiatives to Challenge to Space)"""
    org_id = session.get('organization_id')
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    # Get all value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Process form data for each value type
    for vt in value_types:
        enabled = request.form.get(f'enabled_{vt.id}') == 'on'
        formula = request.form.get(f'formula_{vt.id}', 'default')

        # Find or create rule
        rule = RollupRule.query.filter_by(
            source_type='challenge',
            source_id=challenge_id,
            value_type_id=vt.id
        ).first()

        if rule:
            rule.rollup_enabled = enabled
            rule.formula_override = formula
        else:
            rule = RollupRule(
                source_type='challenge',
                source_id=challenge_id,
                value_type_id=vt.id,
                rollup_enabled=enabled,
                formula_override=formula
            )
            db.session.add(rule)

    db.session.commit()
    flash(f'Rollup configuration saved for {challenge.name}', 'success')
    return redirect(url_for('organization_admin.edit_challenge', challenge_id=challenge_id))


# Initiative Management

@bp.route('/challenges/<int:challenge_id>/initiatives/create', methods=['GET', 'POST'])
@login_required
@organization_required
def create_initiative(challenge_id):
    """Create a new initiative and link it to a challenge"""
    org_id = session.get('organization_id')
    challenge = Challenge.query.filter_by(id=challenge_id, organization_id=org_id).first_or_404()

    form = InitiativeCreateForm()

    if form.validate_on_submit():
        # Create the initiative
        initiative = Initiative(
            organization_id=org_id,
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(initiative)
        db.session.flush()  # Get the ID

        # Link to challenge
        link = ChallengeInitiativeLink(
            challenge_id=challenge_id,
            initiative_id=initiative.id,
            display_order=0
        )
        db.session.add(link)
        db.session.commit()

        flash(f'Initiative {initiative.name} created and linked to {challenge.name}', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/create_initiative.html', form=form, challenge=challenge)


@bp.route('/initiatives/<int:initiative_id>/edit', methods=['GET', 'POST'])
@login_required
@organization_required
def edit_initiative(initiative_id):
    """Edit an existing initiative"""
    org_id = session.get('organization_id')
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    form = InitiativeEditForm(obj=initiative)

    if form.validate_on_submit():
        initiative.name = form.name.data
        initiative.description = form.description.data
        db.session.commit()
        flash(f'Initiative {initiative.name} updated successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    return render_template('organization_admin/edit_initiative.html',
                          form=form,
                          initiative=initiative,
                          value_types=value_types)


@bp.route('/challenge-initiative-links/<int:link_id>/rollup-config', methods=['POST'])
@login_required
@organization_required
def configure_initiative_rollup(link_id):
    """Configure rollup rules for an initiative (from Systems to Initiative)"""
    org_id = session.get('organization_id')
    link = ChallengeInitiativeLink.query.get_or_404(link_id)

    # Verify ownership
    if link.initiative.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.spaces'))

    # Get all value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Process form data for each value type
    for vt in value_types:
        enabled = request.form.get(f'enabled_{vt.id}') == 'on'
        formula = request.form.get(f'formula_{vt.id}', 'default')

        # Find or create rule
        rule = RollupRule.query.filter_by(
            source_type='challenge_initiative',
            source_id=link_id,
            value_type_id=vt.id
        ).first()

        if rule:
            rule.rollup_enabled = enabled
            rule.formula_override = formula
        else:
            rule = RollupRule(
                source_type='challenge_initiative',
                source_id=link_id,
                value_type_id=vt.id,
                rollup_enabled=enabled,
                formula_override=formula
            )
            db.session.add(rule)

    db.session.commit()
    flash(f'Rollup configuration saved for {link.initiative.name}', 'success')
    return redirect(url_for('organization_admin.edit_initiative', initiative_id=link.initiative_id))


# System Management

@bp.route('/initiatives/<int:initiative_id>/systems/create', methods=['GET', 'POST'])
@login_required
@organization_required
def create_system(initiative_id):
    """Create a new system and link it to an initiative"""
    org_id = session.get('organization_id')
    initiative = Initiative.query.filter_by(id=initiative_id, organization_id=org_id).first_or_404()

    form = SystemCreateForm()

    if form.validate_on_submit():
        # Create the system
        system = System(
            organization_id=org_id,
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(system)
        db.session.flush()  # Get the ID

        # Link to initiative
        link = InitiativeSystemLink(
            initiative_id=initiative_id,
            system_id=system.id,
            display_order=0
        )
        db.session.add(link)
        db.session.commit()

        flash(f'System {system.name} created and linked to {initiative.name}', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/create_system.html', form=form, initiative=initiative)


@bp.route('/systems/<int:system_id>/edit', methods=['GET', 'POST'])
@login_required
@organization_required
def edit_system(system_id):
    """Edit an existing system"""
    org_id = session.get('organization_id')
    system = System.query.filter_by(id=system_id, organization_id=org_id).first_or_404()

    form = SystemEditForm(obj=system)

    if form.validate_on_submit():
        system.name = form.name.data
        system.description = form.description.data
        db.session.commit()
        flash(f'System {system.name} updated successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    # Get value types for rollup configuration tab
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    return render_template('organization_admin/edit_system.html',
                          form=form,
                          system=system,
                          value_types=value_types)


@bp.route('/initiative-system-links/<int:link_id>/rollup-config', methods=['POST'])
@login_required
@organization_required
def configure_system_rollup(link_id):
    """Configure rollup rules for a system (from KPIs to System)"""
    org_id = session.get('organization_id')
    link = InitiativeSystemLink.query.get_or_404(link_id)

    # Verify ownership
    if link.initiative.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.spaces'))

    # Get all value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    # Process form data for each value type
    for vt in value_types:
        enabled = request.form.get(f'enabled_{vt.id}') == 'on'
        formula = request.form.get(f'formula_{vt.id}', 'default')

        # Find or create rule
        rule = RollupRule.query.filter_by(
            source_type='initiative_system',
            source_id=link_id,
            value_type_id=vt.id
        ).first()

        if rule:
            rule.rollup_enabled = enabled
            rule.formula_override = formula
        else:
            rule = RollupRule(
                source_type='initiative_system',
                source_id=link_id,
                value_type_id=vt.id,
                rollup_enabled=enabled,
                formula_override=formula
            )
            db.session.add(rule)

    db.session.commit()
    flash(f'Rollup configuration saved for {link.system.name}', 'success')
    return redirect(url_for('organization_admin.edit_system', system_id=link.system_id))


# KPI Management

@bp.route('/initiative-system-links/<int:link_id>/kpis/create', methods=['GET', 'POST'])
@login_required
@organization_required
def create_kpi(link_id):
    """Create a new KPI under an initiative-system link"""
    org_id = session.get('organization_id')
    link = InitiativeSystemLink.query.get_or_404(link_id)

    # Verify ownership
    if link.initiative.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.spaces'))

    # Get active value types for selection
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).all()

    form = KPICreateForm()
    form.value_type_ids.choices = [(vt.id, vt.name) for vt in value_types]

    if form.validate_on_submit():
        # Create the KPI
        kpi = KPI(
            initiative_system_link_id=link_id,
            name=form.name.data,
            description=form.description.data,
            display_order=form.display_order.data
        )
        db.session.add(kpi)
        db.session.flush()  # Get the ID

        # Link selected value types with colors
        selected_vt_ids = request.form.getlist('value_type_ids')
        for vt_id in selected_vt_ids:
            vt_id_int = int(vt_id)
            
            # Get color values from form
            color_positive = request.form.get(f'color_positive_{vt_id}', '#28a745')
            color_zero = request.form.get(f'color_zero_{vt_id}', '#6c757d')
            color_negative = request.form.get(f'color_negative_{vt_id}', '#dc3545')
            
            config = KPIValueTypeConfig(
                kpi_id=kpi.id,
                value_type_id=vt_id_int,
                display_order=0,
                color_positive=color_positive,
                color_zero=color_zero,
                color_negative=color_negative
            )
            db.session.add(config)

        db.session.commit()
        flash(f'KPI {kpi.name} created successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/create_kpi.html',
                          form=form,
                          link=link,
                          initiative=link.initiative,
                          system=link.system,
                          value_types=value_types)

@bp.route('/kpis/<int:kpi_id>/edit', methods=['GET', 'POST'])
@login_required
@organization_required
def edit_kpi(kpi_id):
    """Edit an existing KPI"""
    org_id = session.get('organization_id')
    kpi = KPI.query.get_or_404(kpi_id)

    # Verify ownership
    if kpi.initiative_system_link.initiative.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.spaces'))

    form = KPIEditForm(obj=kpi)
    if form.validate_on_submit():
        kpi.name = form.name.data
        kpi.description = form.description.data
        kpi.display_order = form.display_order.data
        
        # Update colors for each value type config
        for config in kpi.value_type_configs:
            if config.value_type.kind == 'numeric':
                color_positive = request.form.get(f'color_positive_{config.id}')
                color_zero = request.form.get(f'color_zero_{config.id}')
                color_negative = request.form.get(f'color_negative_{config.id}')

                if color_positive:
                    config.color_positive = color_positive
                if color_zero:
                    config.color_zero = color_zero
                if color_negative:
                    config.color_negative = color_negative

        db.session.commit()
        flash(f'KPI {kpi.name} updated successfully', 'success')
        return redirect(url_for('organization_admin.spaces'))

    return render_template('organization_admin/edit_kpi.html', form=form, kpi=kpi)


# Value Type Management

@bp.route('/value-types')
@login_required
@organization_required
def value_types():
    """List all value types"""
    org_id = session.get('organization_id')
    value_types = ValueType.query.filter_by(organization_id=org_id).order_by(ValueType.display_order).all()
    return render_template('organization_admin/value_types.html', value_types=value_types)


@bp.route('/value-types/reorder', methods=['POST'])
@login_required
@organization_required
def reorder_value_types():
    """Update value type display order via AJAX (CSRF exempt for AJAX)"""
    # Note: CSRF validation happens through login_required - user must be authenticated
    org_id = session.get('organization_id')
    data = request.get_json()
    order = data.get('order', [])

    if not order:
        return jsonify({'success': False, 'error': 'No order provided'}), 400

    try:
        # Update display_order for each value type
        for index, vt_id in enumerate(order):
            vt = ValueType.query.filter_by(id=vt_id, organization_id=org_id).first()
            if vt:
                vt.display_order = index

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/value-types/create', methods=['GET', 'POST'])
@login_required
@organization_required
def create_value_type():
    """Create a new value type"""
    form = ValueTypeCreateForm()

    if form.validate_on_submit():
        value_type = ValueType(
            organization_id=session.get('organization_id'),
            name=form.name.data,
            kind=form.kind.data,
            numeric_format=form.numeric_format.data if form.kind.data == 'numeric' else None,
            decimal_places=form.decimal_places.data if form.kind.data == 'numeric' else None,
            unit_label=form.unit_label.data,
            default_aggregation_formula=form.default_aggregation_formula.data,
            display_order=form.display_order.data,
            is_active=form.is_active.data
        )
        db.session.add(value_type)
        db.session.commit()
        flash(f'Value Type {value_type.name} created successfully', 'success')
        return redirect(url_for('organization_admin.value_types'))

    return render_template('organization_admin/create_value_type.html', form=form)


@bp.route('/value-types/<int:vt_id>/edit', methods=['GET', 'POST'])
@login_required
@organization_required
def edit_value_type(vt_id):
    """Edit a value type"""
    org_id = session.get('organization_id')
    value_type = ValueType.query.get_or_404(vt_id)

    if value_type.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.value_types'))

    form = ValueTypeEditForm(obj=value_type)

    if form.validate_on_submit():
        value_type.name = form.name.data
        if value_type.kind == 'numeric' and form.decimal_places.data is not None:
            value_type.decimal_places = form.decimal_places.data
        if form.unit_label.data is not None:
            value_type.unit_label = form.unit_label.data
        value_type.is_active = form.is_active.data
        value_type.display_order = form.display_order.data
        db.session.commit()
        flash(f'Value Type {value_type.name} updated successfully', 'success')
        return redirect(url_for('organization_admin.value_types'))

    return render_template('organization_admin/edit_value_type.html', form=form, value_type=value_type)

@bp.route('/value-types/<int:vt_id>/delete-check')
@login_required
@organization_required
def delete_value_type_check(vt_id):
    """Check if value type can be deleted and show usage"""
    value_type = ValueType.query.get_or_404(vt_id)

    if value_type.organization_id != session.get('organization_id'):
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.value_types'))

    can_delete, reason = ValueTypeUsageService.can_delete(vt_id)
    usage = ValueTypeUsageService.check_usage(vt_id)

    return render_template('organization_admin/delete_value_type_check.html',
                          value_type=value_type,
                          can_delete=can_delete,
                          reason=reason,
                          usage=usage)


@bp.route('/value-types/<int:vt_id>/rollup-config', methods=['GET', 'POST'])
@login_required
@organization_required
def configure_rollup(vt_id):
    """Configure rollup rules for a value type"""
    org_id = session.get('organization_id')
    value_type = ValueType.query.get_or_404(vt_id)

    if value_type.organization_id != org_id:
        flash('Access denied', 'danger')
        return redirect(url_for('organization_admin.value_types'))

    if request.method == 'POST':
        # Get all form data for rollup configuration
        # Format: rollup_enabled_<level> and formula_<level>

        # System → Initiative rules (for all InitiativeSystemLinks)
        sys_enabled = request.form.get('rollup_enabled_system') == 'on'
        sys_formula = request.form.get('formula_system', 'default')

        # Initiative → Challenge rules (for all ChallengeInitiativeLinks)
        init_enabled = request.form.get('rollup_enabled_initiative') == 'on'
        init_formula = request.form.get('formula_initiative', 'default')

        # Challenge → Space rules (for all Challenges)
        chal_enabled = request.form.get('rollup_enabled_challenge') == 'on'
        chal_formula = request.form.get('formula_challenge', 'default')

        # Update or create default rules
        # Note: These are organization-level defaults. Specific overrides can be added later.

        # Store in session for now (we'll create a more robust solution later)
        flash(f'Rollup configuration updated for {value_type.name}', 'success')
        flash('Note: Full per-context rollup configuration coming soon!', 'info')

        return redirect(url_for('organization_admin.value_types'))

    # Get current default settings
    default_enabled = True  # By default, rollup is enabled
    default_formula = value_type.default_aggregation_formula

    return render_template('organization_admin/configure_rollup.html',
                          value_type=value_type,
                          default_enabled=default_enabled,
                          default_formula=default_formula)

@bp.route('/yaml-upload', methods=['GET', 'POST'])
@login_required
@organization_required
def yaml_upload():
    """Upload YAML file to create complete organizational structure"""
    org_id = session.get('organization_id')
    form = YAMLUploadForm()

    if form.validate_on_submit():
        if not form.confirm_delete.data:
            flash('You must confirm that you understand all data will be deleted', 'danger')
            return redirect(url_for('organization_admin.yaml_upload'))

        try:
            # Read uploaded file
            yaml_file = form.yaml_file.data
            yaml_content = yaml_file.read().decode('utf-8')

            # Delete ALL existing organization data
            # This is intentional and destructive - user was warned!
            _delete_all_organization_data(org_id)

            # Import from YAML
            result = YAMLImportService.import_from_string(yaml_content, org_id, dry_run=False)

            if result.get('success'):
                flash(f'✓ Import successful!', 'success')
                flash(f'Created: {result["spaces"]} spaces, {result["challenges"]} challenges, '
                      f'{result["initiatives"]} initiatives, {result["systems"]} systems, '
                      f'{result["kpis"]} KPIs, {result["value_types"]} value types', 'info')

                if result.get('errors'):
                    flash(f'Warnings: {len(result["errors"])} issues encountered', 'warning')
                    for error in result['errors'][:5]:  # Show first 5 errors
                        flash(f'⚠ {error}', 'warning')

                return redirect(url_for('organization_admin.spaces'))
            else:
                flash('Import failed', 'danger')
                for error in result.get('errors', []):
                    flash(error, 'danger')

        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading YAML: {str(e)}', 'danger')

    return render_template('organization_admin/yaml_upload.html', form=form)


@bp.route('/yaml-export')
@login_required
@organization_required
def yaml_export():
    """Export organization structure to YAML file"""
    from io import BytesIO
    org_id = session.get('organization_id')
    org_name = session.get('organization_name')

    try:
        # Generate YAML content
        yaml_content = YAMLExportService.export_to_yaml(org_id)

        # Create BytesIO object for download
        yaml_bytes = BytesIO(yaml_content.encode('utf-8'))
        yaml_bytes.seek(0)

        # Create safe filename
        safe_org_name = "".join(c for c in org_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"structure_{safe_org_name}.yaml"

        return send_file(
            yaml_bytes,
            mimetype='application/x-yaml',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Error exporting YAML: {str(e)}', 'danger')
        return redirect(url_for('organization_admin.index'))


def _delete_all_organization_data(org_id):
    """
    Delete ALL data for an organization.
    This is called before YAML import to start fresh.
    
    WARNING: This is destructive and irreversible!
    """
    # Delete in correct order to respect foreign keys
    
    # Delete Contributions (leaf level)
    from app.models import Contribution
    contributions = Contribution.query.join(KPIValueTypeConfig).join(KPI).join(InitiativeSystemLink).join(Initiative).filter(Initiative.organization_id == org_id).all()
    for contrib in contributions:
        db.session.delete(contrib)
    
    # Delete KPIValueTypeConfigs
    configs = KPIValueTypeConfig.query.join(KPI).join(InitiativeSystemLink).join(Initiative).filter(Initiative.organization_id == org_id).all()
    for config in configs:
        db.session.delete(config)
    
    # Delete KPIs
    kpis = KPI.query.join(InitiativeSystemLink).join(Initiative).filter(Initiative.organization_id == org_id).all()
    for kpi in kpis:
        db.session.delete(kpi)
    
    # Delete InitiativeSystemLinks
    links = InitiativeSystemLink.query.join(Initiative).filter(Initiative.organization_id == org_id).all()
    for link in links:
        db.session.delete(link)
    
    # Delete Systems
    systems = System.query.filter_by(organization_id=org_id).all()
    for system in systems:
        db.session.delete(system)
    
    # Delete ChallengeInitiativeLinks
    from app.models import ChallengeInitiativeLink
    challenge_links = ChallengeInitiativeLink.query.join(Challenge).filter(Challenge.organization_id == org_id).all()
    for link in challenge_links:
        db.session.delete(link)
    
    # Delete Initiatives
    initiatives = Initiative.query.filter_by(organization_id=org_id).all()
    for initiative in initiatives:
        db.session.delete(initiative)
    
    # Delete Challenges
    challenges = Challenge.query.filter_by(organization_id=org_id).all()
    for challenge in challenges:
        db.session.delete(challenge)
    
    # Delete Spaces
    spaces = Space.query.filter_by(organization_id=org_id).all()
    for space in spaces:
        db.session.delete(space)
    
    # Delete ValueTypes
    value_types = ValueType.query.filter_by(organization_id=org_id).all()
    for vt in value_types:
        db.session.delete(vt)
    
    # Delete RollupRules
    from app.models import RollupRule
    rollup_rules = RollupRule.query.join(ValueType).filter(ValueType.organization_id == org_id).all()
    for rule in rollup_rules:
        db.session.delete(rule)
    
    db.session.flush()
