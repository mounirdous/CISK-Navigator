"""
Unit tests for CommentService
"""

import pytest

from app.models import (
    KPI,
    CellComment,
    Challenge,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    MentionNotification,
    Space,
    System,
    User,
    UserOrganizationMembership,
    ValueType,
)
from app.services.comment_service import CommentService


class TestCommentService:
    """Tests for CommentService"""

    def test_parse_mentions_single(self):
        """Test parsing single mention from text"""
        text = "Hey @john, can you check this?"
        mentions = CommentService.parse_mentions(text)

        assert mentions == ["john"]

    def test_parse_mentions_multiple(self):
        """Test parsing multiple mentions"""
        text = "CC @alice @bob @charlie"
        mentions = CommentService.parse_mentions(text)

        assert set(mentions) == {"alice", "bob", "charlie"}

    def test_parse_mentions_with_dots_and_underscores(self):
        """Test parsing usernames with special characters"""
        text = "@john.doe and @jane_smith please review"
        mentions = CommentService.parse_mentions(text)

        assert set(mentions) == {"john.doe", "jane_smith"}

    def test_parse_mentions_no_mentions(self):
        """Test text with no mentions"""
        text = "This is a regular comment without mentions"
        mentions = CommentService.parse_mentions(text)

        assert mentions == []

    def test_parse_mentions_deduplicates(self):
        """Test that duplicate mentions are deduplicated"""
        text = "@john @alice @john @alice"
        mentions = CommentService.parse_mentions(text)

        assert len(mentions) == 2
        assert set(mentions) == {"john", "alice"}

    def test_resolve_mentions_to_user_ids(self, db, sample_organization):
        """Test resolving usernames to user IDs"""
        # Create users in organization
        user1 = User(login="alice", email="alice@test.com", display_name="Alice", is_active=True)
        user1.set_password("pass")
        user2 = User(login="bob", email="bob@test.com", display_name="Bob", is_active=True)
        user2.set_password("pass")
        db.session.add_all([user1, user2])
        db.session.flush()

        # Add memberships
        membership1 = UserOrganizationMembership(user_id=user1.id, organization_id=sample_organization.id)
        membership2 = UserOrganizationMembership(user_id=user2.id, organization_id=sample_organization.id)
        db.session.add_all([membership1, membership2])
        db.session.commit()

        # Resolve mentions
        mentions = ["alice", "bob"]
        user_ids = CommentService.resolve_mentions_to_user_ids(mentions, sample_organization.id)

        assert len(user_ids) == 2
        assert user1.id in user_ids
        assert user2.id in user_ids

    def test_resolve_mentions_ignores_non_members(self, db, sample_organization):
        """Test that users not in organization are not resolved"""
        # Create user NOT in organization
        user = User(login="external", email="ext@test.com", display_name="External", is_active=True)
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()

        # Try to resolve
        mentions = ["external"]
        user_ids = CommentService.resolve_mentions_to_user_ids(mentions, sample_organization.id)

        assert user_ids == []

    def test_resolve_mentions_empty_list(self, db, sample_organization):
        """Test resolving empty mention list"""
        user_ids = CommentService.resolve_mentions_to_user_ids([], sample_organization.id)
        assert user_ids == []

    def test_create_comment(self, db, sample_organization, sample_user):
        """Test creating a comment"""
        # Setup KPI structure
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.commit()

        # Create comment
        comment = CommentService.create_comment(
            config_id=config.id,
            user_id=sample_user.id,
            comment_text="This is a test comment",
            organization_id=sample_organization.id,
        )

        assert comment is not None
        assert comment.comment_text == "This is a test comment"
        assert comment.user_id == sample_user.id
        assert comment.kpi_value_type_config_id == config.id

    def test_create_comment_with_mentions(self, db, sample_organization, sample_user):
        """Test creating comment with @mentions creates notifications"""
        # Create another user to mention
        mentioned_user = User(login="alice", email="alice@test.com", display_name="Alice", is_active=True)
        mentioned_user.set_password("pass")
        db.session.add(mentioned_user)
        db.session.flush()

        # Add membership
        membership = UserOrganizationMembership(user_id=mentioned_user.id, organization_id=sample_organization.id)
        db.session.add(membership)
        db.session.commit()

        # Setup KPI structure
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.commit()

        # Create comment with mention
        comment = CommentService.create_comment(
            config_id=config.id,
            user_id=sample_user.id,
            comment_text="Hey @alice, please review this value",
            organization_id=sample_organization.id,
        )

        # Check notification was created
        notification = MentionNotification.query.filter_by(
            comment_id=comment.id, mentioned_user_id=mentioned_user.id
        ).first()

        assert notification is not None
        assert notification.is_read is False

    def test_create_threaded_comment(self, db, sample_organization, sample_user):
        """Test creating a reply to another comment"""
        # Setup KPI structure
        space = Space(name="Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.flush()

        challenge = Challenge(
            name="Challenge", organization_id=sample_organization.id, space_id=space.id, display_order=1
        )
        db.session.add(challenge)
        db.session.flush()

        initiative = Initiative(name="Initiative", organization_id=sample_organization.id)
        system = System(name="System", organization_id=sample_organization.id)
        db.session.add_all([initiative, system])
        db.session.flush()

        link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(link)
        db.session.flush()

        kpi = KPI(name="KPI", initiative_system_link_id=link.id)
        db.session.add(kpi)
        db.session.flush()

        value_type = ValueType(name="Value", kind="numeric", organization_id=sample_organization.id, is_active=True)
        db.session.add(value_type)
        db.session.flush()

        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=value_type.id)
        db.session.add(config)
        db.session.commit()

        # Create parent comment
        parent_comment = CommentService.create_comment(
            config_id=config.id,
            user_id=sample_user.id,
            comment_text="Original comment",
            organization_id=sample_organization.id,
        )

        # Create reply
        reply_comment = CommentService.create_comment(
            config_id=config.id,
            user_id=sample_user.id,
            comment_text="This is a reply",
            parent_comment_id=parent_comment.id,
            organization_id=sample_organization.id,
        )

        assert reply_comment.parent_comment_id == parent_comment.id
        assert reply_comment.comment_text == "This is a reply"
