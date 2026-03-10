"""
Authentication routes
"""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import ChangePasswordForm, LoginForm, ProfileEditForm
from app.models import Organization, SSOConfig, User
from app.services import AuditService

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Single-step login with automatic organization selection.

    Uses user's default organization or first available org.
    Users can switch organizations via navbar after login.
    """
    # If already authenticated AND has organization context, go to workspace
    if current_user.is_authenticated and session.get("organization_id"):
        return redirect(url_for("workspace.dashboard"))

    # If authenticated but no organization, log out and restart
    if current_user.is_authenticated and not session.get("organization_id"):
        logout_user()
        session.clear()
        flash("Session expired. Please log in again.", "info")

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(login=form.login.data).first()

        if user is None or not user.check_password(form.password.data):
            # Audit log failed login
            AuditService.log_login(user, success=False, reason="Invalid credentials")
            flash("Invalid login or password", "danger")
            return redirect(url_for("auth.login"))

        if not user.is_active:
            # Audit log failed login
            AuditService.log_login(user, success=False, reason="Account inactive")
            flash("Your account is inactive", "danger")
            return redirect(url_for("auth.login"))

        # Get user's organizations (exclude deleted ones)
        user_orgs = user.get_organizations()
        active_orgs = [org for org in user_orgs if org.is_active and not org.is_deleted]

        # Special case: Global Admin with no organizations
        # Allow them to log in and access Global Admin panel
        if user.is_global_admin and not active_orgs:
            login_user(user)
            session["organization_id"] = None
            session["organization_name"] = "Global Administration"

            # Audit log successful login
            AuditService.log_login(user, success=True)

            # Handle password change requirement
            if user.must_change_password and not session.get("_pwd_check_done"):
                session["_pwd_check_done"] = True
                flash("You must change your password", "warning")
                return redirect(url_for("auth.change_password"))

            flash(f"Welcome, {user.display_name or user.login}! (Global Admin)", "success")
            return redirect(url_for("global_admin.index"))

        # Determine which organization to log into
        selected_org = None

        # Priority 1: User's default organization (if set and user has access)
        if user.default_organization_id:
            default_org = Organization.query.get(user.default_organization_id)
            if (
                default_org
                and default_org.is_active
                and not default_org.is_deleted
                and user.has_organization_access(default_org.id)
            ):
                selected_org = default_org

        # Priority 2: First available organization
        if not selected_org and active_orgs:
            selected_org = active_orgs[0]

        # No organizations available (and not a global admin)
        if not selected_org:
            flash("You do not have access to any organizations. Please contact your administrator.", "danger")
            return redirect(url_for("auth.login"))

        # Log user in with organization context
        login_user(user)
        session["organization_id"] = selected_org.id
        session["organization_name"] = selected_org.name

        # Audit log successful login
        AuditService.log_login(user, success=True)

        # Handle password change requirement
        if user.must_change_password and not session.get("_pwd_check_done"):
            session["_pwd_check_done"] = True
            flash("You must change your password", "warning")
            return redirect(url_for("auth.change_password"))

        # Success message
        flash(f"Welcome back, {user.display_name or user.login}!", "success")
        return redirect(url_for("workspace.dashboard"))

    # Check SSO status - only use SSOConfig as single source of truth
    sso_config = SSOConfig.get_instance()
    sso_enabled = sso_config and sso_config.is_enabled and sso_config.is_configured()

    return render_template(
        "auth/login.html", form=form, sso_enabled=sso_enabled, sso_config=sso_config if sso_enabled else None
    )


@bp.route("/logout")
def logout():
    """Logout current user"""
    if current_user.is_authenticated:
        # Audit log before logging out
        AuditService.log_logout(current_user)
        logout_user()
    session.pop("organization_id", None)
    session.pop("organization_name", None)
    session.pop("_temp_user_id", None)
    session.pop("_pwd_check_done", None)
    flash("You have been logged out", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and edit user profile"""
    form = ProfileEditForm()

    # Populate organization choices
    user_orgs = current_user.get_organizations()
    org_choices = [(0, "-- None (use first available) --")] + [(org.id, org.name) for org in user_orgs if org.is_active]
    form.default_organization.choices = org_choices

    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.email = form.email.data
        current_user.dark_mode = form.dark_mode.data

        # Handle default organization
        default_org_id = form.default_organization.data
        if default_org_id == 0:
            current_user.default_organization_id = None
        else:
            # Verify user has access
            if current_user.has_organization_access(default_org_id):
                current_user.default_organization_id = default_org_id
            else:
                flash("You do not have access to the selected organization", "danger")
                return redirect(url_for("auth.profile"))

        db.session.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for("auth.profile"))

    # Pre-populate form with current values
    if request.method == "GET":
        form.display_name.data = current_user.display_name
        form.email.data = current_user.email
        form.dark_mode.data = current_user.dark_mode
        form.default_organization.data = current_user.default_organization_id or 0

    return render_template("auth/profile.html", form=form)


@bp.route("/switch-organization/<int:org_id>", methods=["POST"])
@login_required
def switch_organization(org_id):
    """Switch to a different organization without logging out"""
    # Verify user has access to this organization
    if not current_user.has_organization_access(org_id):
        flash("You do not have access to this organization", "danger")
        return redirect(request.referrer or url_for("workspace.dashboard"))

    # Get organization
    organization = Organization.query.get(org_id)
    if not organization or not organization.is_active:
        flash("Organization is not available", "danger")
        return redirect(request.referrer or url_for("workspace.dashboard"))

    # Switch organization context
    session["organization_id"] = organization.id
    session["organization_name"] = organization.name

    flash(f"Switched to {organization.name}", "success")
    return redirect(url_for("workspace.dashboard"))


