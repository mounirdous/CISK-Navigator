"""
Pytest configuration and fixtures
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Organization, UserOrganizationMembership


@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def global_admin(app):
    """Create a global admin user"""
    with app.app_context():
        admin = User(
            login='testadmin',
            email='admin@test.com',
            is_active=True,
            is_global_admin=True,
            must_change_password=False
        )
        admin.set_password('TestPass123')
        db.session.add(admin)
        db.session.commit()
        return admin


@pytest.fixture
def organization(app):
    """Create a test organization"""
    with app.app_context():
        org = Organization(
            name='Test Organization',
            description='Test org',
            is_active=True
        )
        db.session.add(org)
        db.session.commit()
        return org


@pytest.fixture
def regular_user(app, organization):
    """Create a regular user assigned to an organization"""
    with app.app_context():
        user = User(
            login='testuser',
            email='user@test.com',
            is_active=True,
            is_global_admin=False,
            must_change_password=False
        )
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.flush()

        membership = UserOrganizationMembership(
            user_id=user.id,
            organization_id=organization.id
        )
        db.session.add(membership)
        db.session.commit()
        return user
