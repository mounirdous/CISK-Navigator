"""
Authentication tests
"""
import pytest
from app.models import User
from app.extensions import db


def test_bootstrap_admin_created(app):
    """Test that bootstrap admin is created on first startup"""
    with app.app_context():
        admin = User.query.filter_by(login='cisk').first()
        assert admin is not None
        assert admin.is_global_admin is True
        assert admin.must_change_password is True
        assert admin.check_password('Zurich20')


def test_login_valid_credentials(client, regular_user, organization):
    """Test login with valid credentials"""
    response = client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'TestPass123',
        'organization': organization.id
    }, follow_redirects=True)

    assert response.status_code == 200


def test_login_invalid_password(client, regular_user, organization):
    """Test login rejection for wrong password"""
    response = client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'WrongPassword',
        'organization': organization.id
    })

    assert b'Invalid login or password' in response.data


def test_login_inactive_user(client, regular_user, organization):
    """Test login rejection for inactive user"""
    with client.application.app_context():
        user = User.query.filter_by(login='testuser').first()
        user.is_active = False
        db.session.commit()

    response = client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'TestPass123',
        'organization': organization.id
    })

    assert b'inactive' in response.data


def test_global_admin_login_to_global_administration(client, global_admin):
    """Test that global admin can log into Global Administration"""
    response = client.post('/auth/login', data={
        'login': 'testadmin',
        'password': 'TestPass123',
        'organization': 0  # 0 = Global Administration
    }, follow_redirects=True)

    assert response.status_code == 200


def test_regular_user_cannot_login_to_global_administration(client, regular_user):
    """Test that regular user cannot access Global Administration"""
    response = client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'TestPass123',
        'organization': 0  # 0 = Global Administration
    })

    assert b'do not have permission' in response.data


def test_user_cannot_login_to_unassigned_organization(client, regular_user):
    """Test that user cannot login to organization they're not assigned to"""
    with client.application.app_context():
        # Create another organization
        from app.models import Organization
        other_org = Organization(name='Other Org', is_active=True)
        db.session.add(other_org)
        db.session.commit()
        other_org_id = other_org.id

    response = client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'TestPass123',
        'organization': other_org_id
    })

    assert b'do not have access' in response.data


def test_password_change(client, regular_user, organization):
    """Test forced password change on first login"""
    with client.application.app_context():
        user = User.query.filter_by(login='testuser').first()
        user.must_change_password = True
        db.session.commit()

    # Login
    client.post('/auth/login', data={
        'login': 'testuser',
        'password': 'TestPass123',
        'organization': organization.id
    })

    # Change password
    response = client.post('/auth/change-password', data={
        'current_password': 'TestPass123',
        'new_password': 'NewPass123',
        'confirm_password': 'NewPass123'
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify must_change_password is now False
    with client.application.app_context():
        user = User.query.filter_by(login='testuser').first()
        assert user.must_change_password is False
        assert user.check_password('NewPass123')
