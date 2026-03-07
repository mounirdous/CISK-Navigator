"""
Authentication routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, Organization
from app.forms import LoginForm, ChangePasswordForm

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Two-step login:
    1. Authenticate with username/password
    2. Select organization (filtered by user access)
    """
    # If already authenticated AND has organization context, go to workspace
    if current_user.is_authenticated and session.get('organization_id'):
        return redirect(url_for('workspace.index'))
    # If authenticated but no organization (e.g., session cleared), log out and restart
    if current_user.is_authenticated and not session.get('organization_id'):
        logout_user()
        session.clear()
        flash('Session expired. Please log in again.', 'info')

    # Check if we're at step 2 (user already authenticated in session)
    temp_user_id = session.get('_temp_user_id')

    if temp_user_id:
        # STEP 2: Organization selection
        user = User.query.get(temp_user_id)
        if not user:
            session.pop('_temp_user_id', None)
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        # Get organizations user has access to
        user_orgs = user.get_organizations()
        org_choices = [(org.id, org.name) for org in user_orgs if org.is_active]

        if request.method == 'POST':
            is_admin_login = request.form.get('admin_login') == 'on'

            # Handle Global Administration
            if is_admin_login:
                if not user.is_global_admin:
                    flash('You do not have permission to access Global Administration', 'danger')
                    return render_template('auth/login_step2.html',
                                         user=user,
                                         organizations=org_choices,
                                         show_admin=user.is_global_admin)

                login_user(user)
                session.pop('_temp_user_id', None)
                session['organization_id'] = None
                session['organization_name'] = 'Global Administration'

                if user.must_change_password:
                    flash('You must change your password', 'warning')
                    return redirect(url_for('auth.change_password'))

                return redirect(url_for('global_admin.index'))

            # Handle organization selection
            selected_org_id = request.form.get('organization')
            if not selected_org_id:
                flash('Please select an organization', 'warning')
                return render_template('auth/login_step2.html',
                                     user=user,
                                     organizations=org_choices,
                                     show_admin=user.is_global_admin)

            selected_org_id = int(selected_org_id)
            if not user.has_organization_access(selected_org_id):
                flash('You do not have access to this organization', 'danger')
                return render_template('auth/login_step2.html',
                                     user=user,
                                     organizations=org_choices,
                                     show_admin=user.is_global_admin)

            organization = Organization.query.get(selected_org_id)
            if not organization or not organization.is_active:
                flash('Selected organization is not available', 'danger')
                return render_template('auth/login_step2.html',
                                     user=user,
                                     organizations=org_choices,
                                     show_admin=user.is_global_admin)

            login_user(user)
            session.pop('_temp_user_id', None)
            session['organization_id'] = organization.id
            session['organization_name'] = organization.name

            if user.must_change_password:
                flash('You must change your password', 'warning')
                return redirect(url_for('auth.change_password'))

            return redirect(url_for('workspace.index'))

        # GET request for step 2
        return render_template('auth/login_step2.html',
                             user=user,
                             organizations=org_choices,
                             show_admin=user.is_global_admin)

    # STEP 1: Username/password authentication
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid login or password', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('Your account is inactive', 'danger')
            return redirect(url_for('auth.login'))

        # Check if user has only one org - auto-login if so
        user_orgs = user.get_organizations()
        active_orgs = [org for org in user_orgs if org.is_active]

        # Auto-login if user has exactly one org and is not a global admin
        if len(active_orgs) == 1 and not user.is_global_admin:
            organization = active_orgs[0]
            login_user(user)
            session['organization_id'] = organization.id
            session['organization_name'] = organization.name

            if user.must_change_password:
                flash('You must change your password', 'warning')
                return redirect(url_for('auth.change_password'))

            return redirect(url_for('workspace.index'))

        # Store user ID temporarily for step 2
        session['_temp_user_id'] = user.id
        return redirect(url_for('auth.login'))

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    """Logout current user"""
    if current_user.is_authenticated:
        logout_user()
    session.pop('organization_id', None)
    session.pop('organization_name', None)
    session.pop('_temp_user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password (required for bootstrap admin on first login)"""
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('auth.change_password'))

        if form.new_password.data != form.confirm_password.data:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('auth.change_password'))

        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()

        flash('Password changed successfully', 'success')

        # Redirect based on context
        if session.get('organization_id') is None:
            return redirect(url_for('global_admin.index'))
        else:
            return redirect(url_for('workspace.index'))

    return render_template('auth/change_password.html', form=form)
