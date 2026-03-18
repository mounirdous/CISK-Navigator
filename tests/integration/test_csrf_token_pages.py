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

    # Auth Routes
    def test_auth_change_password(self, authenticated_org_user):
        """Test /auth/change-password has csrf_token"""
        response = authenticated_org_user.get("/auth/change-password")
        self.assert_no_csrf_errors(response)

    def test_org_admin_onboarding(self, authenticated_org_user, sample_organization):
        """Test /org-admin/onboarding has csrf_token"""
        response = authenticated_org_user.get(f"/org-admin/onboarding?org_id={sample_organization.id}")
        self.assert_no_csrf_errors(response)

    def test_action_items_edit(self, authenticated_org_user, sample_organization, org_user):
        """Test /toolbox/actions/<id>/edit has csrf_token"""
        from app import db
        from app.models import ActionItem

        # Create a test action item
        action_item = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=org_user.id,
            created_by_user_id=org_user.id,
            title="Test Action",
            description="Test Description",
            type="action",
            status="active",
            priority="medium",
            visibility="shared",
        )
        db.session.add(action_item)
        db.session.commit()

        response = authenticated_org_user.get(f"/toolbox/actions/{action_item.id}/edit")
        self.assert_no_csrf_errors(response)

    def test_space_swot(self, authenticated_org_user, sample_organization, org_user):
        """Test /org-admin/spaces/<id>/swot has csrf_token"""
        from app import db
        from app.models import Space

        # Create a test space
        space = Space(
            name="Test Space",
            description="Test Description",
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(space)
        db.session.commit()

        response = authenticated_org_user.get(f"/org-admin/spaces/{space.id}/swot")
        self.assert_no_csrf_errors(response)

    def test_porters_edit(self, authenticated_org_user, sample_organization, org_user):
        """Test /org-admin/porters/edit has csrf_token and handles permissions correctly"""
        from app import db

        # Give user permission to edit Porter's
        membership = org_user.get_membership(sample_organization.id)
        membership.can_edit_porters = True
        db.session.commit()

        response = authenticated_org_user.get("/org-admin/porters/edit")
        self.assert_no_csrf_errors(response)

        # Test permission denial
        membership.can_edit_porters = False
        db.session.commit()

        response = authenticated_org_user.get("/org-admin/porters/edit", follow_redirects=False)
        assert response.status_code == 302  # Should redirect
        assert "/org-admin/porters" in response.location  # Should redirect to view page

    def test_entity_create_edit_routes(self, authenticated_org_user, sample_organization, org_user):
        """Test all create/edit entity routes have csrf_token"""
        from app import db
        from app.models import Challenge, GovernanceBody, Initiative, Space, System, ValueType

        # Give user full permissions
        membership = org_user.get_membership(sample_organization.id)
        membership.can_manage_spaces = True
        membership.can_manage_challenges = True
        membership.can_manage_initiatives = True
        membership.can_manage_systems = True
        membership.can_manage_kpis = True
        membership.can_manage_value_types = True
        membership.can_manage_governance_bodies = True
        db.session.commit()

        # Create test space
        space = Space(
            name="Test Space",
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(space)
        db.session.commit()

        # Test space routes
        response = authenticated_org_user.get("/org-admin/spaces/create")
        self.assert_no_csrf_errors(response)

        response = authenticated_org_user.get(f"/org-admin/spaces/{space.id}/edit")
        self.assert_no_csrf_errors(response)

        response = authenticated_org_user.get(f"/org-admin/spaces/{space.id}/swot/edit")
        self.assert_no_csrf_errors(response)

        # Create test challenge
        challenge = Challenge(
            name="Test Challenge",
            space_id=space.id,
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(challenge)
        db.session.commit()

        # Test challenge routes
        response = authenticated_org_user.get(f"/org-admin/spaces/{space.id}/challenges/create")
        self.assert_no_csrf_errors(response)

        response = authenticated_org_user.get(f"/org-admin/challenges/{challenge.id}/edit")
        self.assert_no_csrf_errors(response)

        # Create test initiative
        initiative = Initiative(
            name="Test Initiative",
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(initiative)
        db.session.flush()

        # Link initiative to challenge
        from app.models import ChallengeInitiativeLink

        link = ChallengeInitiativeLink(challenge_id=challenge.id, initiative_id=initiative.id, display_order=1)
        db.session.add(link)
        db.session.commit()

        # Test initiative routes
        response = authenticated_org_user.get(f"/org-admin/challenges/{challenge.id}/initiatives/create")
        self.assert_no_csrf_errors(response)

        response = authenticated_org_user.get(f"/org-admin/initiatives/{initiative.id}/edit")
        self.assert_no_csrf_errors(response)

        # Create test system
        system = System(
            name="Test System",
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(system)
        db.session.flush()

        # Link system to initiative
        from app.models import InitiativeSystemLink

        sys_link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(sys_link)
        db.session.commit()

        # Test system routes
        response = authenticated_org_user.get(f"/org-admin/initiatives/{initiative.id}/systems/create")
        self.assert_no_csrf_errors(response)

        response = authenticated_org_user.get(f"/org-admin/systems/{system.id}/edit")
        self.assert_no_csrf_errors(response)

        # Test KPI routes
        response = authenticated_org_user.get(f"/org-admin/systems/{system.id}/kpis/create")
        self.assert_no_csrf_errors(response)

        # Test value type routes
        response = authenticated_org_user.get("/org-admin/value-types/create")
        self.assert_no_csrf_errors(response)

        # Create test value type for edit
        value_type = ValueType(
            name="Test VT",
            unit_label="units",
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(value_type)
        db.session.commit()

        response = authenticated_org_user.get(f"/org-admin/value-types/{value_type.id}/edit")
        self.assert_no_csrf_errors(response)

        # Test governance body routes
        response = authenticated_org_user.get("/org-admin/governance-bodies/create")
        self.assert_no_csrf_errors(response)

        # Create test governance body for edit
        gb = GovernanceBody(
            name="Test GB",
            abbreviation="TGB",
            organization_id=sample_organization.id,
            created_by=org_user.id,
        )
        db.session.add(gb)
        db.session.commit()

        response = authenticated_org_user.get(f"/org-admin/governance-bodies/{gb.id}/edit")
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
        "/org-admin/porters",
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
        # Stakeholder Mapping
        "/stakeholders/",
        "/stakeholders/list",
        "/stakeholders/matrix",
        "/stakeholders/maps",
        "/stakeholders/maps/create",
        "/stakeholders/create",
    ],
)
class TestOrganizationRoutes:
    """Parametrized test for all organization-scoped routes"""

    def test_route_has_no_undefined_errors(self, client, org_user, sample_organization, route):
        """Test route has no csrf_token undefined errors"""
        # For stakeholder routes, user needs org admin permission
        if route.startswith("/stakeholders"):
            membership = org_user.get_membership(sample_organization.id)
            if membership:
                membership.is_org_admin = True
                from app import db

                db.session.commit()

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

            # Test route - add organization_id param for stakeholder routes
            test_url = route
            if route.startswith("/stakeholders"):
                test_url = f"{route}?organization_id={sample_organization.id}"

            response = client.get(test_url)
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
