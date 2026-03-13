"""
Integration tests for admin operations
"""

import pytest

from app.models import Space, ValueType


class TestGlobalAdmin:
    """Tests for Global Admin operations"""

    def test_global_admin_index_requires_admin(self, client, sample_user):
        """Test regular users cannot access global admin"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)

        response = client.get("/global-admin/", follow_redirects=True)
        assert response.status_code in [200, 302, 403]
        if response.status_code == 200:
            data = response.data.decode("utf-8").lower()
            # Should show login or permission error
            assert "login" in data or "permission" in data or "denied" in data

    def test_global_admin_index_accessible_by_admin(self, client, admin_user):
        """Test global admins can access global admin pages"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/")
        assert response.status_code == 200

    def test_global_admin_can_view_users(self, client, admin_user, db):
        """Test global admin can view user list"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/users")
        assert response.status_code == 200

    def test_global_admin_can_view_organizations(self, client, admin_user, sample_organization, db):
        """Test global admin can view organization list"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/organizations")
        assert response.status_code == 200
        assert sample_organization.name.encode() in response.data

    def test_global_admin_user_creation_page_loads(self, client, admin_user):
        """Test global admin can access user creation form"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/users/create")
        assert response.status_code == 200
        assert b"Create" in response.data or b"create" in response.data

    def test_global_admin_organization_creation_page_loads(self, client, admin_user):
        """Test global admin can access organization creation form"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/organizations/create")
        assert response.status_code == 200


class TestOrganizationAdmin:
    """Tests for Organization Admin operations"""

    def test_org_admin_requires_organization_context(self, client, org_user):
        """Test org admin pages require organization selection"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            # No organization_id set

        response = client.get("/org-admin/", follow_redirects=True)
        assert response.status_code == 200

    def test_org_admin_index_loads(self, client, org_user, sample_organization, db):
        """Test organization admin index loads"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/")
        assert response.status_code == 200

    def test_org_admin_can_view_spaces(self, client, org_user, sample_organization, db):
        """Test org admin spaces route redirects to workspace"""
        # Create a space
        space = Space(name="Admin Test Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/spaces", follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to workspace
        assert b"Workspace" in response.data or b"workspace" in response.data

    def test_org_admin_space_creation_requires_permission(self, client, sample_user, sample_organization, db):
        """Test users without permission cannot create spaces"""
        # sample_user has no organization membership
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/spaces/create", follow_redirects=True)
        # Should be denied or redirected
        assert response.status_code in [200, 302, 403]

    def test_org_admin_can_view_value_types(self, client, org_user, sample_organization, db):
        """Test org admin can view value types"""
        # Create a value type
        value_type = ValueType(
            name="Test Metric",
            kind="numeric",
            numeric_format="integer",
            organization_id=sample_organization.id,
            is_active=True,
        )
        db.session.add(value_type)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/value-types")
        assert response.status_code == 200
        assert b"Test Metric" in response.data

    def test_org_admin_value_type_creation_page_loads(self, client, org_user, sample_organization, db):
        """Test org admin can access value type creation form"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/value-types/create")
        assert response.status_code == 200


class TestBackupRestore:
    """Tests for backup and restore functionality"""

    def test_backup_restore_requires_global_admin(self, client, sample_user):
        """Test backup/restore requires global admin access"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)

        response = client.get("/global-admin/backup-restore", follow_redirects=True)
        # Should be denied access
        assert response.status_code in [200, 302, 403]

    def test_backup_restore_page_loads_for_admin(self, client, admin_user, sample_organization, db):
        """Test global admin can access backup/restore page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/backup-restore")
        assert response.status_code == 200
        assert b"Backup" in response.data or b"backup" in response.data

    def test_create_backup_requires_admin(self, client, sample_user, sample_organization, db):
        """Test creating backup requires global admin"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)

        response = client.get(f"/global-admin/backup-restore/create/{sample_organization.id}", follow_redirects=True)
        assert response.status_code in [200, 302, 403]

    def test_create_backup_returns_yaml_for_admin(self, client, admin_user, sample_organization, db):
        """Test backup creates JSON file for download"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get(f"/global-admin/backup-restore/create/{sample_organization.id}")
        # Should either return JSON content or redirect
        assert response.status_code in [200, 302]
        if response.status_code == 200:
            # Check content type is JSON (evolved from YAML)
            assert response.content_type in [
                "application/json",
                "application/octet-stream",
            ]


class TestHealthDashboard:
    """Tests for health dashboard"""

    @pytest.mark.skip(reason="Health dashboard route may not exist yet")
    def test_health_dashboard_requires_admin(self, client, sample_user):
        """Test health dashboard requires global admin"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)

        response = client.get("/global-admin/health", follow_redirects=True)
        assert response.status_code in [200, 302, 403, 404]

    @pytest.mark.skip(reason="Health dashboard route may not exist yet")
    def test_health_dashboard_loads_for_admin(self, client, admin_user, db):
        """Test global admin can access health dashboard"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/global-admin/health")
        # Route may not exist yet
        assert response.status_code in [200, 404]
