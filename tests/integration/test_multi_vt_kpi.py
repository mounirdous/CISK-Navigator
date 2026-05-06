"""
Multi-value-type KPI integration tests.

Phase 3 coverage for the v7.22.x multi-VT story: the DB has always allowed
many value-type configs per KPI, but until v7.22.0 the create/edit forms and
several read paths assumed exactly one. These tests pin the new behaviour so
future refactors can't silently regress to single-VT assumptions.
"""

import pytest

from app.extensions import db as _db
from app.models import (
    KPI,
    Challenge,
    Contribution,
    GovernanceBody,
    Initiative,
    InitiativeSystemLink,
    KPIGovernanceBodyLink,
    KPIValueTypeConfig,
    Space,
    System,
    ValueType,
)


def _build_workspace_skeleton(db, org, *, num_vts=2, with_kpi=False):
    """Create a minimal Space → Challenge → Initiative → System → SysLink graph
    with `num_vts` numeric value types and a governance body. Returns the
    important objects so individual tests can attach KPIs / configs as needed.
    """
    space = Space(name="S", organization_id=org.id, display_order=1)
    db.session.add(space)
    db.session.flush()

    challenge = Challenge(
        name="C", organization_id=org.id, space_id=space.id, display_order=1
    )
    db.session.add(challenge)
    db.session.flush()

    initiative = Initiative(name="I", organization_id=org.id)
    db.session.add(initiative)
    db.session.flush()

    from app.models import ChallengeInitiativeLink

    db.session.add(
        ChallengeInitiativeLink(
            challenge_id=challenge.id, initiative_id=initiative.id, display_order=1
        )
    )

    system = System(name="Sys", organization_id=org.id)
    db.session.add(system)
    db.session.flush()

    sys_link = InitiativeSystemLink(
        initiative_id=initiative.id, system_id=system.id, display_order=1
    )
    db.session.add(sys_link)
    db.session.flush()

    vts = []
    for i in range(num_vts):
        vt = ValueType(
            name=f"VT{i}",
            kind=ValueType.KIND_NUMERIC,
            unit_label="u",
            organization_id=org.id,
            is_active=True,
            display_order=i,
        )
        db.session.add(vt)
        vts.append(vt)
    db.session.flush()

    gb = GovernanceBody(
        name="GB", abbreviation="GB", organization_id=org.id
    )
    db.session.add(gb)

    kpi = None
    if with_kpi:
        kpi = KPI(
            name="K", initiative_system_link_id=sys_link.id, display_order=1
        )
        db.session.add(kpi)
        db.session.flush()
        for vt in vts:
            db.session.add(
                KPIValueTypeConfig(
                    kpi_id=kpi.id,
                    value_type_id=vt.id,
                    calculation_type="manual",
                )
            )

    db.session.commit()
    return {
        "space": space,
        "challenge": challenge,
        "initiative": initiative,
        "system": system,
        "sys_link": sys_link,
        "vts": vts,
        "gb": gb,
        "kpi": kpi,
    }


@pytest.fixture
def authed(client, org_user, sample_organization):
    """Logged-in client with org context. Mirrors the pattern from
    test_csrf_token_pages.TestCSRFTokenAvailability.authenticated_org_user."""
    with client:
        client.post(
            "/auth/login",
            data={"login": org_user.login, "password": "password123"},
            follow_redirects=True,
        )
        with client.session_transaction() as sess:
            sess["organization_id"] = sample_organization.id
            sess["organization_name"] = sample_organization.name
        yield client


class TestMultiVTSchema:
    """Sanity check that the DB / models have always supported many configs
    per KPI. If this ever fails, every other multi-VT assumption breaks."""

    def test_kpi_can_hold_multiple_value_type_configs(self, db, sample_organization):
        ctx = _build_workspace_skeleton(db, sample_organization, num_vts=3, with_kpi=True)
        configs = list(ctx["kpi"].value_type_configs)
        assert len(configs) == 3
        assert {c.value_type_id for c in configs} == {vt.id for vt in ctx["vts"]}


