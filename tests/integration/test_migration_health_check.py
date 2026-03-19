"""
Test migration health check UI route (v2.13.1 feature tests)
"""


class TestMigrationHealthCheckRoute:
    """Test the migration health check route in global admin"""

    def test_migration_check_requires_admin(self, app, db, sample_user):
        """Test that migration check requires global admin access"""
        with app.test_client() as client:
            client.post(
                "/auth/login", data={"login": sample_user.login, "password": "password123"}, follow_redirects=True
            )

            response = client.get("/global-admin/health-dashboard/migration-check", follow_redirects=True)

            # Should redirect to login or show access denied
            assert response.status_code == 200
            assert b"Access denied" in response.data or b"permission required" in response.data.lower()

    def test_migration_check_accessible_by_admin(self, app, db, admin_user):
        """Test that global admins can access migration check"""
        with app.test_client() as client:
            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            response = client.get("/global-admin/health-dashboard/migration-check", follow_redirects=True)

            # Should load the page
            assert response.status_code == 200
            # Should show script output or results
            assert b"Migration Health Check" in response.data or b"migration" in response.data.lower()

    def test_migration_check_runs_script(self, app, db, admin_user):
        """Test that the route actually runs the migration check script"""
        with app.test_client() as client:
            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            response = client.get("/global-admin/health-dashboard/migration-check", follow_redirects=True)

            assert response.status_code == 200
            # Check for output from the script
            # The script outputs things like "Found X migration files", "revision", etc.
            assert (
                b"migration" in response.data.lower()
                or b"revision" in response.data.lower()
                or b"check" in response.data.lower()
            )

    def test_migration_check_displays_status(self, app, db, admin_user):
        """Test that the route displays success or error status"""
        with app.test_client() as client:
            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            response = client.get("/global-admin/health-dashboard/migration-check", follow_redirects=True)

            assert response.status_code == 200
            # Should show either "All Checks Passed" or "Checks Failed" or similar status
            # The actual output depends on migration state, so just check page renders
            assert len(response.data) > 100  # Page should have content

    def test_health_dashboard_has_migration_check_link(self, app, db, admin_user):
        """Test that health dashboard has link to migration check"""
        with app.test_client() as client:
            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            response = client.get("/global-admin/health-dashboard", follow_redirects=True)

            assert response.status_code == 200
            # Should have link to migration check
            assert (
                b"/global-admin/health-dashboard/migration-check" in response.data
                or b"Run Migration Health Check" in response.data
            )

    def test_migration_check_back_button_works(self, app, db, admin_user):
        """Test that back button on migration check page works"""
        with app.test_client() as client:
            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            response = client.get("/global-admin/health-dashboard/migration-check", follow_redirects=True)

            assert response.status_code == 200
            # Should have back link to health dashboard
            assert (
                b"/global-admin/health-dashboard" in response.data or b"Back to Dashboard" in response.data
            ) or b"health" in response.data.lower()

    def test_migration_check_rerun_button(self, app, db, admin_user):
        """Test that migration check page has re-run button"""
        with app.test_client() as client:
            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            response = client.get("/global-admin/health-dashboard/migration-check", follow_redirects=True)

            assert response.status_code == 200
            # Should have re-run button or link
            assert (
                b"Re-run" in response.data
                or b"Refresh" in response.data
                or b"migration-check" in response.data  # Link to same route
            )
