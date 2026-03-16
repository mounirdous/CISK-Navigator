"""
Search Service

Advanced search functionality with fuzzy matching, query parsing, and multi-entity search.
"""

import re

from Levenshtein import ratio

from app.extensions import db
from app.models import KPI, Challenge, Initiative, InitiativeSystemLink, Space, System


class SearchService:
    """
    Service for advanced search across CISK Navigator entities.

    Features:
    - Fuzzy text matching (typo-tolerant)
    - Query parsing (operators: >, <, =, ranges, dates)
    - Multi-entity search (KPIs, Systems, Initiatives, Challenges, Spaces)
    - Advanced filtering (status, dates, geography, governance)
    """

    # Fuzzy match threshold (0.0 to 1.0, higher = stricter)
    FUZZY_THRESHOLD = 0.6

    # Search modifiers
    MODIFIER_AT_RISK = "@risk"
    MODIFIER_INCOMPLETE = "@incomplete"
    MODIFIER_NO_CONSENSUS = "@no_consensus"
    MODIFIER_ARCHIVED = "@archived"

    @staticmethod
    def search_all(query, filters=None, organization_id=None):
        """
        Main search entry point - searches across all entity types.

        Args:
            query (str): Search query text
            filters (dict): Optional filters (entity_types, date_range, status, etc.)
            organization_id (int): Organization ID to scope search

        Returns:
            dict: Categorized search results
                {
                    "kpis": [...],
                    "systems": [...],
                    "initiatives": [...],
                    "challenges": [...],
                    "spaces": [...],
                    "query_info": {...}
                }
        """
        if not query or not organization_id:
            return SearchService._empty_results()

        # Parse query for operators and modifiers
        parsed = SearchService.parse_query(query)

        # Default filters if none provided
        if filters is None:
            filters = {}

        # Determine which entity types to search
        entity_types = filters.get("entity_types", ["kpis", "systems", "initiatives", "challenges", "spaces"])

        results = {
            "kpis": [],
            "systems": [],
            "initiatives": [],
            "challenges": [],
            "spaces": [],
            "query_info": {
                "original_query": query,
                "parsed_query": parsed["clean_query"],
                "modifiers": parsed["modifiers"],
                "operators": parsed["operators"],
            },
        }

        # Search each entity type
        if "kpis" in entity_types:
            results["kpis"] = SearchService.search_kpis(parsed, filters, organization_id)

        if "systems" in entity_types:
            results["systems"] = SearchService.search_systems(parsed, filters, organization_id)

        if "initiatives" in entity_types:
            results["initiatives"] = SearchService.search_initiatives(parsed, filters, organization_id)

        if "challenges" in entity_types:
            results["challenges"] = SearchService.search_challenges(parsed, filters, organization_id)

        if "spaces" in entity_types:
            results["spaces"] = SearchService.search_spaces(parsed, filters, organization_id)

        return results

    @staticmethod
    def parse_query(query):
        """
        Parse search query for operators, modifiers, and clean text.

        Supports:
        - Modifiers: @risk, @incomplete, @no_consensus, @archived
        - Date operators: updated:last_week, updated:last_month, updated:today
        - Numeric operators: value>100, value<50, value=25
        - Ranges: value:10-20

        Args:
            query (str): Raw query string

        Returns:
            dict: Parsed query components
        """
        result = {
            "clean_query": query,
            "modifiers": [],
            "operators": {},
            "date_filters": {},
        }

        # Extract modifiers (@risk, @incomplete, etc.)
        modifiers = re.findall(r"@(\w+)", query)
        result["modifiers"] = modifiers

        # Remove modifiers from query
        clean_query = re.sub(r"@\w+", "", query).strip()

        # Extract date filters (updated:last_week, etc.)
        date_matches = re.findall(r"updated:(\w+)", clean_query)
        if date_matches:
            result["date_filters"]["updated"] = date_matches[0]
            clean_query = re.sub(r"updated:\w+", "", clean_query).strip()

        # Extract numeric operators (value>100, value<50, etc.)
        value_ops = re.findall(r"value([><=]+)([\d.]+)", clean_query)
        if value_ops:
            for op, val in value_ops:
                result["operators"]["value"] = {"op": op, "value": float(val)}
            clean_query = re.sub(r"value[><=]+[\d.]+", "", clean_query).strip()

        # Extract ranges (value:10-20)
        range_match = re.search(r"value:([\d.]+)-([\d.]+)", clean_query)
        if range_match:
            result["operators"]["value_range"] = {
                "min": float(range_match.group(1)),
                "max": float(range_match.group(2)),
            }
            clean_query = re.sub(r"value:[\d.]+-[\d.]+", "", clean_query).strip()

        result["clean_query"] = clean_query

        return result

    @staticmethod
    def fuzzy_match(text, query, threshold=None):
        """
        Perform fuzzy string matching using Levenshtein distance.

        Args:
            text (str): Text to search in
            query (str): Query to match
            threshold (float): Similarity threshold (0.0-1.0)

        Returns:
            bool: True if match exceeds threshold
        """
        if not text or not query:
            return False

        if threshold is None:
            threshold = SearchService.FUZZY_THRESHOLD

        # Convert to lowercase for comparison
        text = text.lower()
        query = query.lower()

        # Exact substring match always passes
        if query in text:
            return True

        # Calculate similarity ratio
        similarity = ratio(text, query)

        return similarity >= threshold

    @staticmethod
    def search_kpis(parsed, filters, organization_id):
        """
        Search KPIs by name, description, and associated entities.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching KPI records with context
        """
        query = parsed["clean_query"]
        modifiers = parsed["modifiers"]

        # Base query - join through the relationship chain
        base_query = (
            db.session.query(KPI)
            .join(KPI.initiative_system_link)
            .join(InitiativeSystemLink.initiative)
            .filter(Initiative.organization_id == organization_id)
        )

        # Apply modifiers
        if "archived" not in modifiers:
            base_query = base_query.filter(KPI.is_archived is False)
        else:
            base_query = base_query.filter(KPI.is_archived is True)

        # Get all KPIs
        all_kpis = base_query.all()

        # Filter by fuzzy match
        results = []
        for kpi in all_kpis:
            match_score = 0

            # Check name
            if SearchService.fuzzy_match(kpi.name, query):
                match_score += 2

            # Check description
            if kpi.description and SearchService.fuzzy_match(kpi.description, query):
                match_score += 1

            # Check system name
            if kpi.initiative_system_link and kpi.initiative_system_link.system:
                system_name = kpi.initiative_system_link.system.name
                if SearchService.fuzzy_match(system_name, query):
                    match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": kpi.id,
                        "name": kpi.name,
                        "description": kpi.description,
                        "system_name": (
                            kpi.initiative_system_link.system.name
                            if kpi.initiative_system_link and kpi.initiative_system_link.system
                            else None
                        ),
                        "initiative_name": (
                            kpi.initiative_system_link.initiative.name
                            if kpi.initiative_system_link and kpi.initiative_system_link.initiative
                            else None
                        ),
                        "match_score": match_score,
                        "is_archived": kpi.is_archived,
                        "updated_at": kpi.updated_at.isoformat() if kpi.updated_at else None,
                    }
                )

        # Sort by match score
        results.sort(key=lambda x: x["match_score"], reverse=True)

        return results

    @staticmethod
    def search_systems(parsed, filters, organization_id):
        """
        Search Systems by name and description.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching System records
        """
        query = parsed["clean_query"]

        # Base query
        base_query = (
            db.session.query(System)
            .join(System.initiative_links)
            .join(InitiativeSystemLink.initiative)
            .filter(Initiative.organization_id == organization_id)
            .distinct()
        )

        # Note: System model doesn't have is_archived field
        # Systems are always active

        all_systems = base_query.all()

        # Filter by fuzzy match
        results = []
        for system in all_systems:
            match_score = 0

            if SearchService.fuzzy_match(system.name, query):
                match_score += 2

            if system.description and SearchService.fuzzy_match(system.description, query):
                match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": system.id,
                        "name": system.name,
                        "description": system.description,
                        "match_score": match_score,
                        "updated_at": system.updated_at.isoformat() if system.updated_at else None,
                    }
                )

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    @staticmethod
    def search_initiatives(parsed, filters, organization_id):
        """
        Search Initiatives by name and description.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching Initiative records
        """
        query = parsed["clean_query"]
        modifiers = parsed["modifiers"]

        # Base query
        base_query = db.session.query(Initiative).filter(Initiative.organization_id == organization_id)

        # Note: Initiative model doesn't have is_archived field

        # Apply modifiers
        if "no_consensus" in modifiers:
            base_query = base_query.filter(Initiative.impact_on_challenge == "no_consensus")

        all_initiatives = base_query.all()

        # Filter by fuzzy match
        results = []
        for initiative in all_initiatives:
            match_score = 0

            if SearchService.fuzzy_match(initiative.name, query):
                match_score += 2

            if initiative.description and SearchService.fuzzy_match(initiative.description, query):
                match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": initiative.id,
                        "name": initiative.name,
                        "description": initiative.description,
                        "impact_on_challenge": initiative.impact_on_challenge,
                        "match_score": match_score,
                        "updated_at": initiative.updated_at.isoformat() if initiative.updated_at else None,
                    }
                )

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    @staticmethod
    def search_challenges(parsed, filters, organization_id):
        """
        Search Challenges by name and description.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching Challenge records
        """
        query = parsed["clean_query"]

        # Get all challenges for organization
        # Note: Challenge model doesn't have is_archived field
        all_challenges = (
            db.session.query(Challenge).join(Challenge.space).filter(Space.organization_id == organization_id).all()
        )

        # Filter by fuzzy match
        results = []
        for challenge in all_challenges:
            match_score = 0

            if SearchService.fuzzy_match(challenge.name, query):
                match_score += 2

            if challenge.description and SearchService.fuzzy_match(challenge.description, query):
                match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": challenge.id,
                        "name": challenge.name,
                        "description": challenge.description,
                        "space_name": challenge.space.name if challenge.space else None,
                        "match_score": match_score,
                        "updated_at": challenge.updated_at.isoformat() if challenge.updated_at else None,
                    }
                )

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    @staticmethod
    def search_spaces(parsed, filters, organization_id):
        """
        Search Spaces by name and description.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching Space records
        """
        query = parsed["clean_query"]

        # Get all spaces for organization
        # Note: Space model doesn't have is_archived field
        all_spaces = db.session.query(Space).filter(Space.organization_id == organization_id).all()

        # Filter by fuzzy match
        results = []
        for space in all_spaces:
            match_score = 0

            if SearchService.fuzzy_match(space.name, query):
                match_score += 2

            if space.description and SearchService.fuzzy_match(space.description, query):
                match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": space.id,
                        "name": space.name,
                        "description": space.description,
                        "match_score": match_score,
                        "updated_at": space.updated_at.isoformat() if space.updated_at else None,
                    }
                )

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    @staticmethod
    def _empty_results():
        """Return empty search results structure."""
        return {
            "kpis": [],
            "systems": [],
            "initiatives": [],
            "challenges": [],
            "spaces": [],
            "query_info": {"original_query": "", "parsed_query": "", "modifiers": [], "operators": {}},
        }
