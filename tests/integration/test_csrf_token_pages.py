"""
Integration tests to ensure all pages have csrf_token available
and no UndefinedError appears in templates
"""

import pytest


class TestCSRFTokenAvailability:
    """Test that all pages requiring POST have csrf_token available"""

    @pytest.fixture
    def authenticated_org_user(self, client, org_user, sample_organization):
        """Client authenticated with organization context"""
        with client:
            # Login
            client.post(
                "/auth/login",
                data={"login": org_user.login, "password": "password123"},
                follow_redirects=True,
            )

            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id
                sess["organization_name"] = sample_organization.name

            yield client

    @pytest.fixture
    def authenticated_admin(self, client, admin_user):
        """Client authenticated as global admin"""
        with client:
            client.post(
                "/auth/login",
                data={"login": admin_user.login, "password": "admin123"},
                follow_redirects=True,
            )
            yield client

    @pytest.fixture
    def authenticated_super_admin(self, client, super_admin_user):
        """Client authenticated as super admin"""
        with client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )
            yield client

    def assert_no_csrf_errors(self, response):
        """Helper to check response for csrf_token errors"""
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.data.decode("utf-8")

        # Check for undefined errors
        assert "UndefinedError" not in data, "Found UndefinedError in response"
        assert "'csrf_token' is undefined" not in data, "Found csrf_token undefined error"

        # For debugging - print if there are any jinja2 errors
        if "jinja2" in data.lower() and "error" in data.lower():
            print("\nWarning: Jinja2 error found in response")
            # Extract error context
            lines = data.split("\n")
            for i, line in enumerate(lines):
                if "jinja2" in line.lower() and "error" in line.lower():
                    print("\n".join(lines[max(0, i - 3) : min(len(lines), i + 3)]))

    # Organization Admin Routes
    def test_organization_admin_index(self, authenticated_org_user):
        """Test /org-admin/ has csrf_token"""
        response = authenticated_org_user.get("/org-admin/")
        self.assert_no_csrf_errors(response)

    # Workspace Routes
    def test_workspace_index(self, authenticated_org_user):
        """Test /workspace/ has csrf_token"""
        response = authenticated_org_user.get("/workspace/")
        self.assert_no_csrf_errors(response)

    def test_workspace_snapshots_list(self, authenticated_org_user):
        """Test /workspace/snapshots/list has csrf_token"""
        response = authenticated_org_user.get("/workspace/snapshots/list")
        self.assert_no_csrf_errors(response)

    # Executive Dashboard
    def test_executive_dashboard(self, authenticated_org_user):
        """Test /executive/dashboard has csrf_token"""
        response = authenticated_org_user.get("/executive/dashboard")
        self.assert_no_csrf_errors(response)

    # Analytics Dashboard
    def test_analytics_dashboard(self, authenticated_org_user):
        """Test /analytics/dashboard has csrf_token"""
        response = authenticated_org_user.get("/analytics/dashboard")
        self.assert_no_csrf_errors(response)

    # Map Dashboard
    def test_map_dashboard(self, authenticated_org_user):
        """Test /map/ has csrf_token"""
        response = authenticated_org_user.get("/map/")
        self.assert_no_csrf_errors(response)

    # Geography Routes
    def test_geography_index(self, authenticated_org_user):
        """Test /org-admin/geography/ has csrf_token"""
        response = authenticated_org_user.get("/org-admin/geography/")
        self.assert_no_csrf_errors(response)

    # Super Admin Routes (require super admin)
    def test_super_admin_index(self, authenticated_super_admin):
        """Test /super-admin/ has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/")
        self.assert_no_csrf_errors(response)

    def test_super_admin_settings(self, authenticated_super_admin):
        """Test /super-admin/settings has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/settings")
        self.assert_no_csrf_errors(response)

    def test_super_admin_users(self, authenticated_super_admin):
        """Test /super-admin/users has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/users")
        self.assert_no_csrf_errors(response)

    def test_super_admin_logs(self, authenticated_super_admin):
        """Test /super-admin/logs has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/logs")
        self.assert_no_csrf_errors(response)

    def test_super_admin_health(self, authenticated_super_admin):
        """Test /super-admin/health has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/health")
        self.assert_no_csrf_errors(response)

    def test_super_admin_sso_settings(self, authenticated_super_admin):
        """Test /super-admin/settings/sso has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/settings/sso")
        self.assert_no_csrf_errors(response)

    def test_super_admin_security_settings(self, authenticated_super_admin):
        """Test /super-admin/settings/security has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/settings/security")
        self.assert_no_csrf_errors(response)

    def test_super_admin_maintenance_settings(self, authenticated_super_admin):
        """Test /super-admin/settings/maintenance has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/settings/maintenance")
        self.assert_no_csrf_errors(response)

    def test_super_admin_email_settings(self, authenticated_super_admin):
        """Test /super-admin/settings/email has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/settings/email")
        self.assert_no_csrf_errors(response)

    def test_super_admin_pending_users(self, authenticated_super_admin):
        """Test /super-admin/users/pending has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/users/pending")
        self.assert_no_csrf_errors(response)

    def test_super_admin_linked_kpis(self, authenticated_super_admin):
        """Test /super-admin/linked-kpis has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/linked-kpis")
        self.assert_no_csrf_errors(response)

    def test_super_admin_backup(self, authenticated_super_admin):
        """Test /super-admin/backup has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/backup")
        self.assert_no_csrf_errors(response)

    def test_super_admin_announcements_list(self, authenticated_super_admin):
        """Test /super-admin/announcements has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/announcements")
        self.assert_no_csrf_errors(response)

    def test_super_admin_announcements_create(self, authenticated_super_admin):
        """Test /super-admin/announcements/create has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/announcements/create")
        self.assert_no_csrf_errors(response)

    def test_super_admin_documentation(self, authenticated_super_admin):
        """Test /super-admin/documentation has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/documentation")
        self.assert_no_csrf_errors(response)

    def test_super_admin_bulk_operations(self, authenticated_super_admin):
        """Test /super-admin/bulk-operations has csrf_token"""
        response = authenticated_super_admin.get("/super-admin/bulk-operations")
        self.assert_no_csrf_errors(response)

    # Global Admin Routes
    def test_global_admin_index(self, authenticated_admin):
        """Test /global-admin/ has csrf_token"""
        response = authenticated_admin.get("/global-admin/")
        self.assert_no_csrf_errors(response)

    def test_global_admin_users(self, authenticated_admin):
        """Test /global-admin/users has csrf_token"""
        response = authenticated_admin.get("/global-admin/users")
        self.assert_no_csrf_errors(response)

    def test_global_admin_organizations(self, authenticated_admin):
        """Test /global-admin/organizations has csrf_token"""
        response = authenticated_admin.get("/global-admin/organizations")
        self.assert_no_csrf_errors(response)

    def test_global_admin_backup(self, authenticated_admin):
        """Test /global-admin/backup-restore has csrf_token"""
        response = authenticated_admin.get("/global-admin/backup-restore")
        self.assert_no_csrf_errors(response)

    def test_global_admin_health_dashboard(self, authenticated_admin):
        """Test /global-admin/health-dashboard has csrf_token"""
        response = authenticated_admin.get("/global-admin/health-dashboard")
        self.assert_no_csrf_errors(response)

    def test_global_admin_archived_orgs(self, authenticated_admin):
        """Test /global-admin/organizations/archived has csrf_token"""
        response = authenticated_admin.get("/global-admin/organizations/archived")
        self.assert_no_csrf_errors(response)


@pytest.mark.parametrize(
    "route",
    [
        # Organization Admin
        "/org-admin/",
        "/org-admin/challenges",
        "/org-admin/initiatives",
        "/org-admin/value-types",
        "/org-admin/governance-bodies",
        "/org-admin/yaml-upload",
        "/org-admin/geography/",
        # Workspace
        "/workspace/",
        "/workspace/snapshots/list",
        "/workspace/search",
        # Dashboards
        "/executive/dashboard",
        "/analytics/dashboard",
        "/map/",
        # Action Items & Memos
        "/toolbox/actions/",
        "/toolbox/actions/create",
    ],
)
class TestOrganizationRoutes:
    """Parametrized test for all organization-scoped routes"""

    def test_route_has_no_undefined_errors(self, client, org_user, sample_organization, route):
        """Test route has no csrf_token undefined errors"""
        with client:
            # Login
            client.post(
                "/auth/login",
                data={"login": org_user.login, "password": "password123"},
                follow_redirects=True,
            )

            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id
                sess["organization_name"] = sample_organization.name

            # Test route
            response = client.get(route)
            assert response.status_code == 200

            data = response.data.decode("utf-8")
            assert "UndefinedError" not in data, f"Found UndefinedError in {route}"
            assert "'csrf_token' is undefined" not in data, f"Found csrf_token undefined in {route}"


@pytest.mark.parametrize(
    "route",
    [
        "/global-admin/",
        "/global-admin/health-dashboard",
        "/global-admin/users",
        "/global-admin/organizations",
        "/global-admin/backup-restore",
        "/global-admin/organizations/archived",
    ],
)
class TestGlobalAdminRoutes:
    """Parametrized test for all global admin routes"""

    def test_route_has_no_undefined_errors(self, client, admin_user, route):
        """Test global admin route has no csrf_token undefined errors"""
        with client:
            # Login as admin
            client.post(
                "/auth/login",
                data={"login": admin_user.login, "password": "admin123"},
                follow_redirects=True,
            )

            # Test route
            response = client.get(route)
            assert response.status_code == 200

            data = response.data.decode("utf-8")
            assert "UndefinedError" not in data, f"Found UndefinedError in {route}"
            assert "'csrf_token' is undefined" not in data, f"Found csrf_token undefined in {route}"


@pytest.mark.parametrize(
    "route",
    [
        "/super-admin/",
        "/super-admin/settings",
        "/super-admin/users",
        "/super-admin/logs",
        "/super-admin/health",
        "/super-admin/settings/sso",
        "/super-admin/settings/security",
        "/super-admin/settings/maintenance",
        "/super-admin/settings/email",
        "/super-admin/users/pending",
        "/super-admin/linked-kpis",
        "/super-admin/backup",
        "/super-admin/announcements",
        "/super-admin/announcements/create",
        "/super-admin/documentation",
        "/super-admin/bulk-operations",
    ],
)
class TestSuperAdminRoutes:
    """Parametrized test for all super admin routes"""

    def test_route_has_no_undefined_errors(self, client, super_admin_user, route):
        """Test super admin route has no csrf_token undefined errors"""
        with client:
            # Login as super admin
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            # Test route
            response = client.get(route)
            assert response.status_code == 200

            data = response.data.decode("utf-8")
            assert "UndefinedError" not in data, f"Found UndefinedError in {route}"
            assert "'csrf_token' is undefined" not in data, f"Found csrf_token undefined in {route}"
