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
    MODIFIER_INCOMPLETE = "@incomplete"
    MODIFIER_NO_CONSENSUS = "@no_consensus"
    MODIFIER_ARCHIVED = "@archived"
    MODIFIER_MISSING_KPIS = "@missing_kpis"
    MODIFIER_MISSING_GOVERNANCE = "@missing_governance"
    MODIFIER_REQUIRES_ACTION = "@requires_action"

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

        # For @requires_action, only search entity types with action items
        modifiers = parsed["modifiers"]
        if "requires_action" in modifiers:
            # Only search entities that have action item criteria
            entity_types = ["kpis", "systems", "initiatives", "spaces"]
        else:
            # Determine which entity types to search
            entity_types = filters.get(
                "entity_types", ["kpis", "systems", "initiatives", "challenges", "spaces", "value_types", "comments"]
            )

        results = {
            "kpis": [],
            "systems": [],
            "initiatives": [],
            "challenges": [],
            "spaces": [],
            "value_types": [],
            "comments": [],
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

        if "value_types" in entity_types:
            results["value_types"] = SearchService.search_value_types(parsed, filters, organization_id)

        if "comments" in entity_types:
            results["comments"] = SearchService.search_comments(parsed, filters, organization_id)

        return results

    @staticmethod
    def parse_query(query):
        """
        Parse search query for operators, modifiers, and clean text.

        Supports:
        - Modifiers: @incomplete, @no_consensus, @archived, @missing_kpis, @missing_governance, @requires_action
        - @requires_action: Special umbrella modifier that uses OR logic (not expanded to individual modifiers)
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

        # Extract modifiers (@incomplete, @no_consensus, @archived)
        modifiers = re.findall(r"@(\w+)", query)

        # Note: @requires_action is NOT expanded here - it's handled specially in search functions
        # to use OR logic instead of AND logic

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

        # Check if query matches any individual word (for multi-word text)
        # This allows "inventroy" to match "Inventory turns improvement"
        words = text.split()
        for word in words:
            word_similarity = ratio(word, query)
            if word_similarity >= threshold:
                return True

        # Fall back to comparing entire text (for short phrases)
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
            base_query = base_query.filter(KPI.is_archived == False)  # noqa: E712
        else:
            base_query = base_query.filter(KPI.is_archived == True)  # noqa: E712

        # Get all KPIs
        all_kpis = base_query.all()

        # Filter by fuzzy match
        results = []
        for kpi in all_kpis:
            # Check @missing_governance or @requires_action modifier
            if "missing_governance" in modifiers or "requires_action" in modifiers:
                # Check if KPI has governance bodies
                from app.models import KPIGovernanceBodyLink

                has_governance = (
                    db.session.query(KPIGovernanceBodyLink).filter(KPIGovernanceBodyLink.kpi_id == kpi.id).count() > 0
                )
                if has_governance:
                    continue  # Skip KPIs that have governance bodies

            # Fuzzy match logic
            match_score = 0
            if query:  # If there's a text query, check fuzzy match
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

                # Skip if no fuzzy match
                if match_score == 0:
                    continue
            else:
                # Modifier-only search - include all that passed modifier filters
                match_score = 1

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
        modifiers = parsed["modifiers"]

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
            # Check @missing_kpis or @requires_action modifier
            if "missing_kpis" in modifiers or "requires_action" in modifiers:
                # Check if system has any KPIs
                has_kpis = (
                    db.session.query(KPI)
                    .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
                    .filter(InitiativeSystemLink.system_id == system.id)
                    .count()
                    > 0
                )
                if has_kpis:
                    continue  # Skip systems that have KPIs

            # Fuzzy match logic
            match_score = 0
            if query:  # If there's a text query, check fuzzy match
                if SearchService.fuzzy_match(system.name, query):
                    match_score += 2

                if system.description and SearchService.fuzzy_match(system.description, query):
                    match_score += 1

                # Skip if no fuzzy match
                if match_score == 0:
                    continue
            else:
                # Modifier-only search - include all systems that passed filters
                match_score = 1

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

        # Base query - get ALL initiatives first
        all_initiatives = db.session.query(Initiative).filter(Initiative.organization_id == organization_id).all()

        # Filter by fuzzy match and modifiers
        results = []
        for initiative in all_initiatives:
            # Handle @requires_action with OR logic
            if "requires_action" in modifiers:
                # Include if: no_consensus OR incomplete
                is_no_consensus = initiative.impact_on_challenge == "no_consensus"
                filled, total, status = initiative.get_form_completion()
                is_incomplete = status != "complete"

                if not (is_no_consensus or is_incomplete):
                    continue  # Skip initiatives that don't match any action item criteria

            # Handle individual modifiers with AND logic (more specific)
            else:
                # Check no_consensus modifier
                if "no_consensus" in modifiers:
                    if initiative.impact_on_challenge != "no_consensus":
                        continue

                # Check incomplete modifier
                if "incomplete" in modifiers:
                    filled, total, status = initiative.get_form_completion()
                    if status == "complete":
                        continue  # Skip complete initiatives

            # Fuzzy match logic
            match_score = 0
            if query:  # If there's a text query, check fuzzy match
                if SearchService.fuzzy_match(initiative.name, query):
                    match_score += 2

                if initiative.description and SearchService.fuzzy_match(initiative.description, query):
                    match_score += 1

                # Skip if no fuzzy match
                if match_score == 0:
                    continue
            else:
                # Modifier-only search (no text query) - include all that passed modifier filters
                match_score = 1

            # Include in results
            result_dict = {
                "id": initiative.id,
                "name": initiative.name,
                "description": initiative.description,
                "impact_on_challenge": initiative.impact_on_challenge,
                "match_score": match_score,
                "updated_at": initiative.updated_at.isoformat() if initiative.updated_at else None,
            }

            # Add completion info if @incomplete modifier
            if "incomplete" in modifiers:
                filled, total, status = initiative.get_form_completion()
                result_dict["completion_status"] = f"{filled}/{total} fields"
                result_dict["completion_percent"] = int((filled / total) * 100) if total > 0 else 0

            results.append(result_dict)

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
            # Fuzzy match logic
            match_score = 0
            if query:  # If there's a text query, check fuzzy match
                if SearchService.fuzzy_match(challenge.name, query):
                    match_score += 2

                if challenge.description and SearchService.fuzzy_match(challenge.description, query):
                    match_score += 1

                # Skip if no fuzzy match
                if match_score == 0:
                    continue
            else:
                # Modifier-only search - include all challenges
                match_score = 1

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
        modifiers = parsed["modifiers"]

        # Get all spaces for organization
        # Note: Space model doesn't have is_archived field
        all_spaces = db.session.query(Space).filter(Space.organization_id == organization_id).all()

        # Filter by modifiers and fuzzy match
        results = []
        for space in all_spaces:
            # Check incomplete modifier (spaces without complete SWOT)
            if "incomplete" in modifiers or "requires_action" in modifiers:
                filled, total, status = space.get_swot_completion()
                if status == "complete":
                    continue  # Skip complete spaces

            # Fuzzy match logic
            match_score = 0
            if query:  # If there's a text query, check fuzzy match
                if SearchService.fuzzy_match(space.name, query):
                    match_score += 2

                if space.description and SearchService.fuzzy_match(space.description, query):
                    match_score += 1

                # Skip if no fuzzy match
                if match_score == 0:
                    continue
            else:
                # Modifier-only search - include all that passed modifier filters
                match_score = 1

            # Include in results
            result_dict = {
                "id": space.id,
                "name": space.name,
                "description": space.description,
                "match_score": match_score,
                "updated_at": space.updated_at.isoformat() if space.updated_at else None,
            }

            # Add completion info if @incomplete modifier
            if "incomplete" in modifiers:
                filled, total, status = space.get_swot_completion()
                result_dict["completion_status"] = f"{filled}/{total} SWOT fields"
                result_dict["completion_percent"] = int((filled / total) * 100) if total > 0 else 0

            results.append(result_dict)

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    @staticmethod
    def search_value_types(parsed, filters, organization_id):
        """
        Search Value Types by name and unit label.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching ValueType records
        """
        from app.models import ValueType

        query = parsed["clean_query"]

        # Get all value types for organization
        all_value_types = db.session.query(ValueType).filter(ValueType.organization_id == organization_id).all()

        # Filter by fuzzy match
        results = []
        for value_type in all_value_types:
            # Fuzzy match logic
            match_score = 0
            if query:  # If there's a text query, check fuzzy match
                if SearchService.fuzzy_match(value_type.name, query):
                    match_score += 2

                if value_type.unit_label and SearchService.fuzzy_match(value_type.unit_label, query):
                    match_score += 1

                # Skip if no fuzzy match
                if match_score == 0:
                    continue
            else:
                # Modifier-only search - include all value types
                match_score = 1

            results.append(
                {
                    "id": value_type.id,
                    "name": value_type.name,
                    "unit_label": value_type.unit_label,
                    "kind": value_type.kind,
                    "match_score": match_score,
                    "updated_at": value_type.updated_at.isoformat() if value_type.updated_at else None,
                }
            )

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    @staticmethod
    def search_comments(parsed, filters, organization_id):
        """
        Search Comments by text content.

        Args:
            parsed (dict): Parsed query
            filters (dict): Additional filters
            organization_id (int): Organization ID

        Returns:
            list: Matching Comment records with context
        """
        from app.models import CellComment, Initiative, KPIValueTypeConfig

        query = parsed["clean_query"]

        # Only search if there's actual query text (comments need context)
        if not query or len(query) < 3:
            return []

        # Get comments for organization (via KPI -> Initiative -> Organization)
        all_comments = (
            db.session.query(CellComment)
            .join(KPIValueTypeConfig)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(InitiativeSystemLink)
            .join(Initiative)
            .filter(Initiative.organization_id == organization_id)
            .limit(100)  # Limit for performance
            .all()
        )

        # Filter by fuzzy match
        results = []
        for comment in all_comments:
            # Fuzzy match on comment text
            match_score = 0
            if SearchService.fuzzy_match(comment.comment_text, query):
                match_score += 1

            if match_score > 0:
                results.append(
                    {
                        "id": comment.id,
                        "text": comment.comment_text[:200] if comment.comment_text else "",
                        "user": comment.user.display_name if comment.user else "Unknown",
                        "kpi": comment.config.kpi.name if comment.config and comment.config.kpi else "Unknown",
                        "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M") if comment.created_at else "",
                        "match_score": match_score,
                    }
                )

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:50]  # Return top 50 comments

    @staticmethod
    def _empty_results():
        """Return empty search results structure."""
        return {
            "kpis": [],
            "systems": [],
            "initiatives": [],
            "challenges": [],
            "spaces": [],
            "value_types": [],
            "comments": [],
            "query_info": {"original_query": "", "parsed_query": "", "modifiers": [], "operators": {}},
        }