@bp.route("/switch-to-global-admin", methods=["POST", "GET"])
@login_required
def switch_to_global_admin():
    """Switch to Global Admin mode (clear organization context)"""
    if not current_user.is_global_admin:
        flash("Access denied: Global Administrator permission required", "danger")
        return redirect(url_for("workspace.dashboard"))

    # Clear organization context
    session["organization_id"] = None
    session["organization_name"] = "Global Administration"

    flash("Switched to Global Administration mode", "success")
    return redirect(url_for("global_admin.index"))


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change password (required for bootstrap admin on first login)"""
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect", "danger")
            return redirect(url_for("auth.change_password"))

        if form.new_password.data != form.confirm_password.data:
            flash("New passwords do not match", "danger")
            return redirect(url_for("auth.change_password"))

        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()

        # Clear the password check flag so they won't be prompted again
        session.pop("_pwd_check_done", None)

        flash("Password changed successfully", "success")

        # Redirect based on context
        if session.get("organization_id") is None:
            return redirect(url_for("global_admin.index"))
        else:
            return redirect(url_for("workspace.dashboard"))

    return render_template("auth/change_password.html", form=form)


# ============================================================================
# SSO Routes
# ============================================================================


@bp.route("/sso/initiate")
def sso_initiate():
    """
    Initiate SSO authentication flow.

    Redirects user to the identity provider's authorization endpoint.
    """
    from app.services import SSOService

    # Check if SSO is enabled and configured
    if not SSOService.can_use_sso():
        flash("SSO is not available", "warning")
        return redirect(url_for("auth.login"))

    # Initiate OIDC flow
    redirect_url = SSOService.initiate_oidc_flow()
    if redirect_url:
        return redirect(redirect_url)
    else:
        flash("Failed to initiate SSO flow", "danger")
        return redirect(url_for("auth.login"))


@bp.route("/sso/callback")
def sso_callback():
    """
    Handle SSO callback from identity provider.

    Exchanges authorization code for tokens and logs user in.
    """
    from app.services import SSOService

    # Get authorization code and state from query parameters
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        flash(f"SSO authentication failed: {error}", "danger")
        return redirect(url_for("auth.login"))

    if not code or not state:
        flash("Invalid SSO callback", "danger")
        return redirect(url_for("auth.login"))

    # Handle OIDC callback
    user_info, error_msg = SSOService.handle_oidc_callback(code, state)

    if error_msg:
        flash(error_msg, "danger")
        return redirect(url_for("auth.login"))

    if not user_info:
        flash("Failed to retrieve user information from SSO provider", "danger")
        return redirect(url_for("auth.login"))

    # Provision or update user (JIT)
    user, was_created = SSOService.provision_or_update_user(user_info)

    if not user:
        flash("Failed to provision user. Please contact your administrator.", "danger")
        return redirect(url_for("auth.login"))

    if not user.is_active:
        flash("Your account is inactive", "danger")
        return redirect(url_for("auth.login"))

    # Get user's organizations
    user_orgs = user.get_organizations()
    active_orgs = [org for org in user_orgs if org.is_active]

    # Special case: Global Admin with no organizations
    if user.is_global_admin and not active_orgs:
        login_user(user)
        session["organization_id"] = None
        session["organization_name"] = "Global Administration"
        session.pop("sso_state", None)

        flash(f"Welcome, {user.display_name or user.login}! (Global Admin)", "success")
        return redirect(url_for("global_admin.index"))

    # Determine which organization to log into
    selected_org = None

    # Priority 1: User's default organization (if set and user has access)
    if user.default_organization_id:
        default_org = Organization.query.get(user.default_organization_id)
        if default_org and default_org.is_active and user.has_organization_access(default_org.id):
            selected_org = default_org

    # Priority 2: First available organization
    if not selected_org and active_orgs:
        selected_org = active_orgs[0]

    # No organizations available
    if not selected_org:
        if was_created:
            # New SSO user with no organizations - show helpful message
            flash(
                f"Welcome, {user.display_name or user.login}! Your account has been created. "
                "Please contact your administrator to be added to an organization.",
                "info",
            )
        else:
            flash("You do not have access to any organizations. Please contact your administrator.", "warning")
        logout_user()  # Log them out since they can't access anything
        return redirect(url_for("auth.login"))

    # Log user in with organization context
    login_user(user)
    session["organization_id"] = selected_org.id
    session["organization_name"] = selected_org.name

    # Clean up SSO session data
    session.pop("sso_state", None)

    # Flash welcome message
    if was_created:
        flash(f"Welcome to CISK Navigator, {user.display_name or user.login}!", "success")
    else:
        flash(f"Welcome back, {user.display_name or user.login}!", "success")

    return redirect(url_for("workspace.dashboard"))


@bp.route("/sso/logout")
@login_required
def sso_logout():
    """
    Handle SSO logout.

    Logs user out of CISK Navigator and optionally redirects to IdP logout.
    """
    # Check if user is SSO user
    if current_user.is_sso_user():
        # TODO: Implement IdP logout (Single Logout - SLO)
        # For now, just local logout
        pass

    logout_user()
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for("auth.login"))
