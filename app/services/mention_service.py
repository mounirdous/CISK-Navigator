"""
Shared Mention Service

Handles @mentions for both users and entities across the application.
Used by Action Register, Comments, and other features.
"""

import re
from typing import Dict, List, Tuple

from app.extensions import db
from app.models import KPI, Challenge, Initiative, Space, System, User, UserOrganizationMembership


class MentionService:
    """Unified service for handling @mentions of users and entities"""

    # Mention patterns
    USER_MENTION_PATTERN = r"@([\w\.\-]+)"  # @username
    ENTITY_MENTION_PATTERN = r'@"([^"]+)"|@(\S+)'  # @"Entity Name" or @EntityName

    @staticmethod
    def parse_all_mentions(text: str) -> Dict[str, List[str]]:
        """
        Parse all mentions (users and entities) from text.

        Returns:
            Dictionary with 'users' and 'entities' lists
        """
        if not text:
            return {"users": [], "entities": []}

        # Parse user mentions (simple @username)
        user_mentions = re.findall(MentionService.USER_MENTION_PATTERN, text)

        # Parse entity mentions (@"Name" or @Name but exclude user mentions)
        entity_matches = re.finditer(MentionService.ENTITY_MENTION_PATTERN, text)
        entity_mentions = []

        for match in entity_matches:
            mention_text = match.group(1) or match.group(2)
            # If it looks like a quoted name or has spaces, treat as entity
            if match.group(1) or " " in mention_text:
                entity_mentions.append(mention_text)
            # If it's not a simple username, might be an entity
            elif mention_text not in user_mentions:
                entity_mentions.append(mention_text)

        return {
            "users": list(set(user_mentions)),  # Deduplicate
            "entities": list(set(entity_mentions)),  # Deduplicate
        }

    @staticmethod
    def resolve_user_mentions(usernames: List[str], organization_id: int) -> List[int]:
        """
        Convert usernames to user IDs within an organization.

        Args:
            usernames: List of usernames (without @)
            organization_id: Organization context

        Returns:
            List of user IDs
        """
        if not usernames:
            return []

        users = (
            db.session.query(User)
            .join(UserOrganizationMembership)
            .filter(User.login.in_(usernames), UserOrganizationMembership.organization_id == organization_id)
            .all()
        )

        return [user.id for user in users]

    @staticmethod
    def resolve_user_mentions_with_logins(usernames: List[str], organization_id: int) -> List[Tuple[str, int]]:
        """
        Convert usernames to (login, user_id) pairs within an organization.

        Returns tuples so callers can store the original login text alongside the
        stable user_id — enabling rename-safe rendering later.
        """
        if not usernames:
            return []

        users = (
            db.session.query(User)
            .join(UserOrganizationMembership)
            .filter(User.login.in_(usernames), UserOrganizationMembership.organization_id == organization_id)
            .all()
        )

        return [(user.login, user.id) for user in users]

    @staticmethod
    def resolve_entity_mentions(entity_names: List[str], organization_id: int) -> List[Tuple[str, int, str]]:
        """
        Find entities by name across spaces, challenges, initiatives, systems, KPIs.

        Args:
            entity_names: List of entity names to find
            organization_id: Organization context

        Returns:
            List of tuples: (entity_type, entity_id, matched_name)
        """
        if not entity_names:
            return []

        results = []

        for name in entity_names:
            name_lower = name.lower().strip()

            # Search spaces
            space = Space.query.filter(
                Space.organization_id == organization_id, db.func.lower(Space.name) == name_lower
            ).first()
            if space:
                results.append(("space", space.id, name))
                continue

            # Search challenges
            challenge = Challenge.query.filter(
                Challenge.organization_id == organization_id, db.func.lower(Challenge.name) == name_lower
            ).first()
            if challenge:
                results.append(("challenge", challenge.id, name))
                continue

            # Search initiatives
            initiative = Initiative.query.filter(
                Initiative.organization_id == organization_id, db.func.lower(Initiative.name) == name_lower
            ).first()
            if initiative:
                results.append(("initiative", initiative.id, name))
                continue

            # Search systems
            system = System.query.filter(
                System.organization_id == organization_id, db.func.lower(System.name) == name_lower
            ).first()
            if system:
                results.append(("system", system.id, name))
                continue

            # Search KPIs
            kpi = (
                KPI.query.join(KPI.initiative_system_link)
                .join(Initiative)
                .filter(Initiative.organization_id == organization_id, db.func.lower(KPI.name) == name_lower)
                .first()
            )
            if kpi:
                results.append(("kpi", kpi.id, name))
                continue

        return results

    @staticmethod
    def search_entities(query: str, organization_id: int, limit: int = 10) -> List[Dict]:
        """
        Search for entities to mention (for autocomplete).

        Returns list with entity info including type, id, name, label.
        """
        if not query or len(query) < 1:
            return []

        results = []
        search_pattern = f"%{query.lower()}%"

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

    @staticmethod
    def search_users(query: str, organization_id: int, limit: int = 10) -> List[Dict]:
        """
        Search for users to mention (for autocomplete).

        Returns list with user info including id, login, display_name, label.
        """
        if not query or len(query) < 1:
            return []

        search_pattern = f"%{query.lower()}%"

        users = (
            db.session.query(User)
            .join(UserOrganizationMembership)
            .filter(
                UserOrganizationMembership.organization_id == organization_id,
                User.is_active.is_(True),
                db.or_(
                    db.func.lower(User.login).like(search_pattern),
                    db.func.lower(User.display_name).like(search_pattern),
                ),
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "type": "user",
                "id": user.id,
                "login": user.login,
                "display_name": user.display_name or user.login,
                "label": f"@{user.login} ({user.display_name or user.login})",
            }
            for user in users
        ]

    @staticmethod
    def search_all(query: str, organization_id: int, limit: int = 10) -> Dict[str, List[Dict]]:
        """
        Search for both users and entities (for unified autocomplete).

        Returns:
            Dictionary with 'users' and 'entities' lists
        """
        half_limit = max(1, limit // 2)

        return {
            "users": MentionService.search_users(query, organization_id, half_limit),
            "entities": MentionService.search_entities(query, organization_id, half_limit),
        }

    @staticmethod
    def get_entity_url(entity_type: str, entity_id: int, comment_id: int = None) -> str:
        """
        Get URL for a mentioned entity.

        Args:
            entity_type: Type of entity (space, challenge, initiative, system, kpi)
            entity_id: ID of the entity
            comment_id: Optional comment ID for context tracking

        Returns:
            URL string to view the entity in workspace
        """
        from flask import url_for

        url_map = {
            "space": lambda: (
                url_for("workspace.index", from_comment=comment_id, _anchor=f"space-{entity_id}")
                if comment_id
                else url_for("workspace.index", _anchor=f"space-{entity_id}")
            ),
            "challenge": lambda: (
                url_for("workspace.index", from_comment=comment_id, _anchor=f"challenge-{entity_id}")
                if comment_id
                else url_for("workspace.index", _anchor=f"challenge-{entity_id}")
            ),
            "initiative": lambda: (
                url_for("workspace.index", from_comment=comment_id, _anchor=f"initiative-{entity_id}")
                if comment_id
                else url_for("workspace.index", _anchor=f"initiative-{entity_id}")
            ),
            "system": lambda: (
                url_for("workspace.index", from_comment=comment_id, _anchor=f"system-{entity_id}")
                if comment_id
                else url_for("workspace.index", _anchor=f"system-{entity_id}")
            ),
            "kpi": lambda: (
                url_for("workspace.index", from_comment=comment_id, _anchor=f"kpi-{entity_id}")
                if comment_id
                else url_for("workspace.index", _anchor=f"kpi-{entity_id}")
            ),
        }

        return url_map.get(entity_type, lambda: "#")()
