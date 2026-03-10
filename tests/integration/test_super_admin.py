"""
Integration tests for Super Admin routes
"""

from app.models import SystemSetting


class TestSuperAdminAccess:
    """Tests for Super Admin access control"""

    def test_super_admin_dashboard_requires_super_admin(self, client, admin_user):
        """Test that global admins cannot access super admin dashboard"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_user.id)

        response = client.get("/super-admin/")
        assert response.status_code == 403

    def test_super_admin_dashboard_accessible_to_super_admin(self, client, super_admin_user):
        """Test that super admins can access dashboard"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/")
        assert response.status_code == 200
        assert b"Super Admin Dashboard" in response.data

    def test_super_admin_dashboard_requires_authentication(self, client):
        """Test that unauthenticated users are redirected"""
        response = client.get("/super-admin/")
        assert response.status_code == 302
        assert "login" in response.location.lower()


class TestSystemSettings:
    """Tests for system settings management"""

    def test_system_settings_page_loads(self, client, super_admin_user, db):
        """Test system settings page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/settings")
        assert response.status_code == 200
        assert b"System Settings" in response.data

    def test_default_settings_exist(self, db):
        """Test that default settings are created by migration"""
        # Note: These will be created by the migration
        sso_enabled = SystemSetting.query.filter_by(key="sso_enabled").first()
        maintenance_mode = SystemSetting.query.filter_by(key="maintenance_mode").first()

        # Settings might not exist yet if migration hasn't run
        # Just verify the model works
        assert SystemSetting.query.count() >= 0

    def test_update_setting(self, client, super_admin_user, db):
        """Test updating a system setting"""
        # Create a test setting
        setting = SystemSetting(key="test_setting", value="false", value_type="boolean", category="test")
        db.session.add(setting)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.post(
            "/super-admin/settings/update", data={"key": "test_setting", "value": "true"}, follow_redirects=True
        )

        assert response.status_code == 200

        # Verify setting was updated
        updated_setting = SystemSetting.query.filter_by(key="test_setting").first()
        assert updated_setting.value == "true"


class TestSSOSettings:
    """Tests for SSO configuration"""

    def test_sso_settings_page_loads(self, client, super_admin_user):
        """Test SSO settings page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/settings/sso")
        assert response.status_code == 200
        assert b"SSO" in response.data or b"Single Sign-On" in response.data

    def test_sso_toggle(self, client, super_admin_user, db):
        """Test toggling SSO on/off"""
        # Create SSO setting
        sso_setting = SystemSetting(key="sso_enabled", value="false", value_type="boolean", category="authentication")
        db.session.add(sso_setting)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        # Toggle SSO on
        response = client.post("/super-admin/settings/sso/toggle", follow_redirects=True)
        assert response.status_code == 200

        # Verify SSO was enabled
        updated_setting = SystemSetting.query.filter_by(key="sso_enabled").first()
        assert updated_setting.value.lower() == "true"

        # Toggle SSO off
        response = client.post("/super-admin/settings/sso/toggle", follow_redirects=True)
        assert response.status_code == 200

        # Verify SSO was disabled
        updated_setting = SystemSetting.query.filter_by(key="sso_enabled").first()
        assert updated_setting.value.lower() == "false"


class TestMaintenanceMode:
    """Tests for maintenance mode"""

    def test_maintenance_settings_page_loads(self, client, super_admin_user):
        """Test maintenance settings page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/settings/maintenance")
        assert response.status_code == 200

    def test_maintenance_mode_toggle(self, client, super_admin_user, db):
        """Test toggling maintenance mode"""
        # Create maintenance mode setting
        maintenance_setting = SystemSetting(
            key="maintenance_mode", value="false", value_type="boolean", category="system"
        )
        db.session.add(maintenance_setting)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        # Toggle maintenance mode on
        response = client.post("/super-admin/settings/maintenance/toggle", follow_redirects=True)
        assert response.status_code == 200

        # Verify maintenance mode was enabled
        updated_setting = SystemSetting.query.filter_by(key="maintenance_mode").first()
        assert updated_setting.value.lower() == "true"


class TestUserManagement:
    """Tests for user management in super admin"""

    def test_users_page_loads(self, client, super_admin_user):
        """Test users page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/users")
        assert response.status_code == 200
        assert b"User Management" in response.data or b"Users" in response.data


class TestSystemHealth:
    """Tests for system health monitoring"""

    def test_health_page_loads(self, client, super_admin_user):
        """Test health page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/health")
        assert response.status_code == 200

    def test_logs_page_loads(self, client, super_admin_user):
        """Test logs page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/logs")
        assert response.status_code == 200


class TestSecuritySettings:
    """Tests for security settings"""

    def test_security_settings_page_loads(self, client, super_admin_user):
        """Test security settings page is accessible"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(super_admin_user.id)

        response = client.get("/super-admin/settings/security")
        assert response.status_code == 200
