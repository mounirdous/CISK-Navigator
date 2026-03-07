"""
CISK Navigator Application Factory
"""
import os
from flask import Flask
from app.extensions import db, migrate, login_manager
from app.config import config


def create_app(config_name=None):
    """
    Application factory pattern.

    Creates and configures the Flask application.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Enable SQLite foreign keys
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        @app.before_request
        def _enable_foreign_keys():
            from flask import g
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
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import auth, global_admin, organization_admin, workspace
    app.register_blueprint(auth.bp)
    app.register_blueprint(global_admin.bp)
    app.register_blueprint(organization_admin.bp)
    app.register_blueprint(workspace.bp)

    # Disable caching in development
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    # Register Jinja2 filters
    @app.template_filter('format_value')
    def format_value_filter(value, value_type):
        """Format a numeric value according to its value type's decimal places"""
        if value is None:
            return ''

        # For qualitative types, return as-is
        if value_type.kind != 'numeric':
            return value

        # For numeric types, format according to decimal_places
        if value_type.numeric_format == 'integer':
            return f'{int(value)}'
        else:
            # Decimal format
            decimal_places = value_type.decimal_places if value_type.decimal_places is not None else 2
            return f'{float(value):.{decimal_places}f}'

    @app.template_filter('default_value_color')
    def default_value_color_filter(value):
        """Get default color for a numeric value based on its sign (for rollups)"""
        if value is None:
            return None
        try:
            numeric_value = float(value)
            if numeric_value > 0:
                return '#28a745'  # green
            elif numeric_value < 0:
                return '#dc3545'  # red
            else:
                return '#6c757d'  # gray
        except (ValueError, TypeError):
            return None

    # Bootstrap admin (only creates if doesn't exist)
    # Note: DO NOT use db.create_all() in production - use migrations instead!
    with app.app_context():
        # Only create tables in testing/development without migrations
        if app.config.get('TESTING') or (app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite:///')):
            db.create_all()

        _bootstrap_admin()

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
        login='cisk',
        email='admin@cisk.local',
        display_name='CISK Administrator',
        is_active=True,
        is_global_admin=True,
        must_change_password=True
    )
    admin.set_password('Zurich20')

    db.session.add(admin)
    db.session.commit()

    print("Bootstrap admin created: login=cisk, password=Zurich20 (must change on first login)")
