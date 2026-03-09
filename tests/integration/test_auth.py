"""
Integration tests for authentication
"""

import pytest


class TestLogin:
    """Tests for login functionality"""

    def test_login_page_loads(self, client):
        """Test login page is accessible"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Login" in response.data or b"login" in response.data

    def test_valid_login(self, client, sample_user):
        """Test login with valid credentials"""
        response = client.post(
            "/auth/login", data={"login": sample_user.login, "password": "password123"}, follow_redirects=True
        )

        assert response.status_code == 200
        # Should redirect to organization selection or dashboard

    def test_invalid_login(self, client):
        """Test login with invalid credentials fails"""
        response = client.post(
            "/auth/login", data={"login": "nonexistent", "password": "wrongpassword"}, follow_redirects=True
        )

        assert response.status_code == 200
        # Should show error message
        data_lower = response.data.decode("utf-8").lower()
        assert b"Invalid" in response.data or "incorrect" in data_lower

    def test_inactive_user_cannot_login(self, client, db, sample_user):
        """Test inactive users cannot login"""
        # Make user inactive
        sample_user.is_active = False
        db.session.commit()

        response = client.post(
            "/auth/login", data={"login": sample_user.login, "password": "password123"}, follow_redirects=True
        )

        assert response.status_code == 200
        # Should deny access
        data_lower = response.data.decode("utf-8").lower()
        assert "inactive" in data_lower or "disabled" in data_lower

    def test_logout(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.get("/auth/logout", follow_redirects=True)
        assert response.status_code == 200

        # After logout, accessing protected page should redirect to login
        response = authenticated_client.get("/workspace/dashboard")
        data_lower = response.data.decode("utf-8").lower()
        assert response.status_code == 302 or "login" in data_lower


class TestPermissions:
    """Tests for permission system"""

    def test_global_admin_can_access_admin_pages(self, client, admin_user):
        """Test global admin can access admin pages"""
        # Login as admin
        client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

        # Should be able to access global admin index
        response = client.get("/global-admin/")
        assert response.status_code == 200

    def test_regular_user_cannot_access_admin_pages(self, client, sample_user):
        """Test regular users cannot access admin pages"""
        # Login as regular user
        client.post("/auth/login", data={"login": sample_user.login, "password": "password123"}, follow_redirects=True)

        # Should be denied access to global admin
        response = client.get("/global-admin/", follow_redirects=True)
        # Should either be 403, redirected, or show login/permission message
        assert response.status_code in [403, 302, 200]
        if response.status_code == 200:
            data_lower = response.data.decode("utf-8").lower()
            # Flask-Login redirects and shows "please log in" for unauthorized access
            assert "denied" in data_lower or "permission" in data_lower or "please log in" in data_lower

    def test_unauthenticated_user_redirected_to_login(self, client):
        """Test unauthenticated users are redirected to login"""
        response = client.get("/workspace/dashboard")
        assert response.status_code == 302  # Redirect
        assert "login" in response.location.lower() or response.location.endswith("/auth/login")
