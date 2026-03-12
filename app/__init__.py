"""
CISK Navigator Application Factory
"""

import os

from flask import Flask

from app.config import config
from app.extensions import db, login_manager, migrate

__version__ = "1.21.0"


def create_app(config_name=None):
    """
    Application factory pattern.

    Creates and configures the Flask application.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Enable SQLite foreign keys
    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        @app.before_request
        def _enable_foreign_keys():
            from sqlalchemy import event
            from sqlalchemy.engine import Engine

            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User

        try:
            return User.query.get(int(user_id))
        except Exception:
            # During migrations, schema might not match - return None to force re-login
            return None

    # Register blueprints
    from app.routes import analytics, auth, executive, global_admin, organization_admin, super_admin, workspace

    app.register_blueprint(auth.bp)
    app.register_blueprint(super_admin.bp)
    app.register_blueprint(global_admin.bp)
    app.register_blueprint(organization_admin.bp)
    app.register_blueprint(workspace.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(executive.bp)

    # Register test error routes (REMOVE IN PRODUCTION)
    if app.config.get("FLASK_ENV") == "development":
        from app.routes import test_errors

        app.register_blueprint(test_errors.bp)

    # Maintenance mode check (global)
    @app.before_request
    def check_maintenance_mode():
        """Block write operations during maintenance mode (except for super admins)"""
        from flask import flash, redirect, request, url_for
        from flask_login import current_user

        from app.models import SystemSetting

        # Skip check for static files and certain routes
        if request.endpoint in ["static", "auth.login", "auth.logout", None]:
            return None

        # Check if maintenance mode is active
        if SystemSetting.is_maintenance_mode():
            # Super admins can bypass maintenance mode
            if current_user.is_authenticated and current_user.is_super_admin:
                return None

            # Block write operations (POST, PUT, DELETE, PATCH)
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                flash(
                    "[MAINTENANCE] System is in maintenance mode. Write operations are temporarily disabled.",
                    "warning",
                )
                # Try to redirect to referer or dashboard
                return redirect(request.referrer or url_for("workspace.dashboard"))

        return None

    # Root route - redirect to login or dashboard
    @app.route("/")
    def index():
        """Redirect root URL to appropriate page based on authentication status"""
        from flask import redirect, session, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            # If user has organization context, go to dashboard
            if session.get("organization_id"):
                return redirect(url_for("workspace.dashboard"))
            # If authenticated but no org, go to org selection
            return redirect(url_for("auth.login"))
        # Not authenticated, go to login
        return redirect(url_for("auth.login"))

    # Disable caching in development
    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    # Context processor - inject maintenance_mode into all templates
    @app.context_processor
    def inject_maintenance_mode():
        """Make maintenance_mode available to all templates"""
        from app.models import SystemSetting

        return {"maintenance_mode": SystemSetting.is_maintenance_mode()}

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 - Page Not Found errors"""
        from flask import render_template

        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 - Internal Server errors"""
        from flask import render_template

        db.session.rollback()  # Clean up any failed transactions
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 - Forbidden errors"""
        from flask import render_template

        return render_template("errors/403.html"), 403

    # Register Jinja2 filters
    @app.template_filter("format_value")
    def format_value_filter(value, value_type, config=None):
        """Format a numeric value according to its value type's decimal places and display scale"""
        if value is None:
            return ""

        # For qualitative types, return as-is
        if value_type.kind != "numeric":
            return value

        # Get display scale settings from config if provided
        divisor = 1
        suffix = ""
        if config and hasattr(config, "display_scale"):
            divisor = config.get_scale_divisor()
            suffix = config.get_scale_suffix()

        # Scale the value
        scaled_value = float(value) / divisor

        # Determine decimal places to use
        if divisor > 1:
            # Using scale: check if display_decimals is explicitly set
            if config and hasattr(config, "display_decimals") and config.display_decimals is not None:
                decimal_places = config.display_decimals
            else:
                # Default: use at least 2 decimals when scaling
                decimal_places = max(2, value_type.decimal_places if value_type.decimal_places is not None else 2)

            formatted = f"{scaled_value:.{decimal_places}f}"
            # Remove trailing zeros and decimal point if not needed
            formatted = formatted.rstrip("0").rstrip(".")
        else:
            # No scaling: use original format
            if value_type.numeric_format == "integer":
                formatted = f"{int(round(scaled_value))}"
            else:
                # Decimal format
                decimal_places = value_type.decimal_places if value_type.decimal_places is not None else 2
                formatted = f"{scaled_value:.{decimal_places}f}"

        # Add suffix if present
        if suffix:
            formatted = f"{formatted}{suffix}"

        return formatted

    @app.template_filter("default_value_color")
    def default_value_color_filter(value):
        """Get default color for a numeric value based on its sign (for rollups)"""
        if value is None:
            return None
        try:
            numeric_value = float(value)
            if numeric_value > 0:
                return "#28a745"  # green
            elif numeric_value < 0:
                return "#dc3545"  # red
            else:
                return "#6c757d"  # gray
        except (ValueError, TypeError):
            return None

    # Bootstrap admin (only creates if doesn't exist)
    # Note: DO NOT use db.create_all() in production - use migrations instead!
    with app.app_context():
        # CRITICAL LOGGING: Show which database we're using
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        flask_env = app.config.get("FLASK_ENV", "development")
        print("=" * 80)
        print(f"FLASK_ENV: {flask_env}")
        if "postgresql" in db_uri:
            # Mask password for security
            safe_uri = db_uri.split("@")[1] if "@" in db_uri else db_uri
            print(f"[OK] USING POSTGRESQL: {safe_uri}")
        elif "sqlite" in db_uri:
            print(f"[WARN] USING SQLITE: {db_uri}")
            if flask_env == "production":
                print("[ERROR] SQLite should NEVER be used in production!")
        print("=" * 80)

        # Only create tables in testing/development without migrations
        if app.config.get("TESTING") or (app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite:///")):
            if flask_env == "production":
                raise RuntimeError("CRITICAL: Attempted to use SQLite in production! Check DATABASE_URL!")
            db.create_all()

        try:
            _bootstrap_admin()
        except Exception as e:
            # During migrations, schema might not match models yet - that's OK
            print(f"Note: Skipping bootstrap (likely during migration): {e}")

    return app


def _bootstrap_admin():
    """
    Create bootstrap global administrator account if it doesn't exist.

    Login: cisk
    Password: Zurich20
    """
    from app.models import User

    # Check if any global admin exists
    existing_admin = User.query.filter_by(is_global_admin=True).first()
    if existing_admin:
        return  # Admin already exists

    # Create bootstrap admin
    admin = User(
        login="cisk",
        email="admin@cisk.local",
        display_name="CISK Administrator",
        is_active=True,
        is_global_admin=True,
        must_change_password=True,
    )
    admin.set_password("Zurich20")

    db.session.add(admin)
    db.session.commit()

    print("Bootstrap admin created: login=cisk, password=Zurich20 (must change on first login)")
