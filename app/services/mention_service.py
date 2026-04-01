"""
Shared Mention Service

Handles @mentions for both users and entities across the application.
Used by Action Register, Comments, and other features.
"""

import re
from typing import Dict, List, Tuple

from app.extensions import db
from app.models import KPI, Challenge, Initiative, Space, Stakeholder, System, User, UserOrganizationMembership


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

            # Search stakeholders
            stakeholder = Stakeholder.query.filter(
                Stakeholder.organization_id == organization_id, db.func.lower(Stakeholder.name) == name_lower
            ).first()
            if stakeholder:
                results.append(("stakeholder", stakeholder.id, name))
                continue

            # Try entity links by title, scoped to organization
            from app.models import EntityLink
            org_filter = MentionService._entity_link_org_filter(organization_id)
            link = EntityLink.query.filter(
                db.func.lower(EntityLink.title) == name_lower,
                EntityLink.is_public == True,
                org_filter,
            ).first()
            if link:
                results.append(("entity_link", link.id, link.title or link.url))
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

        # Search stakeholders
        stakeholders = Stakeholder.query.filter(
            Stakeholder.organization_id == organization_id, db.func.lower(Stakeholder.name).like(search_pattern)
        ).limit(limit)
        for stk in stakeholders:
            role_hint = f" — {stk.role}" if stk.role else ""
            results.append({"type": "stakeholder", "id": stk.id, "name": stk.name, "label": f"{stk.name}{role_hint} [Stakeholder]"})

        # Search entity links (by title or URL), scoped to organization
        from app.models import EntityLink
        org_filter = MentionService._entity_link_org_filter(organization_id)
        link_results = EntityLink.query.filter(
            db.or_(
                EntityLink.title.ilike(f"%{query}%"),
                EntityLink.url.ilike(f"%{query}%"),
            ),
            EntityLink.is_public == True,
            org_filter,
        ).limit(limit).all()
        for link in link_results:
            display_name = link.title or link.url
            type_info = link.get_type_info()
            url_hint = link.url[:60] + "..." if len(link.url) > 60 else link.url
            label = f"{link.title} ({url_hint})" if link.title else url_hint
            results.append({
                "type": "entity_link",
                "id": link.id,
                "name": display_name,
                "label": label,
                "bs_icon": type_info.get("bs_icon", "bi-link-45deg"),
                "icon_color": type_info.get("color", "#0ea5e9"),
                "url_hint": url_hint,
            })

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
            "stakeholder": lambda: url_for("stakeholders.edit", id=entity_id),
            "entity_link": lambda: MentionService._get_entity_link_url(entity_id),
        }

        return url_map.get(entity_type, lambda: "#")()

    @staticmethod
    def _entity_link_org_filter(organization_id):
        """Build a SQLAlchemy filter to scope EntityLink rows to an organization."""
        from app.models import EntityLink
        space_ids = db.session.query(Space.id).filter_by(organization_id=organization_id).subquery()
        challenge_ids = db.session.query(Challenge.id).filter_by(organization_id=organization_id).subquery()
        initiative_ids = db.session.query(Initiative.id).filter_by(organization_id=organization_id).subquery()
        system_ids = db.session.query(System.id).filter_by(organization_id=organization_id).subquery()
        kpi_ids = (
            db.session.query(KPI.id)
            .join(KPI.initiative_system_link)
            .join(Initiative)
            .filter(Initiative.organization_id == organization_id)
            .subquery()
        )
        return db.or_(
            db.and_(EntityLink.entity_type == "space", EntityLink.entity_id.in_(space_ids)),
            db.and_(EntityLink.entity_type == "challenge", EntityLink.entity_id.in_(challenge_ids)),
            db.and_(EntityLink.entity_type == "initiative", EntityLink.entity_id.in_(initiative_ids)),
            db.and_(EntityLink.entity_type == "system", EntityLink.entity_id.in_(system_ids)),
            db.and_(EntityLink.entity_type == "kpi", EntityLink.entity_id.in_(kpi_ids)),
            # action_item entity links belong to the action item, not a CISK entity
            EntityLink.entity_type == "action_item",
        )

    @staticmethod
    def _get_entity_link_url(entity_id):
        """Get the direct URL for an entity link"""
        from app.models import EntityLink
        link = EntityLink.query.get(entity_id)
        return link.url if link else "#"
