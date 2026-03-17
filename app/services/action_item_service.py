"""
Service for managing action items and memos
"""

import re
from datetime import datetime

from sqlalchemy import and_, or_

from app.extensions import db
from app.models import KPI, ActionItem, ActionItemMention, Challenge, Initiative, Space, System


class ActionItemService:
    """Service for action item and memo operations"""

    @staticmethod
    def get_items_for_user(user, organization_id, item_type=None, status=None, visibility_filter="all"):
        """
        Get action items/memos for a user in an organization

        Args:
            user: User object
            organization_id: Organization ID
            item_type: Filter by type ('memo', 'action', or None for all)
            status: Filter by status (for actions only)
            visibility_filter: 'my_items', 'team_items', or 'all'

        Returns:
            List of ActionItem objects
        """
        query = ActionItem.query.filter_by(organization_id=organization_id)

        # Apply type filter
        if item_type:
            query = query.filter_by(type=item_type)

        # Apply status filter (for actions)
        if status:
            query = query.filter_by(status=status)

        # Apply visibility filter
        if visibility_filter == "my_items":
            # Private items owned by user + shared items owned by user
            query = query.filter(ActionItem.owner_user_id == user.id)
        elif visibility_filter == "team_items":
            # All shared items
            query = query.filter_by(visibility="shared")
        elif visibility_filter == "all":
            # Private items owned by user + all shared items
            query = query.filter(
                or_(
                    and_(ActionItem.visibility == "private", ActionItem.owner_user_id == user.id),
                    ActionItem.visibility == "shared",
                )
            )

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

        # Parse and create mentions
        if description:
            ActionItemService._parse_and_create_mentions(item.id, description, organization_id)

        db.session.commit()
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

        # Update mentions if description changed
        if "description" in kwargs:
            # Delete old mentions
            ActionItemMention.query.filter_by(action_item_id=item.id).delete()
            # Create new mentions
            ActionItemService._parse_and_create_mentions(item.id, kwargs["description"], item.organization_id)

        item.updated_at = datetime.utcnow()
        db.session.commit()
        return item

    @staticmethod
    def delete_item(item_id, user_id):
        """
        Delete an action item

        Args:
            item_id: ActionItem ID
            user_id: User performing the deletion (must be owner)

        Returns:
            True if deleted, False if not found/unauthorized
        """
        item = ActionItem.query.get(item_id)
        if not item or item.owner_user_id != user_id:
            return False

        db.session.delete(item)
        db.session.commit()
        return True

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

        Supports patterns like:
        - @"Entity Name" or @EntityName
        - Searches across spaces, challenges, initiatives, systems, KPIs

        Args:
            action_item_id: ActionItem ID
            description: Text to parse
            organization_id: Organization ID for entity lookup
        """
        if not description:
            return

        # Pattern: @"Entity Name" or @EntityName (word characters only)
        mention_pattern = r'@"([^"]+)"|@(\S+)'
        matches = re.finditer(mention_pattern, description)

        for match in matches:
            mention_text = match.group(1) or match.group(2)

            # Try to find the entity
            entity = ActionItemService._find_entity(mention_text, organization_id)

            if entity:
                mention = ActionItemMention(
                    action_item_id=action_item_id,
                    entity_type=entity["type"],
                    entity_id=entity["id"],
                    mention_text=mention_text,
                )
                db.session.add(mention)

    @staticmethod
    def _find_entity(search_text, organization_id):
        """
        Find an entity by name across spaces, challenges, initiatives, systems, KPIs

        Returns:
            Dictionary with 'type' and 'id', or None if not found
        """
        search_text_lower = search_text.lower().strip()

        # Search spaces
        space = Space.query.filter(
            Space.organization_id == organization_id, db.func.lower(Space.name) == search_text_lower
        ).first()
        if space:
            return {"type": "space", "id": space.id}

        # Search challenges
        challenge = Challenge.query.filter(
            Challenge.organization_id == organization_id, db.func.lower(Challenge.name) == search_text_lower
        ).first()
        if challenge:
            return {"type": "challenge", "id": challenge.id}

        # Search initiatives
        initiative = Initiative.query.filter(
            Initiative.organization_id == organization_id, db.func.lower(Initiative.name) == search_text_lower
        ).first()
        if initiative:
            return {"type": "initiative", "id": initiative.id}

        # Search systems
        system = System.query.filter(
            System.organization_id == organization_id, db.func.lower(System.name) == search_text_lower
        ).first()
        if system:
            return {"type": "system", "id": system.id}

        # Search KPIs
        kpi = (
            KPI.query.join(KPI.initiative_system_link)
            .join(Initiative)
            .filter(Initiative.organization_id == organization_id, db.func.lower(KPI.name) == search_text_lower)
            .first()
        )
        if kpi:
            return {"type": "kpi", "id": kpi.id}

        return None

    @staticmethod
    def search_entities_for_mention(search_query, organization_id, limit=10):
        """
        Search for entities to mention (for autocomplete)

        Returns:
            List of dictionaries with entity info
        """
        if not search_query or len(search_query) < 2:
            return []

        results = []
        search_pattern = f"%{search_query.lower()}%"

        # Search spaces
        spaces = Space.query.filter(
            Space.organization_id == organization_id, db.func.lower(Space.name).like(search_pattern)
        ).limit(limit)
        for space in spaces:
            results.append({"type": "space", "id": space.id, "name": space.name, "label": f"{space.name} [Space]"})

        # Search challenges
        challenges = Challenge.query.filter(
            Challenge.organization_id == organization_id, db.func.lower(Challenge.name).like(search_pattern)
        ).limit(limit)
        for challenge in challenges:
            results.append(
                {
                    "type": "challenge",
                    "id": challenge.id,
                    "name": challenge.name,
                    "label": f"{challenge.name} [Challenge]",
                }
            )

        # Search initiatives
        initiatives = Initiative.query.filter(
            Initiative.organization_id == organization_id, db.func.lower(Initiative.name).like(search_pattern)
        ).limit(limit)
        for initiative in initiatives:
            results.append(
                {
                    "type": "initiative",
                    "id": initiative.id,
                    "name": initiative.name,
                    "label": f"{initiative.name} [Initiative]",
                }
            )

        # Search systems
        systems = System.query.filter(
            System.organization_id == organization_id, db.func.lower(System.name).like(search_pattern)
        ).limit(limit)
        for system in systems:
            results.append({"type": "system", "id": system.id, "name": system.name, "label": f"{system.name} [System]"})

        # Search KPIs
        kpis = (
            KPI.query.join(KPI.initiative_system_link)
            .join(Initiative)
            .filter(Initiative.organization_id == organization_id, db.func.lower(KPI.name).like(search_pattern))
            .limit(limit)
        )
        for kpi in kpis:
            results.append({"type": "kpi", "id": kpi.id, "name": kpi.name, "label": f"{kpi.name} [KPI]"})

        return results[:limit]
