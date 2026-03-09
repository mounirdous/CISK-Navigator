"""
Unit tests for database models
"""

import pytest

from app.models import Organization, Space, User


class TestUserModel:
    """Tests for User model"""

    def test_user_creation(self, db):
        """Test creating a user"""
        user = User(login="newuser", email="newuser@example.com", display_name="New User", is_active=True)
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.login == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_global_admin is False

    def test_password_hashing(self, db):
        """Test password is hashed correctly"""
        user = User(login="user1", email="user1@example.com")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()

        # Password should be hashed, not stored as plain text
        assert user.password_hash != "secret"
        assert user.password_hash is not None
        assert len(user.password_hash) > 20

    def test_password_verification(self, db):
        """Test password verification works"""
        user = User(login="user2", email="user2@example.com")
        user.set_password("mypassword")
        db.session.add(user)
        db.session.commit()

        # Correct password should verify
        assert user.check_password("mypassword") is True

        # Wrong password should not verify
        assert user.check_password("wrongpassword") is False
        assert user.check_password("") is False

    def test_global_admin_flag(self, admin_user):
        """Test global admin flag"""
        assert admin_user.is_global_admin is True

    def test_user_can_check_permissions(self, org_user, sample_organization):
        """Test user permission checking"""
        # org_user fixture has all permissions
        assert org_user.has_permission(sample_organization.id, "can_manage_kpis") is True
        assert org_user.has_permission(sample_organization.id, "can_add_comments") is True

    def test_user_without_membership_has_no_permissions(self, sample_user, sample_organization):
        """Test user without org membership has no permissions"""
        assert sample_user.has_permission(sample_organization.id, "can_manage_kpis") is False


class TestOrganizationModel:
    """Tests for Organization model"""

    def test_organization_creation(self, db):
        """Test creating an organization"""
        org = Organization(name="My Org", description="Test organization", is_active=True)
        db.session.add(org)
        db.session.commit()

        assert org.id is not None
        assert org.name == "My Org"
        assert org.is_active is True

    def test_organization_relationships(self, sample_organization, org_user):
        """Test organization has relationships"""
        # Should have user membership
        assert len(sample_organization.user_memberships) > 0

    def test_organization_name_must_be_unique(self, db, sample_organization):
        """Test organization names must be unique"""
        # Try to create another org with same name
        duplicate_org = Organization(name=sample_organization.name, is_active=True)  # Same name
        db.session.add(duplicate_org)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db.session.commit()


class TestSpaceModel:
    """Tests for Space model"""

    def test_space_creation(self, db, sample_organization):
        """Test creating a space"""
        space = Space(
            name="Test Space",
            description="Test space description",
            organization_id=sample_organization.id,
            is_private=False,
            display_order=1,
        )
        db.session.add(space)
        db.session.commit()

        assert space.id is not None
        assert space.name == "Test Space"
        assert space.is_private is False
        assert space.organization_id == sample_organization.id

    def test_space_privacy_default(self, db, sample_organization):
        """Test space is_private defaults to False"""
        space = Space(name="Public Space", organization_id=sample_organization.id)
        db.session.add(space)
        db.session.commit()

        assert space.is_private is False

    def test_private_space_creation(self, db, sample_organization):
        """Test creating a private space"""
        space = Space(name="Private Space", organization_id=sample_organization.id, is_private=True)
        db.session.add(space)
        db.session.commit()

        assert space.is_private is True
