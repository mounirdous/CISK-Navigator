"""
Test Mention Service for parsing and resolving @mentions
"""

import pytest

from app.models import KPI, Challenge, Initiative, InitiativeSystemLink, Space, System
from app.services.mention_service import MentionService


class TestMentionService:
    """Test mention parsing and entity resolution"""

    @pytest.fixture
    def test_entities(self, db, sample_organization):
        """Create test entities for mention resolution"""
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
        db.session.commit()

        return {
            "space": space,
            "challenge": challenge,
            "initiative": initiative,
            "system": system,
            "kpi": kpi,
        }

    def test_parse_user_mentions(self, app):
        """Test parsing @user mentions from text"""
        with app.app_context():
            text = "Hey @john.doe, can you check with @jane-smith about this?"

            result = MentionService.parse_all_mentions(text)

            assert "users" in result
            assert len(result["users"]) == 2
            assert "john.doe" in result["users"]
            assert "jane-smith" in result["users"]

    def test_parse_entity_mentions(self, app):
        """Test parsing entity mentions from text"""
        with app.app_context():
            text = 'This relates to @"Revenue Growth" and @"Digital Transformation"'

            result = MentionService.parse_all_mentions(text)

            assert "entities" in result
            assert len(result["entities"]) == 2
            # Entities are returned as name strings
            assert "Revenue Growth" in result["entities"]
            assert "Digital Transformation" in result["entities"]

    def test_parse_mixed_mentions(self, app):
        """Test parsing both user and entity mentions"""
        with app.app_context():
            text = 'Hey @john please check @"Customer Satisfaction" and @"CRM System" with @jane'

            result = MentionService.parse_all_mentions(text)

            assert len(result["users"]) == 2
            assert len(result["entities"]) == 2

    def test_parse_no_mentions(self, app):
        """Test text with no mentions"""
        with app.app_context():
            text = "This is just regular text without any mentions"

            result = MentionService.parse_all_mentions(text)

            assert len(result["users"]) == 0
            assert len(result["entities"]) == 0

    def test_resolve_challenge_mention(self, app, db, sample_organization, test_entities):
        """Test resolving challenge mention to entity ID"""
        with app.app_context():
            # Create mention list (entity names)
            mentions = ["Test Challenge"]

            resolved = MentionService.resolve_entity_mentions(mentions, sample_organization.id)

            assert len(resolved) == 1
            entity_type, entity_id, mention_text = resolved[0]
            assert entity_type == "challenge"
            assert entity_id == test_entities["challenge"].id

    def test_resolve_initiative_mention(self, app, db, sample_organization, test_entities):
        """Test resolving initiative mention"""
        with app.app_context():
            mentions = ["Test Initiative"]

            resolved = MentionService.resolve_entity_mentions(mentions, sample_organization.id)

            assert len(resolved) == 1
            entity_type, entity_id, mention_text = resolved[0]
            assert entity_type == "initiative"
            assert entity_id == test_entities["initiative"].id

    def test_resolve_system_mention(self, app, db, sample_organization, test_entities):
        """Test resolving system mention"""
        with app.app_context():
            mentions = ["Test System"]

            resolved = MentionService.resolve_entity_mentions(mentions, sample_organization.id)

            assert len(resolved) == 1
            entity_type, entity_id, mention_text = resolved[0]
            assert entity_type == "system"
            assert entity_id == test_entities["system"].id

    def test_resolve_kpi_mention(self, app, db, sample_organization, test_entities):
        """Test resolving KPI mention"""
        with app.app_context():
            mentions = ["Test KPI"]

            resolved = MentionService.resolve_entity_mentions(mentions, sample_organization.id)

            assert len(resolved) == 1
            entity_type, entity_id, mention_text = resolved[0]
            assert entity_type == "kpi"
            assert entity_id == test_entities["kpi"].id

    def test_resolve_nonexistent_entity(self, app, db, sample_organization):
        """Test resolving mention for entity that doesn't exist"""
        with app.app_context():
            mentions = ["Nonexistent Challenge"]

            resolved = MentionService.resolve_entity_mentions(mentions, sample_organization.id)

            # Should return empty list if entity not found
            assert len(resolved) == 0

    def test_resolve_multiple_entities(self, app, db, sample_organization, test_entities):
        """Test resolving multiple entity mentions"""
        with app.app_context():
            mentions = ["Test Challenge", "Test Initiative", "Test System"]

            resolved = MentionService.resolve_entity_mentions(mentions, sample_organization.id)

            assert len(resolved) == 3
            entity_types = [e[0] for e in resolved]
            assert "challenge" in entity_types
            assert "initiative" in entity_types
            assert "system" in entity_types

    def test_search_entities_for_autocomplete(self, app, db, sample_organization, test_entities):
        """Test searching entities for autocomplete suggestions"""
        with app.app_context():
            # Search for "test"
            results = MentionService.search_entities("test", sample_organization.id, limit=10)

            # Should return entities with "test" in name
            assert len(results) > 0

            # Check structure of results
            if results:
                first_result = results[0]
                assert "type" in first_result
                assert "id" in first_result
                assert "name" in first_result
                assert "label" in first_result

    def test_search_entities_case_insensitive(self, app, db, sample_organization, test_entities):
        """Test that entity search is case-insensitive"""
        with app.app_context():
            # Search with different cases
            results_lower = MentionService.search_entities("test", sample_organization.id)
            results_upper = MentionService.search_entities("TEST", sample_organization.id)
            results_mixed = MentionService.search_entities("TeSt", sample_organization.id)

            # Should return same number of results regardless of case
            assert len(results_lower) == len(results_upper)
            assert len(results_lower) == len(results_mixed)

    def test_search_entities_with_limit(self, app, db, sample_organization, test_entities):
        """Test entity search respects limit parameter"""
        with app.app_context():
            # Search with limit
            results = MentionService.search_entities("test", sample_organization.id, limit=2)

            # Should return at most 2 results
            assert len(results) <= 2

    def test_search_entities_no_results(self, app, db, sample_organization):
        """Test entity search with no matches"""
        with app.app_context():
            results = MentionService.search_entities("nonexistentquery12345", sample_organization.id)

            assert len(results) == 0
