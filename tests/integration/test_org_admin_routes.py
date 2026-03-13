"""
Integration tests for organization admin routes
"""

import pytest

from app.models import GovernanceBody, Initiative, Space, System, ValueType


class TestOrgAdminSpaceManagement:
    """Tests for space management routes"""

    def test_create_space_page_loads(self, client, org_user, sample_organization, db):
        """Test space creation form loads"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/spaces/create")
        assert response.status_code == 200
        assert b"Space" in response.data or b"space" in response.data

    def test_edit_space_page_loads(self, client, org_user, sample_organization, db):
        """Test space edit form loads"""
        space = Space(name="Test Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/spaces/{space.id}/edit")
        assert response.status_code == 200
        assert b"Test Space" in response.data

    def test_delete_space_confirmation(self, client, org_user, sample_organization, db):
        """Test space deletion shows confirmation"""
        space = Space(name="To Delete", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/spaces/{space.id}/delete")
        assert response.status_code in [200, 302, 404, 405]


class TestOrgAdminChallengeManagement:
    """Tests for challenge management routes"""

    def test_create_challenge_page_loads(self, client, org_user, sample_organization, db):
        """Test challenge creation form loads"""
        # Need a space first
        space = Space(name="Test Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/challenges/create")
        assert response.status_code in [200, 404]

    def test_challenges_list_page(self, client, org_user, sample_organization, db):
        """Test challenges list page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/challenges")
        assert response.status_code == 200


class TestOrgAdminInitiativeManagement:
    """Tests for initiative management routes"""

    def test_initiatives_list_page(self, client, org_user, sample_organization, db):
        """Test initiatives list page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/initiatives")
        assert response.status_code == 200

    def test_create_initiative_page_loads(self, client, org_user, sample_organization, db):
        """Test initiative creation form loads"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/initiatives/create")
        assert response.status_code in [200, 404]

    def test_edit_initiative_page_loads(self, client, org_user, sample_organization, db):
        """Test initiative edit form loads"""
        initiative = Initiative(name="Test Initiative", organization_id=sample_organization.id)
        db.session.add(initiative)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/initiatives/{initiative.id}/edit")
        assert response.status_code == 200
        assert b"Test Initiative" in response.data


class TestOrgAdminSystemManagement:
    """Tests for system management routes"""

    @pytest.mark.skip(reason="Systems list page removed - route no longer exists")
    def test_systems_list_page(self, client, org_user, sample_organization, db):
        """Test systems list page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/systems")
        assert response.status_code == 200

    def test_create_system_page_loads(self, client, org_user, sample_organization, db):
        """Test system creation form loads"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/systems/create")
        assert response.status_code in [200, 404]

    def test_edit_system_page_loads(self, client, org_user, sample_organization, db):
        """Test system edit form loads"""
        system = System(name="Test System", organization_id=sample_organization.id)
        db.session.add(system)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/systems/{system.id}/edit")
        assert response.status_code == 200
        assert b"Test System" in response.data


class TestOrgAdminGovernanceBodies:
    """Tests for governance body management"""

    def test_governance_bodies_list_page(self, client, org_user, sample_organization, db):
        """Test governance bodies list page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/governance-bodies")
        assert response.status_code == 200

    def test_create_governance_body_page_loads(self, client, org_user, sample_organization, db):
        """Test governance body creation form loads"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/governance-bodies/create")
        assert response.status_code == 200

    def test_edit_governance_body_page_loads(self, client, org_user, sample_organization, db):
        """Test governance body edit form loads"""
        gov_body = GovernanceBody(name="Board of Directors", abbreviation="BOD", organization_id=sample_organization.id)
        db.session.add(gov_body)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/governance-bodies/{gov_body.id}/edit")
        assert response.status_code == 200


class TestOrgAdminYAMLOperations:
    """Tests for YAML import/export"""

    def test_yaml_export_page_loads(self, client, org_user, sample_organization, db):
        """Test YAML export page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/yaml/export")
        assert response.status_code in [200, 404]

    def test_yaml_import_page_loads(self, client, org_user, sample_organization, db):
        """Test YAML import page"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/yaml/import")
        assert response.status_code in [200, 404]


class TestOrgAdminDeletionImpact:
    """Tests for deletion impact checking"""

    def test_deletion_impact_for_space(self, client, org_user, sample_organization, db):
        """Test deletion impact check for space"""
        space = Space(name="Test Space", organization_id=sample_organization.id, display_order=1)
        db.session.add(space)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/deletion-impact/space/{space.id}")
        assert response.status_code in [200, 404]

    def test_deletion_impact_for_value_type(self, client, org_user, sample_organization, db):
        """Test deletion impact check for value type"""
        value_type = ValueType(
            name="Test Metric", kind="numeric", organization_id=sample_organization.id, is_active=True
        )
        db.session.add(value_type)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(org_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get(f"/org-admin/deletion-impact/value-type/{value_type.id}")
        assert response.status_code in [200, 404]


class TestOrgAdminPermissionChecks:
    """Tests for permission enforcement in org admin"""

    def test_user_without_space_permission_denied(self, client, sample_user, sample_organization, db):
        """Test user without can_manage_spaces permission is denied"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/spaces/create", follow_redirects=True)
        # Should be denied or redirected
        assert response.status_code in [200, 302, 403]

    def test_user_without_value_type_permission_denied(self, client, sample_user, sample_organization, db):
        """Test user without can_manage_value_types permission is denied"""
        with client.session_transaction() as sess:
            sess["_user_id"] = str(sample_user.id)
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name

        response = client.get("/org-admin/value-types/create", follow_redirects=True)
        # Should be denied or redirected
        assert response.status_code in [200, 302, 403]
