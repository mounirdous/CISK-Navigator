"""
Comment Service

Manages cell comments, @mentions (users and entities), and discussion threads.
"""

import re
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import CellComment, CommentEntityMention, MentionNotification, User, UserOrganizationMembership
from app.services.mention_service import MentionService


class CommentService:
    """Service for managing comments and mentions"""

    @staticmethod
    def parse_mentions(comment_text: str) -> List[str]:
        """
        Parse @mentions from comment text.

        Returns list of mentioned usernames (without @).

        Examples:
            "@john hello!" -> ["john"]
            "cc @alice @bob" -> ["alice", "bob"]
            "@jane.doe check this" -> ["jane.doe"]
        """
        # Match @username (alphanumeric, dots, underscores, hyphens)
        pattern = r"@([\w\.\-]+)"
        mentions = re.findall(pattern, comment_text)
        return list(set(mentions))  # Deduplicate

    @staticmethod
    def resolve_mentions_to_user_ids(mentions: List[str], organization_id: int) -> List[int]:
        """
        Convert usernames to user IDs within an organization.

        Args:
            mentions: List of usernames (without @)
            organization_id: Organization context

        Returns:
            List of user IDs
        """
        if not mentions:
            return []

        # Find users by login within this organization
        users = (
            db.session.query(User)
            .join(UserOrganizationMembership)
            .filter(User.login.in_(mentions), UserOrganizationMembership.organization_id == organization_id)
            .all()
        )

        return [user.id for user in users]

    @staticmethod
    def create_comment(
        config_id: int,
        user_id: int,
        comment_text: str,
        parent_comment_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> CellComment:
        """
        Create a new comment and process mentions (users and entities).

        Args:
            config_id: KPIValueTypeConfig ID
            user_id: User creating the comment
            comment_text: Comment text (may contain @mentions)
            parent_comment_id: Optional parent for threading
            organization_id: Organization context (required for mentions)

        Returns:
            Created CellComment
        """
        # Parse all mentions using shared service
        all_mentions = MentionService.parse_all_mentions(comment_text)
        mentioned_user_ids = []
        entity_mentions = []

        if organization_id:
            # Resolve user mentions
            if all_mentions["users"]:
                mentioned_user_ids = MentionService.resolve_user_mentions(all_mentions["users"], organization_id)

            # Resolve entity mentions
            if all_mentions["entities"]:
                entity_mentions = MentionService.resolve_entity_mentions(all_mentions["entities"], organization_id)

        # Create comment
        comment = CellComment(
            kpi_value_type_config_id=config_id,
            user_id=user_id,
            comment_text=comment_text,
            parent_comment_id=parent_comment_id,
            mentioned_user_ids=mentioned_user_ids,
        )

        db.session.add(comment)
        db.session.flush()  # Get comment ID

        # Create user mention notifications
        for mentioned_user_id in mentioned_user_ids:
            # Don't notify yourself
            if mentioned_user_id != user_id:
                notification = MentionNotification(mentioned_user_id=mentioned_user_id, comment_id=comment.id)
                db.session.add(notification)

        # Create entity mention records
        for entity_type, entity_id, mention_text in entity_mentions:
            entity_mention = CommentEntityMention(
                comment_id=comment.id, entity_type=entity_type, entity_id=entity_id, mention_text=mention_text
            )
            db.session.add(entity_mention)

        db.session.commit()
        return comment

    @staticmethod
    def update_comment(comment_id: int, comment_text: str, organization_id: Optional[int] = None) -> CellComment:
        """
        Update an existing comment.

        Re-parses mentions (users and entities) and updates notifications.
        """
        comment = CellComment.query.get(comment_id)
        if not comment:
            raise ValueError("Comment not found")

        # Parse all mentions using shared service
        all_mentions = MentionService.parse_all_mentions(comment_text)
        new_mentioned_user_ids = []
        new_entity_mentions = []

        if organization_id:
            # Resolve user mentions
            if all_mentions["users"]:
                new_mentioned_user_ids = MentionService.resolve_user_mentions(all_mentions["users"], organization_id)

            # Resolve entity mentions
            if all_mentions["entities"]:
                new_entity_mentions = MentionService.resolve_entity_mentions(all_mentions["entities"], organization_id)

        old_mentioned_user_ids = comment.mentioned_user_ids or []

        # Update comment
        comment.comment_text = comment_text
        comment.mentioned_user_ids = new_mentioned_user_ids
        comment.updated_at = datetime.utcnow()

        # Handle user mention notifications
        # Remove notifications for users no longer mentioned
        for user_id in old_mentioned_user_ids:
            if user_id not in new_mentioned_user_ids:
                MentionNotification.query.filter_by(comment_id=comment_id, mentioned_user_id=user_id).delete()

        # Add notifications for newly mentioned users
        for user_id in new_mentioned_user_ids:
            if user_id not in old_mentioned_user_ids and user_id != comment.user_id:
                notification = MentionNotification(mentioned_user_id=user_id, comment_id=comment_id)
                db.session.add(notification)

        # Handle entity mentions
        # Delete old entity mentions
        CommentEntityMention.query.filter_by(comment_id=comment_id).delete()

        # Create new entity mentions
        for entity_type, entity_id, mention_text in new_entity_mentions:
            entity_mention = CommentEntityMention(
                comment_id=comment_id, entity_type=entity_type, entity_id=entity_id, mention_text=mention_text
            )
            db.session.add(entity_mention)

        db.session.commit()
        return comment

    @staticmethod
    def delete_comment(comment_id: int) -> bool:
        """
        Delete a comment and all its replies.

        Returns True if deleted successfully.
        """
        comment = CellComment.query.get(comment_id)
        if not comment:
            return False

        # Delete all replies recursively
        for reply in comment.replies:
            CommentService.delete_comment(reply.id)

        # Delete the comment (notifications cascade automatically)
        db.session.delete(comment)
        db.session.commit()
        return True

    @staticmethod
    def resolve_comment(comment_id: int, user_id: int) -> CellComment:
        """
        Mark a comment as resolved.

        Also marks all mention notifications for the resolving user in this
        comment thread as read (comment + all replies).
        """
        comment = CellComment.query.get(comment_id)
        if not comment:
            raise ValueError("Comment not found")

        comment.is_resolved = True
        comment.resolved_by_user_id = user_id
        comment.resolved_at = datetime.utcnow()

        # Mark all mentions for this user in this comment thread as read
        def mark_mentions_read_recursive(comment_obj):
            """Recursively mark mentions as read in comment and all replies"""
            # Mark mentions in this comment
            MentionNotification.query.filter_by(
                comment_id=comment_obj.id, mentioned_user_id=user_id, is_read=False
            ).update({"is_read": True, "read_at": datetime.utcnow()})

            # Mark mentions in all replies
            for reply in comment_obj.replies:
                mark_mentions_read_recursive(reply)

        mark_mentions_read_recursive(comment)

        db.session.commit()
        return comment

    @staticmethod
    def unresolve_comment(comment_id: int) -> CellComment:
        """Mark a comment as unresolved"""
        comment = CellComment.query.get(comment_id)
        if not comment:
            raise ValueError("Comment not found")

        comment.is_resolved = False
        comment.resolved_by_user_id = None
        comment.resolved_at = None

        db.session.commit()
        return comment

    @staticmethod
    def get_comments_for_cell(config_id: int, include_resolved: bool = True) -> List[CellComment]:
        """
        Get all comments for a KPI cell.

        Returns top-level comments (no parents) with replies loaded.
        """
        query = CellComment.query.filter_by(
            kpi_value_type_config_id=config_id, parent_comment_id=None  # Top-level only
        )

        if not include_resolved:
            query = query.filter_by(is_resolved=False)

        return query.order_by(CellComment.created_at.desc()).all()

    @staticmethod
    def get_unread_mentions(user_id: int, limit: int = None) -> List[MentionNotification]:
        """Get unread mentions for a user with eager loading for performance"""
        query = (
            MentionNotification.query.options(joinedload(MentionNotification.comment).joinedload(CellComment.user))
            .filter_by(mentioned_user_id=user_id, is_read=False)
            .order_by(MentionNotification.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_unread_mentions_count(user_id: int) -> int:
        """Get total count of unread mentions for a user"""
        return MentionNotification.query.filter_by(mentioned_user_id=user_id, is_read=False).count()

    @staticmethod
    def mark_mention_read(notification_id: int) -> MentionNotification:
        """Mark a mention notification as read"""
        notification = MentionNotification.query.get(notification_id)
        if not notification:
            raise ValueError("Notification not found")

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        db.session.commit()
        return notification

    @staticmethod
    def mark_all_mentions_read(user_id: int) -> int:
        """
        Mark all mentions for a user as read.

        Returns count of notifications marked.
        """
        notifications = MentionNotification.query.filter_by(mentioned_user_id=user_id, is_read=False).all()

        count = len(notifications)

        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()

        db.session.commit()
        return count

    @staticmethod
    def get_comment_count_for_cell(config_id: int, include_resolved: bool = True) -> int:
        """Get total comment count for a cell"""
        query = CellComment.query.filter_by(kpi_value_type_config_id=config_id)

        if not include_resolved:
            query = query.filter_by(is_resolved=False)

        return query.count()

    @staticmethod
    def render_comment_with_mentions(comment_text: str, organization_id: int) -> str:
        """
        Convert @mentions (users and entities) to clickable links in HTML.

        Args:
            comment_text: Raw comment text
            organization_id: Organization context

        Returns:
            HTML with @mentions as styled elements
        """
        if not comment_text:
            return ""

        # Parse all mentions using shared service
        all_mentions = MentionService.parse_all_mentions(comment_text)

        result = comment_text

        # Resolve and render entity mentions first (to handle @"Entity Name" before simple @username)
        if all_mentions["entities"]:
            entity_mentions = MentionService.resolve_entity_mentions(all_mentions["entities"], organization_id)

            # Sort by length descending to replace longer matches first
            entity_mentions_sorted = sorted(entity_mentions, key=lambda x: len(x[2]), reverse=True)

            for entity_type, entity_id, mention_text in entity_mentions_sorted:
                # Get URL for entity
                entity_url = MentionService.get_entity_url(entity_type, entity_id)

                # Handle both @"Entity Name" and @EntityName patterns
                patterns = [f'@"{mention_text}"', f"@{mention_text}"]

                for pattern in patterns:
                    if pattern in result:
                        replacement = (
                            f'<a href="{entity_url}" '
                            f'class="badge bg-info text-white text-decoration-none" '
                            f'title="View {entity_type}: {mention_text}" '
                            f'target="_blank">'
                            f'{mention_text} <i class="bi bi-box-arrow-up-right"></i>'
                            f"</a>"
                        )
                        result = result.replace(pattern, replacement)

        # Resolve and render user mentions
        if all_mentions["users"]:
            user_ids = MentionService.resolve_user_mentions(all_mentions["users"], organization_id)

            if user_ids:
                users = db.session.query(User).filter(User.id.in_(user_ids)).all()
                user_map = {user.login: user for user in users}

                # Sort by length descending to replace longer usernames first
                sorted_usernames = sorted(all_mentions["users"], key=len, reverse=True)

                for username in sorted_usernames:
                    user = user_map.get(username)
                    if user:
                        pattern = f"@{username}"
                        # Only replace if not already part of an entity mention replacement
                        if pattern in result and "badge bg-info" not in result.split(pattern)[0][-50:]:
                            replacement = f'<span class="mention" data-user-id="{user.id}">@{user.display_name}</span>'
                            result = result.replace(pattern, replacement, 1)

        return result
