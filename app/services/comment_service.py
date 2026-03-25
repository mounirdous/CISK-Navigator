"""
Comment Service

Manages cell comments, @mentions (users and entities), and discussion threads.
"""

import re
from datetime import datetime
from typing import List, Optional

from flask import url_for
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    CellComment,
    CommentEntityMention,
    CommentUserMention,
    MentionNotification,
    User,
    UserOrganizationMembership,
)
from app.services.email_service import EmailService
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
        # List of (login, user_id) pairs for stable ID storage
        user_mention_pairs = []

        if organization_id:
            # Resolve user mentions — returns list of (login, user_id)
            if all_mentions["users"]:
                user_mention_pairs = MentionService.resolve_user_mentions_with_logins(
                    all_mentions["users"], organization_id
                )
                mentioned_user_ids = [uid for _, uid in user_mention_pairs]

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

        # Store user mentions by ID (login → user_id mapping, rename-safe)
        for mention_login, mention_user_id in user_mention_pairs:
            db.session.add(
                CommentUserMention(comment_id=comment.id, user_id=mention_user_id, mention_login=mention_login)
            )

        # Create entity mention records
        for entity_type, entity_id, mention_text in entity_mentions:
            entity_mention = CommentEntityMention(
                comment_id=comment.id, entity_type=entity_type, entity_id=entity_id, mention_text=mention_text
            )
            db.session.add(entity_mention)

        db.session.commit()

        # Send email notifications for mentions (after commit)
        from app.models import KPIValueTypeConfig

        config = KPIValueTypeConfig.query.get(config_id)
        if config and config.kpi:
            kpi_name = config.kpi.name
            # Build comment URL
            try:
                comment_url = url_for(
                    "workspace.index", kpi_id=config.kpi.id, _anchor=f"comment-{comment.id}", _external=True
                )
            except RuntimeError:
                # If not in request context, use relative URL
                comment_url = f"/workspace?kpi_id={config.kpi.id}#comment-{comment.id}"

            for mentioned_user_id in mentioned_user_ids:
                if mentioned_user_id != user_id:
                    mentioned_user = User.query.get(mentioned_user_id)
                    if mentioned_user and mentioned_user.email:
                        try:
                            EmailService.send_mention_notification(
                                user_email=mentioned_user.email,
                                user_name=mentioned_user.display_name or mentioned_user.login,
                                comment_text=comment_text,
                                kpi_name=kpi_name,
                                comment_url=comment_url,
                            )
                        except Exception as e:
                            # Log error but don't fail the comment creation
                            print(f"Failed to send mention email to {mentioned_user.email}: {e}")

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
        new_user_mention_pairs = []
        new_mentioned_user_ids = []
        new_entity_mentions = []

        if organization_id:
            # Resolve user mentions — returns list of (login, user_id)
            if all_mentions["users"]:
                new_user_mention_pairs = MentionService.resolve_user_mentions_with_logins(
                    all_mentions["users"], organization_id
                )
                new_mentioned_user_ids = [uid for _, uid in new_user_mention_pairs]

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

        # Replace stored user mention ID records
        CommentUserMention.query.filter_by(comment_id=comment_id).delete()
        for mention_login, mention_user_id in new_user_mention_pairs:
            db.session.add(
                CommentUserMention(comment_id=comment_id, user_id=mention_user_id, mention_login=mention_login)
            )

        # Handle entity mentions — replace all
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
    def render_comment_with_mentions(comment_text: str, organization_id: int, comment_id: int = None) -> str:
        """
        Convert @mentions (users and entities) to clickable links in HTML.

        Uses stored IDs from CommentEntityMention / CommentUserMention when comment_id
        is provided (rename-safe). Falls back to name-based resolution for old comments
        that pre-date the ID storage.

        Args:
            comment_text: Raw comment text
            organization_id: Organization context
            comment_id: Comment ID — enables ID-based lookup (rename-safe)

        Returns:
            HTML with @mentions as styled elements
        """
        if not comment_text:
            return ""

        result = comment_text

        # ── Entity mentions ────────────────────────────────────────────────────
        # Prefer stored CommentEntityMention records (already had IDs from day 1)
        if comment_id:
            stored_entity_mentions = CommentEntityMention.query.filter_by(comment_id=comment_id).all()
            entity_mentions = [(m.entity_type, m.entity_id, m.mention_text) for m in stored_entity_mentions]
        else:
            # No comment_id supplied — parse and resolve by name (legacy path)
            all_mentions = MentionService.parse_all_mentions(comment_text)
            entity_mentions = (
                MentionService.resolve_entity_mentions(all_mentions["entities"], organization_id)
                if all_mentions["entities"]
                else []
            )

        # Sort by mention_text length descending so longer names are replaced first
        entity_mentions_sorted = sorted(entity_mentions, key=lambda x: len(x[2]), reverse=True)

        for entity_type, entity_id, mention_text in entity_mentions_sorted:
            entity_url = MentionService.get_entity_url(entity_type, entity_id, comment_id=comment_id)
            for pattern in [f'@"{mention_text}"', f"@{mention_text}"]:
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

        # ── User mentions ──────────────────────────────────────────────────────
        # Use stored CommentUserMention records when available (rename-safe)
        if comment_id:
            stored_user_mentions = CommentUserMention.query.filter_by(comment_id=comment_id).all()
            # login → User object map via stored user_id
            stored_ids = [m.user_id for m in stored_user_mentions if m.user_id is not None]
            users_by_id = {}
            if stored_ids:
                for u in db.session.query(User).filter(User.id.in_(stored_ids)).all():
                    users_by_id[u.id] = u
            # Build login → user map using the *original* login text
            user_map = {}
            for m in stored_user_mentions:
                if m.user_id and m.user_id in users_by_id:
                    user_map[m.mention_login] = users_by_id[m.user_id]
            usernames_to_render = sorted(user_map.keys(), key=len, reverse=True)
        else:
            # Legacy path — resolve by current login
            all_mentions = MentionService.parse_all_mentions(comment_text)
            if all_mentions["users"]:
                user_ids = MentionService.resolve_user_mentions(all_mentions["users"], organization_id)
                users = db.session.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
                user_map = {u.login: u for u in users}
            else:
                user_map = {}
            usernames_to_render = sorted(all_mentions.get("users", []), key=len, reverse=True)

        for username in usernames_to_render:
            user = user_map.get(username)
            if user:
                pattern = f"@{username}"
                if pattern in result and "badge bg-info" not in result.split(pattern)[0][-50:]:
                    replacement = f'<span class="mention" data-user-id="{user.id}">@{user.display_name}</span>'
                    result = result.replace(pattern, replacement, 1)

        return result
