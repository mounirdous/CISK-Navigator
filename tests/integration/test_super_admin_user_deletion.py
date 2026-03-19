"""
Test user deletion with foreign key cleanup (v2.13.1 regression tests)
"""

from app.models import ActionItem, CellComment, SavedChart, User
from app.models.announcement import SystemAnnouncement
from app.models.cell_comment import MentionNotification


class TestBulkDeleteUsers:
    """Test bulk user deletion with comprehensive foreign key cleanup"""

    def test_delete_user_with_mention_notifications(self, app, db, super_admin_user, sample_organization):
        """Test deletion of user who was @mentioned in comments"""
        from app.models import (
            KPI,
            Challenge,
            Initiative,
            InitiativeSystemLink,
            KPIValueTypeConfig,
            Space,
            System,
            ValueType,
        )

        # Create organizational hierarchy
        space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            organization_id=sample_organization.id, space_id=space.id, name="Test Challenge", description="Test"
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(
            organization_id=sample_organization.id,
            challenge_id=challenge.id,
            name="Test Initiative",
            description="Test",
        )
        db.session.add(initiative)
        db.session.flush()

        # System is org-level, not space-level
        system = System(organization_id=sample_organization.id, name="Test System", description="Test")
        db.session.add(system)
        db.session.flush()

        # Link initiative to system
        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
        db.session.add(link)
        db.session.flush()

        # KPI belongs to the initiative-system link
        kpi = KPI(initiative_system_link_id=link.id, name="Test KPI", description="")
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(organization_id=sample_organization.id, name="Test Type", unit="units")
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id, is_primary=True)
        db.session.add(config)
        db.session.flush()

        # Create test user who will be mentioned
        mentioned_user = User(login="mentioned", email="mentioned@test.com", is_active=True)
        mentioned_user.set_password("password")
        db.session.add(mentioned_user)
        db.session.commit()

        # Create comment
        comment = CellComment(
            kpi_value_type_config_id=config.id, user_id=super_admin_user.id, comment_text="Test @mentioned comment"
        )
        db.session.add(comment)
        db.session.flush()

        # Create mention notification
        mention = MentionNotification(mentioned_user_id=mentioned_user.id, comment_id=comment.id, is_read=False)
        db.session.add(mention)
        db.session.commit()

        # Verify mention exists
        assert MentionNotification.query.filter_by(mentioned_user_id=mentioned_user.id).count() == 1

        # Login as super admin and delete user
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            delete_response = client.post(
                "/super-admin/bulk-operations/delete-users",
                data={"user_ids": [str(mentioned_user.id)]},
                follow_redirects=True,
            )

            assert delete_response.status_code == 200

            # Verify user deleted
            assert User.query.get(mentioned_user.id) is None

            # Verify mention notification deleted
            assert MentionNotification.query.filter_by(mentioned_user_id=mentioned_user.id).count() == 0

    def test_cannot_delete_user_with_announcements(self, app, db, super_admin_user):
        """Test that users who created announcements cannot be deleted"""
        # Create test user
        creator_user = User(login="creator", email="creator@test.com", is_active=True)
        creator_user.set_password("password")
        db.session.add(creator_user)
        db.session.commit()

        # Create announcement
        announcement = SystemAnnouncement(
            title="Test Announcement",
            message="Test message",
            banner_type="info",
            target_type="all",
            is_active=True,
            created_by=creator_user.id,
        )
        db.session.add(announcement)
        db.session.commit()

        # Verify announcement exists
        assert SystemAnnouncement.query.filter_by(created_by=creator_user.id).count() == 1

        # Attempt to delete user
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            delete_response = client.post(
                "/super-admin/bulk-operations/delete-users",
                data={"user_ids": [str(creator_user.id)]},
                follow_redirects=True,
            )

            # Verify user NOT deleted
            assert User.query.get(creator_user.id) is not None

            # Verify warning message shown
            assert b"has 1 system announcement" in delete_response.data or b"announcement" in delete_response.data

    def test_delete_user_cleans_cell_comments(self, app, db, super_admin_user, sample_organization):
        """Test that cell comments are deleted when deleting user"""
        from app.models import (
            KPI,
            Challenge,
            Initiative,
            InitiativeSystemLink,
            KPIValueTypeConfig,
            Space,
            System,
            ValueType,
        )

        # Create organizational hierarchy
        space = Space(organization_id=sample_organization.id, name="Test Space", description="Test")
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            organization_id=sample_organization.id, space_id=space.id, name="Test Challenge", description="Test"
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(
            organization_id=sample_organization.id,
            challenge_id=challenge.id,
            name="Test Initiative",
            description="Test",
        )
        db.session.add(initiative)
        db.session.flush()

        system = System(organization_id=sample_organization.id, name="Test System", description="Test")
        db.session.add(system)
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(initiative_system_link_id=link.id, name="Test KPI", description="")
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(organization_id=sample_organization.id, name="Test Type", unit="units")
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id, is_primary=True)
        db.session.add(config)
        db.session.flush()

        # Create test user
        test_user = User(login="testuser", email="test@test.com", is_active=True)
        test_user.set_password("password")
        db.session.add(test_user)
        db.session.commit()

        # Create cell comment
        comment = CellComment(kpi_value_type_config_id=config.id, user_id=test_user.id, comment_text="Test comment")
        db.session.add(comment)
        db.session.commit()

        # Verify comment exists
        assert CellComment.query.filter_by(user_id=test_user.id).count() == 1

        # Delete user
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            client.post("/super-admin/bulk-operations/delete-users", data={"user_ids": [str(test_user.id)]})

            # Verify comment deleted
            assert CellComment.query.filter_by(user_id=test_user.id).count() == 0

    def test_delete_user_cleans_action_items(self, app, db, super_admin_user, sample_organization):
        """Test that action items are deleted when deleting user"""
        # Create test user
        test_user = User(login="testuser", email="test@test.com", is_active=True)
        test_user.set_password("password")
        db.session.add(test_user)
        db.session.commit()

        # Create action items (owned and created by user)
        action_owned = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=test_user.id,
            created_by_user_id=super_admin_user.id,
            title="Owned by test user",
            type="action",
            status="active",
        )
        db.session.add(action_owned)

        action_created = ActionItem(
            organization_id=sample_organization.id,
            owner_user_id=super_admin_user.id,
            created_by_user_id=test_user.id,
            title="Created by test user",
            type="action",
            status="active",
        )
        db.session.add(action_created)
        db.session.commit()

        # Verify action items exist
        assert ActionItem.query.filter_by(owner_user_id=test_user.id).count() == 1
        assert ActionItem.query.filter_by(created_by_user_id=test_user.id).count() == 1

        # Delete user
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            client.post("/super-admin/bulk-operations/delete-users", data={"user_ids": [str(test_user.id)]})

            # Verify action items deleted
            assert ActionItem.query.filter_by(owner_user_id=test_user.id).count() == 0
            assert ActionItem.query.filter_by(created_by_user_id=test_user.id).count() == 0

    def test_delete_user_cleans_saved_charts(self, app, db, super_admin_user, sample_organization):
        """Test that saved charts are deleted when deleting user"""
        # Create test user
        test_user = User(login="testuser", email="test@test.com", is_active=True)
        test_user.set_password("password")
        db.session.add(test_user)
        db.session.commit()

        # Create saved chart using correct SavedChart fields
        chart = SavedChart(
            created_by_user_id=test_user.id,
            organization_id=sample_organization.id,
            name="Test Chart",
            year_start=2024,
            year_end=2024,
            view_type="monthly",
            chart_type="line",
            config_ids_colors='{"114": "#007bff"}',
        )
        db.session.add(chart)
        db.session.commit()

        # Verify chart exists
        assert SavedChart.query.filter_by(created_by_user_id=test_user.id).count() == 1

        # Delete user
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            client.post("/super-admin/bulk-operations/delete-users", data={"user_ids": [str(test_user.id)]})

            # Verify chart deleted
            assert SavedChart.query.filter_by(created_by_user_id=test_user.id).count() == 0

    def test_cannot_delete_super_admin(self, app, db, super_admin_user):
        """Test that super admins cannot be deleted"""
        # Create another super admin to try to delete
        super_admin_2 = User(
            login="superadmin2", email="superadmin2@test.com", is_active=True, is_super_admin=True, is_global_admin=True
        )
        super_admin_2.set_password("password")
        db.session.add(super_admin_2)
        db.session.commit()

        # Attempt to delete super admin
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            delete_response = client.post(
                "/super-admin/bulk-operations/delete-users",
                data={"user_ids": [str(super_admin_2.id)]},
                follow_redirects=True,
            )

            # Verify super admin NOT deleted
            assert User.query.get(super_admin_2.id) is not None

            # Verify warning message shown
            assert b"Cannot delete super admin" in delete_response.data

    def test_cannot_delete_current_user(self, app, db, super_admin_user):
        """Test that users cannot delete themselves"""
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            delete_response = client.post(
                "/super-admin/bulk-operations/delete-users",
                data={"user_ids": [str(super_admin_user.id)]},
                follow_redirects=True,
            )

            # Verify user NOT deleted
            assert User.query.get(super_admin_user.id) is not None

            # Verify warning message shown
            assert b"Cannot delete your own account" in delete_response.data

    def test_bulk_delete_multiple_users(self, app, db, super_admin_user):
        """Test deleting multiple users at once"""
        # Create test users
        user1 = User(login="user1", email="user1@test.com", is_active=True)
        user1.set_password("password")
        db.session.add(user1)

        user2 = User(login="user2", email="user2@test.com", is_active=True)
        user2.set_password("password")
        db.session.add(user2)

        db.session.commit()

        # Delete both users
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            delete_response = client.post(
                "/super-admin/bulk-operations/delete-users",
                data={"user_ids": [str(user1.id), str(user2.id)]},
                follow_redirects=True,
            )

            # Verify both users deleted
            assert User.query.get(user1.id) is None
            assert User.query.get(user2.id) is None

            # Verify success message
            assert b"Successfully deleted 2 user" in delete_response.data

    def test_bulk_delete_no_users_selected(self, app, db, super_admin_user):
        """Test bulk delete with no users selected"""
        with app.test_client() as client:
            client.post(
                "/auth/login",
                data={"login": super_admin_user.login, "password": "superadmin123"},
                follow_redirects=True,
            )

            delete_response = client.post(
                "/super-admin/bulk-operations/delete-users", data={"user_ids": []}, follow_redirects=True
            )

            # Verify warning message
            assert b"No users selected" in delete_response.data
