"""
Service for managing action items and memos
"""

from datetime import datetime

from flask import url_for
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import ActionItem, ActionItemMention, User
from app.services.email_service import EmailService
from app.services.mention_service import MentionService


class ActionItemService:
    """Service for action item and memo operations"""

    @staticmethod
    def get_items_for_user(
        user, organization_id, item_type=None, status=None, statuses=None, visibility_filter="all", governance_body_ids=None
    ):
        """
        Get action items/memos for a user in an organization

        Args:
            user: User object
            organization_id: Organization ID
            item_type: Filter by type ('memo', 'action', or None for all)
            statuses: List of statuses to filter by (None = no filter)
            visibility_filter: 'my_items', 'team_items', or 'all'
            governance_body_ids: List of GB IDs to filter by (None = no filter)

        Returns:
            List of ActionItem objects
        """
        from app.models.action_item import action_item_governance_body

        query = ActionItem.query.filter_by(organization_id=organization_id).options(joinedload(ActionItem.mentions))

        # Apply type filter
        if item_type:
            query = query.filter_by(type=item_type)

        # Apply status filter (multi-select list or legacy single value)
        effective_statuses = statuses or ([status] if status else None)
        if effective_statuses:
            query = query.filter(ActionItem.status.in_(effective_statuses))

        # Apply visibility filter
        if visibility_filter == "my_items":
            query = query.filter(ActionItem.owner_user_id == user.id)
        elif visibility_filter == "team_items":
            query = query.filter_by(visibility="shared")
        elif visibility_filter == "all":
            query = query.filter(
                or_(
                    and_(ActionItem.visibility == "private", ActionItem.owner_user_id == user.id),
                    ActionItem.visibility == "shared",
                )
            )

        # Apply governance body filter
        if governance_body_ids:
            query = query.join(
                action_item_governance_body,
                ActionItem.id == action_item_governance_body.c.action_item_id,
            ).filter(action_item_governance_body.c.governance_body_id.in_(governance_body_ids))

        return query.order_by(ActionItem.created_at.desc()).all()

    @staticmethod
    def create_item(
        organization_id, owner_user_id, created_by_user_id, title, description, item_type="action", **kwargs
    ):
        """
        Create a new action item or memo

        Args:
            organization_id: Organization ID
            owner_user_id: Owner user ID
            created_by_user_id: Creator user ID
            title: Item title
            description: Item description
            item_type: 'memo' or 'action'
            **kwargs: Additional fields (status, priority, due_date, visibility)

        Returns:
            ActionItem object
        """
        item = ActionItem(
            organization_id=organization_id,
            owner_user_id=owner_user_id,
            created_by_user_id=created_by_user_id,
            title=title,
            description=description,
            type=item_type,
        )

        # Set optional fields
        if "status" in kwargs:
            item.status = kwargs["status"]
        if "priority" in kwargs:
            item.priority = kwargs["priority"]
        if "due_date" in kwargs:
            item.due_date = kwargs["due_date"]
        if "visibility" in kwargs:
            item.visibility = kwargs["visibility"]

        db.session.add(item)
        db.session.flush()  # Get the ID

        # Attach governance bodies
        if kwargs.get("governance_body_ids"):
            from app.models import GovernanceBody
            gbs = GovernanceBody.query.filter(GovernanceBody.id.in_(kwargs["governance_body_ids"])).all()
            item.governance_bodies = gbs

        # Parse and create mentions
        if description:
            ActionItemService._parse_and_create_mentions(item.id, description, organization_id)

        db.session.commit()

        # Send email notification if assigning to someone else
        if owner_user_id != created_by_user_id:
            owner_user = User.query.get(owner_user_id)
            if owner_user and owner_user.email:
                try:
                    # Build action item URL
                    try:
                        action_url = url_for("action_items.index", _anchor=f"item-{item.id}", _external=True)
                    except RuntimeError:
                        # If not in request context, use relative URL
                        action_url = f"/actions#item-{item.id}"

                    # Format due date
                    due_date_str = item.due_date.strftime("%Y-%m-%d") if item.due_date else "No due date"

                    EmailService.send_action_item_assigned(
                        user_email=owner_user.email,
                        user_name=owner_user.display_name or owner_user.login,
                        action_title=title,
                        action_description=description or "",
                        due_date=due_date_str,
                        action_url=action_url,
                    )
                except Exception as e:
                    # Log error but don't fail the action creation
                    print(f"Failed to send action item email to {owner_user.email}: {e}")

        return item

    @staticmethod
    def update_item(item_id, user_id, **kwargs):
        """
        Update an action item

        Args:
            item_id: ActionItem ID
            user_id: User performing the update (must be owner)
            **kwargs: Fields to update

        Returns:
            Updated ActionItem object or None if not found/unauthorized
        """
        item = ActionItem.query.get(item_id)
        if not item or item.owner_user_id != user_id:
            return None

        # Track if owner changed for notification
        old_owner_id = item.owner_user_id
        new_owner_id = kwargs.get("owner_user_id")
        owner_changed = new_owner_id and new_owner_id != old_owner_id

        # Update fields (only if value is not None, or if it's an explicitly nullable field)
        for field in ["title", "description", "visibility", "owner_user_id"]:
            if field in kwargs and kwargs[field] is not None:
                setattr(item, field, kwargs[field])

        # For actions only: update status, priority, due_date
        if item.type == "action":
            for field in ["status", "priority", "due_date"]:
                if field in kwargs and kwargs[field] is not None:
                    setattr(item, field, kwargs[field])

        # Mark as completed if status changed to completed
        if "status" in kwargs and kwargs["status"] == "completed" and item.completed_at is None:
            item.completed_at = datetime.utcnow()

        # Update governance bodies if provided (empty list = clear all)
        if "governance_body_ids" in kwargs:
            from app.models import GovernanceBody
            gb_ids = kwargs["governance_body_ids"] or []
            item.governance_bodies = GovernanceBody.query.filter(GovernanceBody.id.in_(gb_ids)).all() if gb_ids else []

        # Update mentions if description changed
        if "description" in kwargs:
            # Delete old mentions
            ActionItemMention.query.filter_by(action_item_id=item.id).delete()
            # Create new mentions
            ActionItemService._parse_and_create_mentions(item.id, kwargs["description"], item.organization_id)

        item.updated_at = datetime.utcnow()
        db.session.commit()

        # Send email notification if owner changed
        if owner_changed:
            new_owner = User.query.get(new_owner_id)
            if new_owner and new_owner.email:
                try:
                    # Build action item URL
                    try:
                        action_url = url_for("action_items.index", _anchor=f"item-{item.id}", _external=True)
                    except RuntimeError:
                        action_url = f"/actions#item-{item.id}"

                    due_date_str = item.due_date.strftime("%Y-%m-%d") if item.due_date else "No due date"

                    EmailService.send_action_item_assigned(
                        user_email=new_owner.email,
                        user_name=new_owner.display_name or new_owner.login,
                        action_title=item.title,
                        action_description=item.description or "",
                        due_date=due_date_str,
                        action_url=action_url,
                    )
                except Exception as e:
                    print(f"Failed to send action item email to {new_owner.email}: {e}")

        return item

    @staticmethod
    def delete_item(item_id, user_id, is_admin=False):
        """
        Delete an action item

        Args:
            item_id: ActionItem ID
            user_id: User performing the deletion (must be owner or admin)
            is_admin: If True, bypass owner check (for admins)

        Returns:
            True if deleted, False if not found/unauthorized
        """
        item = ActionItem.query.get(item_id)
        if not item:
            return False

        # Allow if user is owner OR if they're an admin
        if not is_admin and item.owner_user_id != user_id:
            return False

        db.session.delete(item)
        db.session.commit()
        return True

    @staticmethod
    def bulk_delete_items(item_ids, user_id, is_admin=False):
        """
        Delete multiple action items

        Args:
            item_ids: List of ActionItem IDs
            user_id: User performing the deletion
            is_admin: If True, bypass owner check (for admins)

        Returns:
            Number of items deleted
        """
        deleted_count = 0
        for item_id in item_ids:
            if ActionItemService.delete_item(item_id, user_id, is_admin):
                deleted_count += 1
        return deleted_count

    @staticmethod
    def get_stats_for_user(user, organization_id):
        """
        Get statistics for a user's action items

        Returns:
            Dictionary with counts
        """
        my_items = ActionItem.query.filter_by(organization_id=organization_id, owner_user_id=user.id)

        return {
            "total_memos": my_items.filter_by(type="memo").count(),
            "total_actions": my_items.filter_by(type="action").count(),
            "open_actions": my_items.filter_by(type="action", status="active").count(),
            "overdue_actions": sum(1 for item in my_items.filter_by(type="action", status="active") if item.is_overdue),
            "completed_actions": my_items.filter_by(type="action", status="completed").count(),
        }

    @staticmethod
    def _parse_and_create_mentions(action_item_id, description, organization_id):
        """
        Parse description for @mentions and create ActionItemMention records

        Uses shared MentionService for parsing and resolving entities.

        Args:
            action_item_id: ActionItem ID
            description: Text to parse
            organization_id: Organization ID for entity lookup
        """
        if not description:
            return

        # Parse entity mentions using shared service
        all_mentions = MentionService.parse_all_mentions(description)

        # We only care about entity mentions (not user mentions) for action items
        if not all_mentions["entities"]:
            return

        # Resolve entity mentions
        entity_mentions = MentionService.resolve_entity_mentions(all_mentions["entities"], organization_id)

        # Create ActionItemMention records
        for entity_type, entity_id, mention_text in entity_mentions:
            mention = ActionItemMention(
                action_item_id=action_item_id,
                entity_type=entity_type,
                entity_id=entity_id,
                mention_text=mention_text,
            )
            db.session.add(mention)

    @staticmethod
    def search_entities_for_mention(search_query, organization_id, limit=10):
        """
        Search for entities to mention (for autocomplete)

        Delegates to shared MentionService.

        Returns:
            List of dictionaries with entity info
        """
        return MentionService.search_entities(search_query, organization_id, limit)
