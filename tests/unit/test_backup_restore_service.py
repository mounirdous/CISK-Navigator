"""
Unit tests for FullBackupService and FullRestoreService — action items coverage.
"""

import json

import pytest

from app.models import (
    ActionItem,
    ActionItemMention,
    Challenge,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPI,
    Organization,
    Space,
    System,
    User,
    UserOrganizationMembership,
)
from app.services.full_backup_service import FullBackupService
from app.services.full_restore_service import FullRestoreService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_org(db, name="Backup Test Org"):
    org = Organization(name=name, is_active=True)
    db.session.add(org)
    db.session.commit()
    return org


def _make_user(db, login="owner", email="owner@test.com"):
    user = User(login=login, email=email, display_name="Owner", is_active=True)
    user.set_password("Password1!")
    db.session.add(user)
    db.session.commit()
    return user


def _make_membership(db, user, org):
    m = UserOrganizationMembership(user_id=user.id, organization_id=org.id)
    db.session.add(m)
    db.session.commit()
    return m


def _make_action_item(db, org, owner, **kwargs):
    defaults = dict(
        type="action",
        title="Test Action",
        status="active",
        priority="medium",
        visibility="shared",
    )
    defaults.update(kwargs)
    item = ActionItem(
        organization_id=org.id,
        owner_user_id=owner.id,
        created_by_user_id=owner.id,
        **defaults,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _make_space(db, org, name="Test Space"):
    space = Space(organization_id=org.id, name=name)
    db.session.add(space)
    db.session.commit()
    return space


def _make_system(db, org, name="Test System"):
    system = System(organization_id=org.id, name=name)
    db.session.add(system)
    db.session.commit()
    return system


def _make_gb(db, org, name="Risk Committee"):
    gb = GovernanceBody(
        organization_id=org.id,
        name=name,
        abbreviation=name[:10],
        color="#3498db",
    )
    db.session.add(gb)
    db.session.commit()
    return gb


# ---------------------------------------------------------------------------
# Backup tests
# ---------------------------------------------------------------------------

class TestFullBackupActionItems:

    def test_action_items_present_in_backup(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        _make_action_item(db, sample_organization, sample_user, title="My Action")

        backup = FullBackupService.create_full_backup(sample_organization.id)

        assert "action_items" in backup
        assert len(backup["action_items"]) == 1
        item = backup["action_items"][0]
        assert item["title"] == "My Action"
        assert item["type"] == "action"
        assert item["owner_login"] == sample_user.login

    def test_backup_empty_when_no_action_items(self, db, sample_organization):
        backup = FullBackupService.create_full_backup(sample_organization.id)
        assert backup["action_items"] == []

    def test_backup_captures_all_fields(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        item = _make_action_item(
            db, sample_organization, sample_user,
            title="Detailed Action",
            type="memo",
            description="Some description",
            status="completed",
            priority="urgent",
            visibility="private",
        )

        backup = FullBackupService.create_full_backup(sample_organization.id)
        exported = backup["action_items"][0]

        assert exported["type"] == "memo"
        assert exported["description"] == "Some description"
        assert exported["status"] == "completed"
        assert exported["priority"] == "urgent"
        assert exported["visibility"] == "private"

    def test_backup_includes_governance_bodies(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        gb = _make_gb(db, sample_organization, "Audit Board")
        item = _make_action_item(db, sample_organization, sample_user, title="GB Action")
        item.governance_bodies.append(gb)
        db.session.commit()

        backup = FullBackupService.create_full_backup(sample_organization.id)
        exported = backup["action_items"][0]

        assert "Audit Board" in exported["governance_bodies"]

    def test_backup_includes_mentions_with_entity_name(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        system = _make_system(db, sample_organization, "ERP System")
        item = _make_action_item(db, sample_organization, sample_user, title="Mention Action")
        mention = ActionItemMention(
            action_item_id=item.id,
            entity_type="system",
            entity_id=system.id,
            mention_text="@ERP System",
        )
        db.session.add(mention)
        db.session.commit()

        backup = FullBackupService.create_full_backup(sample_organization.id)
        exported = backup["action_items"][0]

        assert len(exported["mentions"]) == 1
        m = exported["mentions"][0]
        assert m["entity_type"] == "system"
        assert m["entity_name"] == "ERP System"
        assert m["mention_text"] == "@ERP System"

    def test_backup_mention_with_missing_entity_exports_none_name(self, db, sample_organization, sample_user):
        """Mention pointing to a deleted entity should export entity_name=None without crashing."""
        _make_membership(db, sample_user, sample_organization)
        item = _make_action_item(db, sample_organization, sample_user, title="Orphan Mention")
        mention = ActionItemMention(
            action_item_id=item.id,
            entity_type="space",
            entity_id=99999,  # non-existent
            mention_text="@Ghost Space",
        )
        db.session.add(mention)
        db.session.commit()

        backup = FullBackupService.create_full_backup(sample_organization.id)
        exported = backup["action_items"][0]

        assert exported["mentions"][0]["entity_name"] is None

    def test_backup_format_version_is_3(self, db, sample_organization):
        backup = FullBackupService.create_full_backup(sample_organization.id)
        assert backup["metadata"]["backup_format_version"] == "3.0"


# ---------------------------------------------------------------------------
# Restore tests
# ---------------------------------------------------------------------------

class TestFullRestoreActionItems:
    """
    We test _restore_action_items directly to avoid the DB schema version
    check that blocks restore_from_json in unit tests.
    """

    def _build_backup_with_action_items(self, action_items_list):
        """Return a minimal backup dict containing only action_items."""
        return {"action_items": action_items_list}

    def test_restore_basic_action_item(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        gb_map = {}
        user_map = {sample_user.login: sample_user}

        backup = self._build_backup_with_action_items([
            {
                "type": "action",
                "title": "Restored Action",
                "description": "desc",
                "status": "active",
                "priority": "high",
                "visibility": "shared",
                "owner_login": sample_user.login,
                "created_by_login": sample_user.login,
                "due_date": None,
                "completed_at": None,
                "governance_bodies": [],
                "mentions": [],
            }
        ])

        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, gb_map)

        assert stats["action_items"] == 1
        assert stats["warnings"] == []

        item = ActionItem.query.filter_by(organization_id=sample_organization.id).first()
        assert item is not None
        assert item.title == "Restored Action"
        assert item.priority == "high"

    def test_restore_skips_item_when_owner_not_found(self, db, sample_organization, sample_user):
        user_map = {}  # empty — owner not resolvable
        backup = self._build_backup_with_action_items([
            {
                "type": "action",
                "title": "No Owner Action",
                "status": "active",
                "priority": "medium",
                "visibility": "shared",
                "owner_login": "ghost_user",
                "governance_bodies": [],
                "mentions": [],
            }
        ])

        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, {})

        assert stats["action_items"] == 0
        assert any("ghost_user" in w for w in stats["warnings"])

    def test_restore_governance_body_link(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        gb = _make_gb(db, sample_organization, "Steering Committee")
        user_map = {sample_user.login: sample_user}
        gb_map = {"Steering Committee": gb}

        backup = self._build_backup_with_action_items([
            {
                "type": "action",
                "title": "GB Action",
                "status": "active",
                "priority": "medium",
                "visibility": "shared",
                "owner_login": sample_user.login,
                "governance_bodies": ["Steering Committee"],
                "mentions": [],
            }
        ])

        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, gb_map)

        assert stats["action_items"] == 1
        item = ActionItem.query.filter_by(organization_id=sample_organization.id).first()
        assert any(g.name == "Steering Committee" for g in item.governance_bodies)

    def test_restore_mention_resolved_by_entity_name(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        system = _make_system(db, sample_organization, "CRM System")
        user_map = {sample_user.login: sample_user}

        backup = self._build_backup_with_action_items([
            {
                "type": "action",
                "title": "Mention Action",
                "status": "active",
                "priority": "medium",
                "visibility": "shared",
                "owner_login": sample_user.login,
                "governance_bodies": [],
                "mentions": [
                    {"entity_type": "system", "entity_name": "CRM System", "mention_text": "@CRM System"}
                ],
            }
        ])

        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, {})

        assert stats["action_items"] == 1
        item = ActionItem.query.filter_by(organization_id=sample_organization.id).first()
        assert len(item.mentions) == 1
        assert item.mentions[0].entity_id == system.id
        assert item.mentions[0].mention_text == "@CRM System"

    def test_restore_mention_skipped_when_entity_not_found(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        user_map = {sample_user.login: sample_user}

        backup = self._build_backup_with_action_items([
            {
                "type": "action",
                "title": "Ghost Mention Action",
                "status": "active",
                "priority": "medium",
                "visibility": "shared",
                "owner_login": sample_user.login,
                "governance_bodies": [],
                "mentions": [
                    {"entity_type": "space", "entity_name": "Nonexistent Space", "mention_text": "@Nonexistent Space"}
                ],
            }
        ])

        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, {})

        assert stats["action_items"] == 1  # item is still created
        assert any("Nonexistent Space" in w for w in stats["warnings"])
        item = ActionItem.query.filter_by(organization_id=sample_organization.id).first()
        assert len(item.mentions) == 0

    def test_restore_due_date_parsing(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        user_map = {sample_user.login: sample_user}

        backup = self._build_backup_with_action_items([
            {
                "type": "action",
                "title": "Dated Action",
                "status": "active",
                "priority": "medium",
                "visibility": "shared",
                "owner_login": sample_user.login,
                "due_date": "2026-12-31",
                "completed_at": None,
                "governance_bodies": [],
                "mentions": [],
            }
        ])

        FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, {})

        item = ActionItem.query.filter_by(organization_id=sample_organization.id).first()
        assert item.due_date is not None
        assert item.due_date.isoformat() == "2026-12-31"

    def test_restore_multiple_items(self, db, sample_organization, sample_user):
        _make_membership(db, sample_user, sample_organization)
        user_map = {sample_user.login: sample_user}

        items_data = [
            {
                "type": "action", "title": f"Action {i}", "status": "active",
                "priority": "medium", "visibility": "shared",
                "owner_login": sample_user.login,
                "governance_bodies": [], "mentions": [],
            }
            for i in range(5)
        ]
        backup = self._build_backup_with_action_items(items_data)

        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, user_map, {})

        assert stats["action_items"] == 5
        assert ActionItem.query.filter_by(organization_id=sample_organization.id).count() == 5

    def test_restore_empty_action_items_list(self, db, sample_organization, sample_user):
        backup = self._build_backup_with_action_items([])
        stats = FullRestoreService._restore_action_items(backup, sample_organization.id, {}, {})
        assert stats["action_items"] == 0
        assert stats["warnings"] == []
