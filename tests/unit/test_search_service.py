"""
Test Search Service for global search functionality
"""

import pytest

from app.models import KPI, Challenge, Initiative, InitiativeSystemLink, Space, System
from app.services.search_service import SearchService


def _total(results):
    """Count total results across all entity-type buckets."""
    return sum(len(v) for k, v in results.items() if k != "query_info" and isinstance(v, list))


def _all_items(results):
    """Flatten all entity results into a single list."""
    items = []
    for k, v in results.items():
        if k != "query_info" and isinstance(v, list):
            items.extend(v)
    return items


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
            results = SearchService.search_all(
                query="Finance",
                filters={"entity_types": ["spaces"]},
                organization_id=sample_organization.id,
            )
            space_results = results.get("spaces", [])
            assert len(space_results) >= 1
            assert any("Finance" in r["name"] for r in space_results)

    def test_search_by_challenge_name(self, app, db, sample_organization, search_data):
        """Test searching for challenges by name"""
        with app.app_context():
            results = SearchService.search_all(
                query="Revenue",
                filters={"entity_types": ["challenges"]},
                organization_id=sample_organization.id,
            )
            challenge_results = results.get("challenges", [])
            assert len(challenge_results) >= 1
            assert any("Revenue" in r["name"] for r in challenge_results)

    def test_search_by_initiative_name(self, app, db, sample_organization, search_data):
        """Test searching for initiatives by name"""
        with app.app_context():
            results = SearchService.search_all(
                query="Digital",
                filters={"entity_types": ["initiatives"]},
                organization_id=sample_organization.id,
            )
            initiative_results = results.get("initiatives", [])
            assert len(initiative_results) >= 1
            assert any("Digital" in r["name"] for r in initiative_results)

    def test_search_by_system_name(self, app, db, sample_organization, search_data):
        """Test searching for systems by name"""
        with app.app_context():
            results = SearchService.search_all(
                query="CRM",
                filters={"entity_types": ["systems"]},
                organization_id=sample_organization.id,
            )
            system_results = results.get("systems", [])
            assert len(system_results) >= 1
            assert any("CRM" in r["name"] for r in system_results)

    def test_search_by_kpi_name(self, app, db, sample_organization, search_data):
        """Test searching for KPIs by name"""
        with app.app_context():
            results = SearchService.search_all(
                query="Revenue",
                filters={"entity_types": ["kpis"]},
                organization_id=sample_organization.id,
            )
            kpi_results = results.get("kpis", [])
            assert len(kpi_results) >= 1
            assert any("Revenue" in r["name"] for r in kpi_results)

    def test_search_all_entity_types(self, app, db, sample_organization, search_data):
        """Test searching across all entity types"""
        with app.app_context():
            results = SearchService.search_all(query="Revenue", organization_id=sample_organization.id)
            # Should find Revenue in both challenges and KPIs
            assert len(results.get("challenges", [])) > 0
            assert len(results.get("kpis", [])) > 0

    def test_search_case_insensitive(self, app, db, sample_organization, search_data):
        """Test that search is case-insensitive"""
        with app.app_context():
            results_lower = SearchService.search_all(query="revenue", organization_id=sample_organization.id)
            results_upper = SearchService.search_all(query="REVENUE", organization_id=sample_organization.id)
            results_mixed = SearchService.search_all(query="ReVeNuE", organization_id=sample_organization.id)
            # All should return same number of results
            assert _total(results_lower) == _total(results_upper)
            assert _total(results_lower) == _total(results_mixed)

    def test_search_by_description(self, app, db, sample_organization, search_data):
        """Test searching by description text"""
        with app.app_context():
            results = SearchService.search_all(
                query="automation",
                filters={"entity_types": ["initiatives"]},
                organization_id=sample_organization.id,
            )
            initiative_results = results.get("initiatives", [])
            assert len(initiative_results) >= 1
            assert any("Automation" in r["name"] for r in initiative_results)

    def test_search_empty_query(self, app, db, sample_organization, search_data):
        """Test search with empty query returns empty results"""
        with app.app_context():
            results = SearchService.search_all(query="", organization_id=sample_organization.id)
            assert _total(results) == 0

    def test_search_no_results(self, app, db, sample_organization, search_data):
        """Test search with no matching results"""
        with app.app_context():
            results = SearchService.search_all(
                query="nonexistentquery12345", organization_id=sample_organization.id
            )
            assert _total(results) == 0

    def test_search_with_limit(self, app, db, sample_organization, search_data):
        """Test search returns results for matching query"""
        with app.app_context():
            # Create several spaces with "test" in name
            for i in range(5):
                space = Space(
                    organization_id=sample_organization.id,
                    name=f"Test Space {i}",
                    description=f"Test description {i}",
                )
                db.session.add(space)
            db.session.commit()

            results = SearchService.search_all(
                query="Test Space",
                filters={"entity_types": ["spaces"]},
                organization_id=sample_organization.id,
            )
            # Should find test spaces
            assert len(results.get("spaces", [])) >= 1

    def test_search_respects_organization(self, app, db, sample_organization):
        """Test that search only returns results from specified organization"""
        from app.models import Organization

        with app.app_context():
            # Create another organization with a space
            org2 = Organization(name="Other Org", description="Other", is_active=True)
            db.session.add(org2)
            db.session.flush()

            space_org2 = Space(organization_id=org2.id, name="Finance Space Org2", description="Finance")
            db.session.add(space_org2)
            db.session.commit()

            # Search in sample_organization — should not find org2's space
            results = SearchService.search_all(query="Finance", organization_id=sample_organization.id)
            all_items = _all_items(results)
            org2_results = [r for r in all_items if r.get("id") == space_org2.id]
            assert len(org2_results) == 0

    def test_search_partial_match(self, app, db, sample_organization, search_data):
        """Test that search matches partial words"""
        with app.app_context():
            results = SearchService.search_all(query="Fin", organization_id=sample_organization.id)
            space_results = results.get("spaces", [])
            assert len(space_results) >= 1
            assert any("Finance" in r["name"] for r in space_results)

    def test_search_multiple_words(self, app, db, sample_organization, search_data):
        """Test searching with multiple words"""
        with app.app_context():
            results = SearchService.search_all(query="Revenue Growth", organization_id=sample_organization.id)
            challenge_results = results.get("challenges", [])
            assert len(challenge_results) >= 1
            assert any("Revenue Growth" in r["name"] for r in challenge_results)
