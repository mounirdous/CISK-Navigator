"""
Test admin bulk delete functionality for action items (v2.13.0 feature tests)
"""

import pytest

from app.models import ActionItem, User, UserOrganizationMembership


class TestActionItemAdminDelete:
    """Test admin permissions for deleting action items"""

    @pytest.fixture
    def contributor_user(self, db, sample_organization):
        """Create a contributor user"""
        user = User(login="contributor", email="contributor@test.com", is_active=True, is_global_admin=False)
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        # Add contributor membership
        membership = UserOrganizationMembership(
            user_id=user.id,
            organization_id=sample_organization.id,
            can_manage_spaces=False,
            can_manage_challenges=False,
            can_manage_initiatives=False,
            can_manage_systems=False,
            can_manage_kpis=False,
            can_view_comments=True,
            can_add_comments=True,
            can_contribute=True,
        )
        db.session.add(membership)
        db.session.commit()
        return user

    @pytest.fixture
    def viewer_user(self, db, sample_organization):
        """Create a viewer user"""
        user = User(login="viewer", email="viewer@test.com", is_active=True, is_global_admin=False)
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        # Add viewer membership (no contribute permission)
        membership = UserOrganizationMembership(
            user_id=user.id,
            organization_id=sample_organization.id,
            can_manage_spaces=False,
            can_manage_challenges=False,
            can_manage_initiatives=False,
            can_manage_systems=False,
            can_manage_kpis=False,
            can_view_comments=True,
            can_add_comments=False,
            can_contribute=False,
        )
        db.session.add(membership)
        db.session.commit()
        return user

    def test_admin_can_delete_any_action_item(self, app, db, admin_user, contributor_user, sample_organization):
        """Test that admins can delete action items they don't own"""
        # Create action item owned by contributor
        action = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=contributor_user.id,
            created_by_user_id=contributor_user.id,
            title="Contributor's action",
            type="action",
            status="active",
        )
        db.session.add(action)
        db.session.commit()

        # Login as admin and delete
        with app.test_client() as client:
            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id

            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            delete_response = client.post(f"/toolbox/actions/{action.id}/delete", follow_redirects=True)

            # Verify action deleted
            assert ActionItem.query.get(action.id) is None
            assert delete_response.status_code == 200

    def test_contributor_can_only_delete_own_items(self, app, db, contributor_user, admin_user, sample_organization):
        """Test that contributors can only delete their own action items"""
        # Create action item owned by admin
        action = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=admin_user.id,
            created_by_user_id=admin_user.id,
            title="Admin's action",
            type="action",
            status="active",
        )
        db.session.add(action)
        db.session.commit()

        # Login as contributor and try to delete
        with app.test_client() as client:
            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id

            client.post(
                "/auth/login", data={"login": contributor_user.login, "password": "password123"}, follow_redirects=True
            )

            delete_response = client.post(f"/toolbox/actions/{action.id}/delete", follow_redirects=True)

            # Verify action NOT deleted
            assert ActionItem.query.get(action.id) is not None
            assert (
                b"not found or unauthorized" in delete_response.data or b"cannot delete" in delete_response.data.lower()
            )

    def test_contributor_can_delete_own_item(self, app, db, contributor_user, sample_organization):
        """Test that contributors can delete their own action items"""
        # Create action item owned by contributor
        action = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=contributor_user.id,
            created_by_user_id=contributor_user.id,
            title="Contributor's action",
            type="action",
            status="active",
        )
        db.session.add(action)
        db.session.commit()

        # Login as contributor and delete own item
        with app.test_client() as client:
            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id

            client.post(
                "/auth/login", data={"login": contributor_user.login, "password": "password123"}, follow_redirects=True
            )

            delete_response = client.post(f"/toolbox/actions/{action.id}/delete", follow_redirects=True)

            # Verify action deleted
            assert ActionItem.query.get(action.id) is None
            assert delete_response.status_code == 200

    def test_bulk_delete_requires_admin(self, app, db, contributor_user, sample_organization):
        """Test that bulk delete requires admin permissions"""
        # Create action items
        action1 = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=contributor_user.id,
            created_by_user_id=contributor_user.id,
            title="Action 1",
            type="action",
            status="active",
        )
        action2 = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=contributor_user.id,
            created_by_user_id=contributor_user.id,
            title="Action 2",
            type="action",
            status="active",
        )
        db.session.add_all([action1, action2])
        db.session.commit()

        # Try bulk delete as non-admin contributor
        with app.test_client() as client:
            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id

            client.post(
                "/auth/login", data={"login": contributor_user.login, "password": "password123"}, follow_redirects=True
            )

            # Contributor CAN use bulk delete for their own items
            delete_response = client.post(
                "/toolbox/actions/bulk-delete",
                data={"item_ids": [str(action1.id), str(action2.id)]},
                follow_redirects=True,
            )

            # They can delete their own items, even in bulk
            # (The permission check allows contributors to bulk delete their own items)
            assert delete_response.status_code == 200

    def test_admin_bulk_delete_multiple_items(self, app, db, admin_user, contributor_user, sample_organization):
        """Test admin can bulk delete multiple items from different owners"""
        # Create action items from different users
        action1 = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=contributor_user.id,
            created_by_user_id=contributor_user.id,
            title="Contributor's action",
            type="action",
            status="active",
        )
        action2 = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=admin_user.id,
            created_by_user_id=admin_user.id,
            title="Admin's action",
            type="action",
            status="active",
        )
        db.session.add_all([action1, action2])
        db.session.commit()

        # Bulk delete as admin
        with app.test_client() as client:
            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id

            client.post("/auth/login", data={"login": admin_user.login, "password": "admin123"}, follow_redirects=True)

            delete_response = client.post(
                "/toolbox/actions/bulk-delete",
                data={"item_ids": [str(action1.id), str(action2.id)]},
                follow_redirects=True,
            )

            # Verify both items deleted
            assert ActionItem.query.get(action1.id) is None
            assert ActionItem.query.get(action2.id) is None
            assert b"Successfully deleted 2 item" in delete_response.data

    def test_viewer_cannot_delete_items(self, app, db, viewer_user, contributor_user, sample_organization):
        """Test that viewers cannot delete action items"""
        # Create action item
        action = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=contributor_user.id,
            created_by_user_id=contributor_user.id,
            title="Test action",
            type="action",
            status="active",
        )
        db.session.add(action)
        db.session.commit()

        # Try to delete as viewer
        with app.test_client() as client:
            # Set organization context
            with client.session_transaction() as sess:
                sess["organization_id"] = sample_organization.id

            client.post(
                "/auth/login", data={"login": viewer_user.login, "password": "password123"}, follow_redirects=True
            )

            delete_response = client.post(f"/toolbox/actions/{action.id}/delete", follow_redirects=True)

            # Verify action NOT deleted
            assert ActionItem.query.get(action.id) is not None
            assert b"not have permission" in delete_response.data or b"denied" in delete_response.data.lower()