class TestCreateKpiMultiVT:
    """Phase 1: the create form's checkbox change unlocked multi-VT creation
    via the existing getlist('value_type_ids') backend path."""

    def test_create_kpi_with_two_value_types(self, authed, db, sample_organization):
        ctx = _build_workspace_skeleton(db, sample_organization, num_vts=2)
        sys_link = ctx["sys_link"]
        vt_a, vt_b = ctx["vts"]
        gb = ctx["gb"]

        response = authed.post(
            f"/org-admin/initiative-system-links/{sys_link.id}/kpis/create",
            data={
                "name": "Multi VT KPI",
                "description": "",
                "display_order": "1",
                # The radio→checkbox flip in v7.22.0 lets the browser send
                # multiple value_type_ids; getlist() reads them all.
                "value_type_ids": [str(vt_a.id), str(vt_b.id)],
                "governance_body_ids": [str(gb.id)],
                f"calc_type_{vt_a.id}": "manual",
                f"calc_type_{vt_b.id}": "manual",
            },
            follow_redirects=False,
        )
        # On success the route redirects (302) to the workspace.
        assert response.status_code in (200, 302)

        kpi = KPI.query.filter_by(name="Multi VT KPI").first()
        assert kpi is not None
        configs = list(kpi.value_type_configs)
        assert {c.value_type_id for c in configs} == {vt_a.id, vt_b.id}

    def test_create_kpi_with_single_value_type_still_works(
        self, authed, db, sample_organization
    ):
        """Back-compat: single-VT creation must keep working after the radio
        was changed to a checkbox."""
        ctx = _build_workspace_skeleton(db, sample_organization, num_vts=2)
        vt_a = ctx["vts"][0]

        response = authed.post(
            f"/org-admin/initiative-system-links/{ctx['sys_link'].id}/kpis/create",
            data={
                "name": "Single VT KPI",
                "description": "",
                "display_order": "1",
                "value_type_ids": [str(vt_a.id)],
                "governance_body_ids": [str(ctx["gb"].id)],
                f"calc_type_{vt_a.id}": "manual",
            },
            follow_redirects=False,
        )
        assert response.status_code in (200, 302)
        kpi = KPI.query.filter_by(name="Single VT KPI").first()
        assert kpi is not None
        assert len(list(kpi.value_type_configs)) == 1


class TestEditKpiAddRemoveVT:
    """Phase 1: edit_kpi handler diffs submitted VT ids against existing
    configs and inserts / deletes accordingly. Removal of a config that has
    contributions or snapshots requires confirm_remove_vt_ids."""

    def _post_edit(self, client, kpi, vt_ids, *, confirm_remove="", gb_id=None):
        data = {
            "name": kpi.name,
            "description": kpi.description or "",
            "display_order": str(kpi.display_order or 1),
            "value_type_ids": [str(v) for v in vt_ids],
            "confirm_remove_vt_ids": confirm_remove,
        }
        if gb_id is not None:
            data["governance_body_ids"] = [str(gb_id)]
        return client.post(
            f"/org-admin/kpis/{kpi.id}/edit", data=data, follow_redirects=False
        )

    def test_add_new_value_type_to_single_vt_kpi(
        self, authed, db, sample_organization
    ):
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=2, with_kpi=False
        )
        vt_a, vt_b = ctx["vts"]
        kpi = KPI(
            name="Solo", initiative_system_link_id=ctx["sys_link"].id, display_order=1
        )
        db.session.add(kpi)
        db.session.flush()
        db.session.add(
            KPIValueTypeConfig(
                kpi_id=kpi.id, value_type_id=vt_a.id, calculation_type="manual"
            )
        )
        db.session.add(
            KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=ctx["gb"].id)
        )
        db.session.commit()
        kpi_id = kpi.id

        # Add vt_b alongside vt_a
        self._post_edit(
            authed, kpi, [vt_a.id, vt_b.id], gb_id=ctx["gb"].id
        )

        refreshed = KPI.query.get(kpi_id)
        assert {c.value_type_id for c in refreshed.value_type_configs} == {
            vt_a.id, vt_b.id
        }

    def test_remove_unused_value_type_succeeds_without_confirm(
        self, authed, db, sample_organization
    ):
        """A VT config with no contributions/snapshots can be removed in one
        step — no JS confirm needed."""
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=2, with_kpi=True
        )
        vt_a, vt_b = ctx["vts"]
        kpi = ctx["kpi"]
        db.session.add(
            KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=ctx["gb"].id)
        )
        db.session.commit()
        kpi_id = kpi.id

        # Submit only vt_a — vt_b should be deleted (it has no data)
        self._post_edit(authed, kpi, [vt_a.id], gb_id=ctx["gb"].id)

        refreshed = KPI.query.get(kpi_id)
        assert {c.value_type_id for c in refreshed.value_type_configs} == {vt_a.id}

    def test_remove_value_type_with_data_blocked_without_confirm(
        self, authed, db, sample_organization
    ):
        """When the dropped VT has contributions, the route must refuse
        without confirm_remove_vt_ids and leave both configs intact."""
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=2, with_kpi=True
        )
        vt_a, vt_b = ctx["vts"]
        kpi = ctx["kpi"]
        cfg_b = next(c for c in kpi.value_type_configs if c.value_type_id == vt_b.id)
        db.session.add(
            Contribution(
                kpi_value_type_config_id=cfg_b.id,
                contributor_name="Alice",
                numeric_value=42.0,
                comment="x",
            )
        )
        db.session.add(
            KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=ctx["gb"].id)
        )
        db.session.commit()
        kpi_id = kpi.id

        response = self._post_edit(
            authed, kpi, [vt_a.id], gb_id=ctx["gb"].id  # no confirm
        )
        # On a guarded validation failure the route re-renders (200), not redirects
        assert response.status_code == 200

        refreshed = KPI.query.get(kpi_id)
        assert {c.value_type_id for c in refreshed.value_type_configs} == {
            vt_a.id, vt_b.id
        }, "configs must be untouched when removal isn't confirmed"

    def test_remove_value_type_with_data_proceeds_with_confirm(
        self, authed, db, sample_organization
    ):
        """When confirm_remove_vt_ids names the VT, the config is deleted and
        its contributions cascade away."""
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=2, with_kpi=True
        )
        vt_a, vt_b = ctx["vts"]
        kpi = ctx["kpi"]
        cfg_b = next(c for c in kpi.value_type_configs if c.value_type_id == vt_b.id)
        cfg_b_id = cfg_b.id
        db.session.add(
            Contribution(
                kpi_value_type_config_id=cfg_b.id,
                contributor_name="Alice",
                numeric_value=42.0,
                comment="x",
            )
        )
        db.session.add(
            KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=ctx["gb"].id)
        )
        db.session.commit()
        kpi_id = kpi.id

        self._post_edit(
            authed, kpi, [vt_a.id], confirm_remove=str(vt_b.id), gb_id=ctx["gb"].id
        )

        refreshed = KPI.query.get(kpi_id)
        assert {c.value_type_id for c in refreshed.value_type_configs} == {vt_a.id}
        # Cascade DELETE on KPIValueTypeConfig.contributions
        leftover = Contribution.query.filter_by(
            kpi_value_type_config_id=cfg_b_id
        ).count()
        assert leftover == 0

    def test_zero_value_types_blocked(self, authed, db, sample_organization):
        """A KPI must always keep at least one value type; an empty submission
        must be rejected with the configs untouched."""
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=1, with_kpi=True
        )
        kpi = ctx["kpi"]
        db.session.add(
            KPIGovernanceBodyLink(kpi_id=kpi.id, governance_body_id=ctx["gb"].id)
        )
        db.session.commit()
        kpi_id = kpi.id

        response = self._post_edit(authed, kpi, [], gb_id=ctx["gb"].id)
        assert response.status_code == 200

        refreshed = KPI.query.get(kpi_id)
        assert len(list(refreshed.value_type_configs)) == 1, (
            "the only VT must survive an attempt to drop everything"
        )


