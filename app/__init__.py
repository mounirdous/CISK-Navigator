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

    # Create tables and bootstrap admin
    with app.app_context():
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
