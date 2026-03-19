"""
Test Search Service for global search functionality
"""

import pytest

from app.models import KPI, Challenge, Initiative, InitiativeSystemLink, Space, System
from app.services.search_service import SearchService


class TestSearchService:
    """Test search service operations"""

    @pytest.fixture
    def search_data(self, db, sample_organization):
        """Create test data for searching"""
        # Create spaces
        space1 = Space(organization_id=sample_organization.id, name="Finance Space", description="Financial reporting")
        space2 = Space(
            organization_id=sample_organization.id, name="Operations Space", description="Operational metrics"
        )
        db.session.add_all([space1, space2])
        db.session.flush()

        # Create challenges
        challenge1 = Challenge(
            organization_id=sample_organization.id,
            space_id=space1.id,
            name="Revenue Growth",
            description="Increase revenue by 20%",
        )
        challenge2 = Challenge(
            organization_id=sample_organization.id,
            space_id=space2.id,
            name="Cost Optimization",
            description="Reduce operational costs",
        )
        db.session.add_all([challenge1, challenge2])
        db.session.flush()

        # Create initiatives
        initiative1 = Initiative(
            organization_id=sample_organization.id,
            name="Digital Sales",
            description="Expand online sales channels",
        )
        initiative2 = Initiative(
            organization_id=sample_organization.id,
            name="Process Automation",
            description="Automate manual processes",
        )
        db.session.add_all([initiative1, initiative2])
        db.session.flush()

        # Create systems
        system1 = System(
            organization_id=sample_organization.id, name="CRM System", description="Customer relationship management"
        )
        system2 = System(
            organization_id=sample_organization.id, name="ERP System", description="Enterprise resource planning"
        )
        db.session.add_all([system1, system2])
        db.session.flush()

        # Create links
        link1 = InitiativeSystemLink(initiative_id=initiative1.id, system_id=system1.id)
        link2 = InitiativeSystemLink(initiative_id=initiative2.id, system_id=system2.id)
        db.session.add_all([link1, link2])
        db.session.flush()

        # Create KPIs
        kpi1 = KPI(initiative_system_link_id=link1.id, name="Monthly Revenue", description="Total monthly revenue")
        kpi2 = KPI(initiative_system_link_id=link2.id, name="Process Efficiency", description="Process completion rate")
        db.session.add_all([kpi1, kpi2])
        db.session.commit()

        return {
            "spaces": [space1, space2],
            "challenges": [challenge1, challenge2],
            "initiatives": [initiative1, initiative2],
            "systems": [system1, system2],
            "kpis": [kpi1, kpi2],
        }

    def test_search_by_space_name(self, app, db, sample_organization, search_data):
        """Test searching for spaces by name"""
        with app.app_context():
            results = SearchService.search(
                query="Finance", organization_id=sample_organization.id, entity_types=["space"]
            )

            # Should find Finance Space
            space_results = [r for r in results if r["type"] == "space"]
            assert len(space_results) >= 1
            assert any("Finance" in r["name"] for r in space_results)

    def test_search_by_challenge_name(self, app, db, sample_organization, search_data):
        """Test searching for challenges by name"""
        with app.app_context():
            results = SearchService.search(
                query="Revenue", organization_id=sample_organization.id, entity_types=["challenge"]
            )

            # Should find Revenue Growth challenge
            challenge_results = [r for r in results if r["type"] == "challenge"]
            assert len(challenge_results) >= 1
            assert any("Revenue" in r["name"] for r in challenge_results)

    def test_search_by_initiative_name(self, app, db, sample_organization, search_data):
        """Test searching for initiatives by name"""
        with app.app_context():
            results = SearchService.search(
                query="Digital", organization_id=sample_organization.id, entity_types=["initiative"]
            )

            # Should find Digital Sales initiative
            initiative_results = [r for r in results if r["type"] == "initiative"]
            assert len(initiative_results) >= 1
            assert any("Digital" in r["name"] for r in initiative_results)

    def test_search_by_system_name(self, app, db, sample_organization, search_data):
        """Test searching for systems by name"""
        with app.app_context():
            results = SearchService.search(query="CRM", organization_id=sample_organization.id, entity_types=["system"])

            # Should find CRM System
            system_results = [r for r in results if r["type"] == "system"]
            assert len(system_results) >= 1
            assert any("CRM" in r["name"] for r in system_results)

    def test_search_by_kpi_name(self, app, db, sample_organization, search_data):
        """Test searching for KPIs by name"""
        with app.app_context():
            results = SearchService.search(
                query="Revenue", organization_id=sample_organization.id, entity_types=["kpi"]
            )

            # Should find Monthly Revenue KPI
            kpi_results = [r for r in results if r["type"] == "kpi"]
            assert len(kpi_results) >= 1
            assert any("Revenue" in r["name"] for r in kpi_results)

    def test_search_all_entity_types(self, app, db, sample_organization, search_data):
        """Test searching across all entity types"""
        with app.app_context():
            results = SearchService.search(query="Revenue", organization_id=sample_organization.id)

            # Should find Revenue in both challenge and KPI
            types_found = {r["type"] for r in results}
            assert "challenge" in types_found
            assert "kpi" in types_found

    def test_search_case_insensitive(self, app, db, sample_organization, search_data):
        """Test that search is case-insensitive"""
        with app.app_context():
            results_lower = SearchService.search(query="revenue", organization_id=sample_organization.id)
            results_upper = SearchService.search(query="REVENUE", organization_id=sample_organization.id)
            results_mixed = SearchService.search(query="ReVeNuE", organization_id=sample_organization.id)

            # All should return same number of results
            assert len(results_lower) == len(results_upper)
            assert len(results_lower) == len(results_mixed)

    def test_search_by_description(self, app, db, sample_organization, search_data):
        """Test searching by description text"""
        with app.app_context():
            results = SearchService.search(
                query="automation", organization_id=sample_organization.id, entity_types=["initiative"]
            )

            # Should find "Process Automation" initiative
            assert len(results) >= 1
            assert any("Automation" in r["name"] for r in results)

    def test_search_empty_query(self, app, db, sample_organization, search_data):
        """Test search with empty query"""
        with app.app_context():
            results = SearchService.search(query="", organization_id=sample_organization.id)

            # Should return empty list for empty query
            assert len(results) == 0

    def test_search_no_results(self, app, db, sample_organization, search_data):
        """Test search with no matching results"""
        with app.app_context():
            results = SearchService.search(query="nonexistentquery12345", organization_id=sample_organization.id)

            # Should return empty list
            assert len(results) == 0

    def test_search_with_limit(self, app, db, sample_organization, search_data):
        """Test search with result limit"""
        with app.app_context():
            # Create many entities with "test" in name
            for i in range(10):
                space = Space(
                    organization_id=sample_organization.id,
                    name=f"Test Space {i}",
                    description=f"Test description {i}",
                )
                db.session.add(space)
            db.session.commit()

            # Search with limit
            results = SearchService.search(query="Test Space", organization_id=sample_organization.id, limit=5)

            # Should return at most 5 results
            assert len(results) <= 5

    def test_search_respects_organization(self, app, db, sample_organization):
        """Test that search only returns results from specified organization"""
        from app.models import Organization

        with app.app_context():
            # Create another organization
            org2 = Organization(name="Other Org", description="Other", is_active=True)
            db.session.add(org2)
            db.session.flush()

            # Create space in org2
            space_org2 = Space(organization_id=org2.id, name="Finance Space Org2", description="Finance")
            db.session.add(space_org2)
            db.session.commit()

            # Search in sample_organization
            results = SearchService.search(query="Finance", organization_id=sample_organization.id)

            # Should not find space from org2
            org2_results = [r for r in results if r.get("id") == space_org2.id]
            assert len(org2_results) == 0

    def test_search_partial_match(self, app, db, sample_organization, search_data):
        """Test that search matches partial words"""
        with app.app_context():
            results = SearchService.search(query="Fin", organization_id=sample_organization.id)

            # Should find "Finance Space" with partial match
            assert len(results) >= 1
            assert any("Finance" in r["name"] for r in results)

    def test_search_multiple_words(self, app, db, sample_organization, search_data):
        """Test searching with multiple words"""
        with app.app_context():
            results = SearchService.search(query="Revenue Growth", organization_id=sample_organization.id)

            # Should find challenge with both words
            assert len(results) >= 1
            challenge_results = [r for r in results if r["type"] == "challenge"]
            assert any("Revenue Growth" in r["name"] for r in challenge_results)