class TestKpiDashboardMultiVT:
    """Phase 2: kpi_dashboard route emits one row per (kpi × VT) cell instead
    of breaking after the first config with data."""

    def test_dashboard_renders_both_vts_for_multi_vt_kpi(
        self, authed, db, sample_organization
    ):
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=2, with_kpi=True
        )
        # Both VTs need consensus values for the rows to be meaningful in the
        # status counts; even without data the dashboard still emits per-cell
        # rows but the assertions below focus on VT-name visibility.
        vt_a, vt_b = ctx["vts"]
        ctx["kpi"].name = "Multi-VT under test"
        db.session.commit()

        response = authed.get("/workspace/kpi-dashboard")
        assert response.status_code == 200
        body = response.data.decode("utf-8")

        # Both VT names should appear at least once (one per cell row)
        assert "VT0" in body
        assert "VT1" in body
        # The "tracked rows" subtitle is added when cells > distinct KPIs
        assert "tracked rows" in body

    def test_dashboard_subtitle_omitted_when_one_cell_per_kpi(
        self, authed, db, sample_organization
    ):
        """Single-VT workspace: cell count == KPI count, so the subtitle is
        suppressed (cosmetic regression check)."""
        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=1, with_kpi=True
        )
        response = authed.get("/workspace/kpi-dashboard")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "tracked rows" not in body


class TestGeographyApiMultiVT:
    """Phase 2: api_map_kpis emits a `value_types` array per feature so the
    map details panel can render a card per VT."""

    def test_feature_carries_value_types_array(self, authed, db, sample_organization):
        from app.models import (
            GeographyCountry,
            GeographyRegion,
            KPIGeographyAssignment,
        )

        ctx = _build_workspace_skeleton(
            db, sample_organization, num_vts=2, with_kpi=True
        )
        # Assign the KPI to a country with coordinates so the route emits a
        # feature for it.
        region = GeographyRegion(
            name="R", organization_id=sample_organization.id, display_order=1
        )
        db.session.add(region)
        db.session.flush()
        country = GeographyCountry(
            name="Country",
            iso_code="XX",
            region_id=region.id,
            latitude=10.0,
            longitude=20.0,
        )
        db.session.add(country)
        db.session.flush()
        db.session.add(
            KPIGeographyAssignment(kpi_id=ctx["kpi"].id, country_id=country.id)
        )
        db.session.commit()

        response = authed.get("/org-admin/geography/api/map-kpis.json")
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        features = data.get("features", [])
        assert features, "expected at least one feature for the geocoded KPI"
        feat = next(
            (f for f in features if f["properties"]["kpi_id"] == ctx["kpi"].id), None
        )
        assert feat is not None
        vts = feat["properties"].get("value_types")
        assert isinstance(vts, list)
        assert len(vts) == 2
        assert {v["vt_name"] for v in vts} == {"VT0", "VT1"}
