"""
Regression test for the @-stripped name fallback in mention restore.

A real-world incident (CIO Onboarding backup, May 2026): an action-item
mention referenced an initiative by a stale json_id. The restorer's existing
name-fallback never fired because mention_text comes through with a leading
'@' (e.g. '@Establish a weekly CIO communication rhythm'), and entity_lookup
is keyed on bare names. Result: the mention was silently skipped on every
import. Fix: strip the leading '@' before the name lookup.
"""

from app.models import (
    ActionItem,
    ActionItemMention,
    Challenge,
    Initiative,
    Space,
)
from app.services.full_restore_service import FullRestoreService


def _build_workspace_for_restore(db, org, *, ini_name):
    """Minimal Space → Challenge → Initiative skeleton so the mention has
    something to resolve to. We commit so each entity has a real DB id."""
    space = Space(name="S", organization_id=org.id, display_order=1)
    db.session.add(space)
    db.session.flush()
    challenge = Challenge(
        name="C", organization_id=org.id, space_id=space.id, display_order=1
    )
    db.session.add(challenge)
    db.session.flush()
    initiative = Initiative(name=ini_name, organization_id=org.id)
    db.session.add(initiative)
    db.session.flush()
    from app.models import ChallengeInitiativeLink

    db.session.add(
        ChallengeInitiativeLink(
            challenge_id=challenge.id, initiative_id=initiative.id, display_order=1
        )
    )
    db.session.commit()
    return initiative


class TestMentionAtStripFallback:
    def test_stale_json_id_is_healed_via_at_stripped_mention_text(
        self, db, sample_organization, org_user
    ):
        """Reproduces the CIO Onboarding incident: mention json_id doesn't
        match anything in the restored set, but mention_text (with leading
        '@') names a real initiative. The fallback must strip the '@' and
        find the initiative by bare name."""
        ini_name = "Establish a weekly CIO communication rhythm"
        initiative = _build_workspace_for_restore(db, sample_organization, ini_name=ini_name)

        # Backup payload simulating the bug: json_id 1089 doesn't exist in
        # this org's restore (only the new initiative.id does), and
        # entity_name is None (matching the real-world export shape).
        backup = {
            "action_items": [
                {
                    "type": "action",
                    "title": "Board",
                    "description": "",
                    "status": "active",
                    "priority": "medium",
                    "is_global": False,
                    "visibility": "shared",
                    "owner_login": org_user.login,
                    "created_by_login": org_user.login,
                    "created_at": "2026-05-06T14:00:00",
                    "governance_bodies": [],
                    "links": [],
                    "mentions": [
                        {
                            "entity_type": "initiative",
                            "json_id": 1089,                   # stale, not in this restore
                            "entity_name": None,               # also missing
                            "mention_text": f"@{ini_name}",    # the only signal we have
                        }
                    ],
                }
            ]
        }

        # user_map maps login → User object (not id) — see line ~1405 of
        # full_restore_service.py where owner_user.id is later read.
        user_map = {org_user.login: org_user}
        # No json_id remap available — forces the name fallback path
        stats = FullRestoreService._restore_action_items(
            backup,
            sample_organization.id,
            user_map,
            governance_body_map={},
            json_id_map={},
        )

        # The action item must restore...
        assert stats["action_items"] == 1, (
            f"action item not restored. warnings={stats.get('warnings')}"
        )
        # ...AND no warning was raised — the @-strip fallback should resolve silently
        warnings = stats.get("warnings", [])
        assert not any("not found" in w for w in warnings), (
            f"expected silent heal, got warnings: {warnings}"
        )

        # ...AND the mention row must point at the real initiative, not be skipped
        ai = ActionItem.query.filter_by(title="Board").first()
        assert ai is not None
        mentions = ActionItemMention.query.filter_by(action_item_id=ai.id).all()
        assert len(mentions) == 1, "the mention was skipped instead of healed"
        assert mentions[0].entity_type == "initiative"
        assert mentions[0].entity_id == initiative.id
