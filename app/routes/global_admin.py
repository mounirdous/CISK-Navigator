"""
Global Administration routes

For managing users and organizations (global admins only).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models import User, Organization, UserOrganizationMembership
from app.forms import UserCreateForm, UserEditForm, OrganizationCreateForm, OrganizationEditForm, OrganizationCloneForm
from app.services import DeletionImpactService, OrganizationCloneService

bp = Blueprint('global_admin', __name__, url_prefix='/global-admin')


def global_admin_required(f):
    """Decorator to require global admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_global_admin:
            flash('Access denied: Global Administrator permission required', 'danger')
            return redirect(url_for('auth.login'))
        if session.get('organization_id') is not None:
            flash('Please log in to Global Administration', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@login_required
@global_admin_required
def index():
    """Global administration dashboard"""
    user_count = User.query.count()
    org_count = Organization.query.count()
    return render_template('global_admin/index.html',
                          user_count=user_count,
                          org_count=org_count)


# User Management Routes

@bp.route('/users')
@login_required
@global_admin_required
def users():
    """List all users"""
    users = User.query.order_by(User.login).all()
    return render_template('global_admin/users.html', users=users)


@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@global_admin_required
def create_user():
    """Create a new user"""
    form = UserCreateForm()
    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    form.organizations.choices = [(org.id, org.name) for org in organizations]

    if form.validate_on_submit():
        user = User(
            login=form.login.data,
            email=form.email.data,
            display_name=form.display_name.data,
            is_active=form.is_active.data,
            is_global_admin=form.is_global_admin.data,
            must_change_password=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # Assign organizations
        for org_id in form.organizations.data:
            membership = UserOrganizationMembership(user_id=user.id, organization_id=org_id)
            db.session.add(membership)

        db.session.commit()
        flash(f'User {user.login} created successfully', 'success')
        return redirect(url_for('global_admin.users'))

    return render_template('global_admin/create_user.html', form=form)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@global_admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    organizations = Organization.query.filter_by(is_active=True).order_by(Organization.name).all()
    form.organizations.choices = [(org.id, org.name) for org in organizations]

    if request.method == 'GET':
        form.organizations.data = [m.organization_id for m in user.organization_memberships]

    if form.validate_on_submit():
        user.login = form.login.data
        user.email = form.email.data
        user.display_name = form.display_name.data
        user.is_active = form.is_active.data
        user.is_global_admin = form.is_global_admin.data

        if form.reset_password.data:
            user.set_password(form.reset_password.data)
            user.must_change_password = True

        # Update organization memberships
        # Remove old memberships
        UserOrganizationMembership.query.filter_by(user_id=user.id).delete()

        # Add new memberships
        for org_id in form.organizations.data:
            membership = UserOrganizationMembership(user_id=user.id, organization_id=org_id)
            db.session.add(membership)

        db.session.commit()
        flash(f'User {user.login} updated successfully', 'success')
        return redirect(url_for('global_admin.users'))

    return render_template('global_admin/edit_user.html', form=form, user=user)


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@global_admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)

    # Prevent deletion of last active global admin
    if user.is_global_admin and user.is_active:
        active_admins = User.query.filter_by(is_global_admin=True, is_active=True).count()
        if active_admins <= 1:
            flash('Cannot delete the last active global administrator', 'danger')
            return redirect(url_for('global_admin.users'))

    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.login} deleted successfully', 'success')
    return redirect(url_for('global_admin.users'))


# Organization Management Routes

@bp.route('/organizations')
@login_required
@global_admin_required
def organizations():
    """List all organizations"""
    organizations = Organization.query.order_by(Organization.name).all()
    return render_template('global_admin/organizations.html', organizations=organizations)


@bp.route('/organizations/create', methods=['GET', 'POST'])
@login_required
@global_admin_required
def create_organization():
    """Create a new organization"""
    form = OrganizationCreateForm()

    if form.validate_on_submit():
        org = Organization(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        db.session.add(org)
        db.session.commit()
        flash(f'Organization {org.name} created successfully', 'success')
        return redirect(url_for('global_admin.organizations'))

    return render_template('global_admin/create_organization.html', form=form)


@bp.route('/organizations/<int:org_id>/edit', methods=['GET', 'POST'])
@login_required
@global_admin_required
def edit_organization(org_id):
    """Edit an existing organization"""
    org = Organization.query.get_or_404(org_id)
    form = OrganizationEditForm(obj=org)

    if form.validate_on_submit():
        org.name = form.name.data
        org.description = form.description.data
        org.is_active = form.is_active.data
        db.session.commit()
        flash(f'Organization {org.name} updated successfully', 'success')
        return redirect(url_for('global_admin.organizations'))

    return render_template('global_admin/edit_organization.html', form=form, org=org)


@bp.route('/organizations/<int:org_id>/delete-preview')
@login_required
@global_admin_required
def delete_organization_preview(org_id):
    """Show deletion impact preview for an organization"""
    org = Organization.query.get_or_404(org_id)

    # Calculate impact
    from app.models import Space, Challenge, Initiative, System, KPI, ValueType, Contribution
    impact = {
        'organization': org.name,
        'spaces': Space.query.filter_by(organization_id=org_id).count(),
        'challenges': Challenge.query.filter_by(organization_id=org_id).count(),
        'initiatives': Initiative.query.filter_by(organization_id=org_id).count(),
        'systems': System.query.filter_by(organization_id=org_id).count(),
        'value_types': ValueType.query.filter_by(organization_id=org_id).count(),
    }

    return render_template('global_admin/delete_organization_preview.html', org=org, impact=impact)


@bp.route('/organizations/<int:org_id>/delete', methods=['POST'])
@login_required
@global_admin_required
def delete_organization(org_id):
    """Delete an organization (cascades to all data)"""
    org = Organization.query.get_or_404(org_id)
    org_name = org.name

    db.session.delete(org)
    db.session.commit()

    flash(f'Organization {org_name} and all its data deleted successfully', 'success')
    return redirect(url_for('global_admin.organizations'))


@bp.route('/organizations/<int:org_id>/clone', methods=['GET', 'POST'])
@login_required
@global_admin_required
def clone_organization(org_id):
    """Clone an organization with all its structure"""
    source_org = Organization.query.get_or_404(org_id)
    form = OrganizationCloneForm()

    if form.validate_on_submit():
        result = OrganizationCloneService.clone_organization(
            source_org_id=org_id,
            new_org_name=form.new_name.data,
            new_org_description=form.new_description.data
        )

        if result['success']:
            stats = result['statistics']
            flash(
                f"Organization cloned successfully! Created: "
                f"{stats['value_types']} value types, "
                f"{stats['spaces']} spaces, "
                f"{stats['challenges']} challenges, "
                f"{stats['initiatives']} initiatives, "
                f"{stats['systems']} systems, "
                f"{stats['kpis']} KPIs",
                'success'
            )
            return redirect(url_for('global_admin.organizations'))
        else:
            flash(f"Clone failed: {result['error']}", 'danger')

    return render_template('global_admin/clone_organization.html', form=form, source_org=source_org)
