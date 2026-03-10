"""
Shared pytest fixtures for all tests
"""

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Organization, User, UserOrganizationMembership


@pytest.fixture(scope="session")
def app():
    """Create test Flask application"""
    app = create_app("testing")

    # Override config for testing
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    return app


@pytest.fixture(scope="function")
def db(app):
    """Create clean database for each test"""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.session.close()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Test client for making requests"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI test runner"""
    return app.test_cli_runner()


@pytest.fixture
def sample_user(db):
    """Create a sample user"""
    user = User(
        login="testuser", email="test@example.com", display_name="Test User", is_active=True, is_global_admin=False
    )
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(db):
    """Create a global admin user"""
    admin = User(
        login="admin", email="admin@example.com", display_name="Admin User", is_active=True, is_global_admin=True
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def super_admin_user(db):
    """Create a super admin user"""
    super_admin = User(
        login="superadmin",
        email="superadmin@example.com",
        display_name="Super Admin",
        is_active=True,
        is_super_admin=True,
        is_global_admin=True,
    )
    super_admin.set_password("superadmin123")
    db.session.add(super_admin)
    db.session.commit()
    return super_admin


@pytest.fixture
def sample_organization(db):
    """Create a sample organization"""
    org = Organization(name="Test Organization", description="Test org for testing", is_active=True)
    db.session.add(org)
    db.session.commit()
    return org


@pytest.fixture
def org_user(db, sample_user, sample_organization):
    """Create user with organization membership"""
    membership = UserOrganizationMembership(
        user_id=sample_user.id,
        organization_id=sample_organization.id,
        can_manage_spaces=True,
        can_manage_challenges=True,
        can_manage_initiatives=True,
        can_manage_systems=True,
        can_manage_kpis=True,
        can_view_comments=True,
        can_add_comments=True,
    )
    db.session.add(membership)
    db.session.commit()
    return sample_user


@pytest.fixture
def authenticated_client(client, sample_user):
    """Client with authenticated user"""
    with client:
        client.post("/auth/login", data={"login": sample_user.login, "password": "password123"}, follow_redirects=True)
        yield client
