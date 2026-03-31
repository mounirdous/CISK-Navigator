"""
Rollup Compute Service — pre-computes and caches all rollup values for an organization.

Walks the full CISK hierarchy (Space→Challenge→Initiative→System→KPI) and stores
computed rollup values in the rollup_cache table for fast workspace loading.
"""

from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Initiative,
    KPIValueTypeConfig,
    RollupCacheEntry,
    Space,
    ValueType,
)
from app.models.system import InitiativeSystemLink


class RollupComputeService:
    """Service for pre-computing and caching rollup values."""

    @staticmethod
    def recompute_organization(organization_id):
        """
        Recompute ALL rollup values for an organization and store in cache.

        Returns dict with stats: {entities_computed, values_cached, duration_ms}
        """
        import time

        start = time.time()

        # Clear existing cache for this org
        RollupCacheEntry.query.filter_by(organization_id=organization_id).delete(synchronize_session=False)
        db.session.commit()  # Commit the delete to avoid unique constraint conflicts

        # Get value types
        value_types = (
            ValueType.query.filter_by(organization_id=organization_id, is_active=True)
            .order_by(ValueType.display_order)
            .all()
        )
        if not value_types:
            db.session.commit()
            return {"entities_computed": 0, "values_cached": 0, "duration_ms": 0}

        non_formula_vts = [vt for vt in value_types if not vt.is_formula()]

        # Get spaces with full hierarchy (eager load)
        from sqlalchemy.orm import selectinload

        spaces = (
            Space.query.filter_by(organization_id=organization_id)
            .options(
                selectinload(Space.challenges)
                .selectinload(Challenge.initiative_links)
                .options(
                    selectinload(ChallengeInitiativeLink.initiative)
                    .selectinload(Initiative.system_links)
                    .options(
                        selectinload(InitiativeSystemLink.system),
                        selectinload(InitiativeSystemLink.kpis)
                        .selectinload(KPI.value_type_configs)
                        .selectinload(KPIValueTypeConfig.value_type),
                    ),
                ),
            )
            .order_by(Space.display_order)
            .all()
        )

        entities_computed = 0
        values_cached = 0
        now = datetime.utcnow()
        _seen = set()  # Track (entity_type, entity_id) to avoid duplicates for shared entities

        # Helper: compute and cache rollup for an entity
        def cache_rollup(entity_type, entity_id, entity_obj, color_config_getter):
            nonlocal values_cached

            # First pass: non-formula value types
            rollup_dict = {}
            for vt in non_formula_vts:
                rollup_data = entity_obj.get_rollup_value(vt.id)
                if rollup_data and rollup_data.get("value") is not None:
                    color_config = color_config_getter(vt.id)
                    try:
                        formatted_value = current_app.jinja_env.filters["format_value"](
                            rollup_data.get("value"), vt, color_config
                        )
                    except Exception:
                        formatted_value = str(rollup_data.get("value"))

                    try:
                        if color_config and hasattr(color_config, "get_value_color"):
                            color = color_config.get_value_color(rollup_data.get("value"))
                        else:
                            color = current_app.jinja_env.filters["default_value_color"](rollup_data.get("value"))
                    except Exception:
                        color = "#6c757d"

                    entry = RollupCacheEntry(
                        organization_id=organization_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        value_type_id=vt.id,
                        value=float(rollup_data["value"]) if rollup_data["value"] is not None else None,
                        formatted_value=formatted_value,
                        unit_label=vt.unit_label,
                        color=color or "#6c757d",
                        formula=rollup_data.get("formula"),
                        is_complete=rollup_data.get("is_complete", False),
                        count_total=rollup_data.get("count_total", 0),
                        count_included=rollup_data.get("count_included", 0),
                        list_label=vt.get_list_option_label(rollup_data.get("value")) if vt.is_list() else None,
                        list_color=vt.get_list_option_color(rollup_data.get("value")) if vt.is_list() else None,
                        computed_at=now,
                    )
                    db.session.add(entry)
                    rollup_dict[vt.id] = {
                        "value": rollup_data.get("value"),
                        "formatted_value": formatted_value,
                    }
                    values_cached += 1

            # Second pass: formula value types
            for vt in value_types:
                if not vt.is_formula() or vt.id in rollup_dict:
                    continue
                if not vt.calculation_config:
                    continue

                # Compute formula from rollup_dict
                try:
                    result = RollupComputeService._compute_formula(vt, rollup_dict, value_types)
                    if result is not None:
                        color_config = color_config_getter(vt.id)
                        try:
                            formatted_value = current_app.jinja_env.filters["format_value"](result, vt, color_config)
                        except Exception:
                            formatted_value = str(result)
                        try:
                            if color_config and hasattr(color_config, "get_value_color"):
                                color = color_config.get_value_color(result)
                            else:
                                color = current_app.jinja_env.filters["default_value_color"](result)
                        except Exception:
                            color = "#6c757d"

                        entry = RollupCacheEntry(
                            organization_id=organization_id,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            value_type_id=vt.id,
                            value=float(result) if result is not None else None,
                            formatted_value=formatted_value,
                            unit_label=vt.unit_label,
                            color=color or "#6c757d",
                            formula="formula",
                            is_complete=True,
                            computed_at=now,
                        )
                        db.session.add(entry)
                        values_cached += 1
                except Exception:
                    pass

        # Helper: cache KPI consensus values
        def cache_kpi(kpi, sys_link):
            nonlocal values_cached

            for vt in value_types:
                config = None
                for c in kpi.value_type_configs:
                    if c.value_type_id == vt.id:
                        config = c
                        break

                if not config:
                    # Check if this is a formula VT that needs a temp config
                    if vt.is_formula():
                        config = KPIValueTypeConfig(
                            kpi_id=kpi.id, value_type_id=vt.id, calculation_type="manual"
                        )
                        config.value_type = vt
                        config.kpi = kpi
                    else:
                        continue

                try:
                    consensus = config.get_consensus_value()
                except Exception:
                    continue

                if not consensus or consensus.get("value") is None:
                    # Cache no_data entry
                    entry = RollupCacheEntry(
                        organization_id=sys_link.initiative.organization_id,
                        entity_type="kpi",
                        entity_id=kpi.id,
                        value_type_id=vt.id,
                        consensus_status=consensus.get("status") if consensus else "no_data",
                        consensus_count=consensus.get("count") if consensus else 0,
                        calculation_type=config.calculation_type if hasattr(config, "calculation_type") else "manual",
                        computed_at=now,
                    )
                    db.session.add(entry)
                    values_cached += 1
                    continue

                try:
                    formatted_value = current_app.jinja_env.filters["format_value"](
                        consensus.get("value"), vt, config
                    )
                except Exception:
                    formatted_value = str(consensus.get("value"))

                try:
                    color = config.get_value_color(consensus.get("value")) if hasattr(config, "get_value_color") else None
                except Exception:
                    color = None

                # Target progress
                target_progress = None
                target_color = None
                if config.target_value is not None and consensus.get("value") is not None:
                    try:
                        target_dir = config.target_direction or "maximize"
                        tv = float(config.target_value)
                        cv = float(consensus.get("value"))
                        if target_dir == "minimize":
                            progress = int((tv / cv) * 100) if cv != 0 else 100
                        elif target_dir == "exact":
                            tol = tv * (config.target_tolerance_pct or 10) / 100
                            diff = abs(cv - tv)
                            progress = 100 if diff <= tol else max(0, int(100 - ((diff - tol) / tv * 100)))
                        else:
                            progress = int((cv / tv) * 100) if tv != 0 else 0
                        target_progress = progress
                        target_color = "#28a745" if progress >= 90 else "#ffc107" if progress >= 60 else "#dc3545"
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

                _list_val = consensus.get("value") if vt.is_list() else None

                # Comments tooltip
                _comment_lines = []
                if hasattr(config, "contributions"):
                    _comment_lines = [
                        f"{c.contributor_name}: {c.comment.strip()}"
                        for c in getattr(config, "contributions", [])
                        if c.comment and c.comment.strip()
                    ]
                comments_tooltip = ("\n\nComments:\n" + "\n".join(_comment_lines)) if _comment_lines else ""

                entry = RollupCacheEntry(
                    organization_id=sys_link.initiative.organization_id,
                    entity_type="kpi",
                    entity_id=kpi.id,
                    value_type_id=vt.id,
                    value=float(consensus["value"]) if consensus["value"] is not None else None,
                    formatted_value=formatted_value,
                    unit_label=vt.unit_label,
                    color=color,
                    consensus_status=consensus.get("status", "no_data"),
                    consensus_count=consensus.get("count", 0),
                    calculation_type=config.calculation_type if hasattr(config, "calculation_type") else "manual",
                    has_target=config.target_value is not None or bool(getattr(config, "target_list_value", None)),
                    target_value_formatted=current_app.jinja_env.filters["format_value"](config.target_value, vt, config) if config.target_value is not None else None,
                    target_date=config.target_date.strftime("%Y-%m-%d") if config.target_date else None,
                    target_direction=config.target_direction or "maximize" if config.target_value else None,
                    target_progress=target_progress,
                    target_color=target_color,
                    list_label=vt.get_list_option_label(_list_val) if _list_val else None,
                    list_color=vt.get_list_option_color(_list_val) if _list_val else None,
                    comments_tooltip=comments_tooltip,
                    computed_at=now,
                )
                db.session.add(entry)
                values_cached += 1

        # Walk the hierarchy (deduplicate shared entities)
        for space in spaces:
            if ("space", space.id) not in _seen:
                _seen.add(("space", space.id))
                cache_rollup("space", space.id, space, lambda vt_id: space.get_color_config(vt_id))
                entities_computed += 1

            for challenge in space.challenges:
                if ("challenge", challenge.id) not in _seen:
                    _seen.add(("challenge", challenge.id))
                    cache_rollup("challenge", challenge.id, challenge, lambda vt_id, ch=challenge: ch.get_color_config(vt_id))
                    entities_computed += 1

                for ci_link in challenge.initiative_links:
                    initiative = ci_link.initiative
                    if ("initiative", initiative.id) not in _seen:
                        _seen.add(("initiative", initiative.id))
                        cache_rollup("initiative", initiative.id, initiative, lambda vt_id, ini=initiative: ini.get_color_config(vt_id))
                        entities_computed += 1

                    for sys_link in initiative.system_links:
                        system = sys_link.system
                        if ("system", system.id) not in _seen:
                            _seen.add(("system", system.id))
                            cache_rollup("system", system.id, sys_link, lambda vt_id, sl=sys_link: sl.get_color_config(vt_id))
                            entities_computed += 1

                        for kpi in sys_link.kpis:
                            if not kpi.is_archived and ("kpi", kpi.id) not in _seen:
                                _seen.add(("kpi", kpi.id))
                                cache_kpi(kpi, sys_link)
                                entities_computed += 1

        # Mark cache as fresh
        from app.models.system_setting import SystemSetting
        SystemSetting.mark_rollup_cache_fresh(organization_id)

        db.session.commit()

        duration_ms = int((time.time() - start) * 1000)
        return {
            "entities_computed": entities_computed,
            "values_cached": values_cached,
            "duration_ms": duration_ms,
        }

    @staticmethod
    def _compute_formula(vt, rollup_dict, all_value_types):
        """Compute a formula value type from existing rollup values."""
        from simpleeval import simple_eval

        mode = vt.calculation_config.get("mode", "simple")

        if mode == "advanced":
            expression = vt.calculation_config.get("expression")
            if not expression:
                return None
            context = {}
            for other_vt in all_value_types:
                if other_vt.id in rollup_dict and not other_vt.is_formula():
                    var_name = other_vt.name.lower().replace(" ", "_").replace("-", "_")
                    val = rollup_dict[other_vt.id].get("value")
                    if val is not None:
                        context[var_name] = float(val)
            try:
                return simple_eval(expression, names=context)
            except Exception:
                return None
        else:
            # Simple mode
            operation = vt.calculation_config.get("operation")
            source_ids = vt.calculation_config.get("source_value_type_ids", [])
            if not operation or not source_ids:
                return None
            values = []
            for sid in source_ids:
                if sid in rollup_dict and rollup_dict[sid].get("value") is not None:
                    values.append(float(rollup_dict[sid]["value"]))
            if not values:
                return None
            if operation == "add":
                return sum(values)
            elif operation == "subtract":
                result = values[0]
                for v in values[1:]:
                    result -= v
                return result
            elif operation == "multiply":
                result = values[0]
                for v in values[1:]:
                    result *= v
                return result
            elif operation == "divide":
                if len(values) >= 2 and values[1] != 0:
                    return values[0] / values[1]
            return None

    @staticmethod
    def recompute_incremental(organization_id, changed_paths):
        """
        Incremental recompute — only recompute entities affected by the changed paths.
        Walks up from the changed entity to the root space.

        changed_paths: list of URL paths like ['/workspace/kpi/1915/value-type/235']
        """
        import re
        import time

        start = time.time()

        # Parse changed paths to find affected KPI/entity IDs
        affected_kpi_ids = set()
        full_recompute_needed = False

        for path in changed_paths:
            # /workspace/kpi/<id>/value-type/<id> → KPI contribution change
            m = re.search(r'/workspace/kpi/(\d+)/value-type/', path)
            if m:
                affected_kpi_ids.add(int(m.group(1)))
                continue
            # /org-admin/ → could be anything, need full recompute
            if '/org-admin/' in path:
                full_recompute_needed = True
                break

        if full_recompute_needed or not affected_kpi_ids:
            return RollupComputeService.recompute_organization(organization_id)

        # Find the chain for each affected KPI: KPI → System → Initiative → Challenge → Space
        from app.models import Challenge, ChallengeInitiativeLink, KPI, Space
        from app.models.system import InitiativeSystemLink

        entities_to_recompute = set()  # (entity_type, entity_id)

        for kpi_id in affected_kpi_ids:
            kpi = KPI.query.get(kpi_id)
            if not kpi:
                continue
            entities_to_recompute.add(("kpi", kpi.id))

            isl = kpi.initiative_system_link
            if not isl:
                continue
            entities_to_recompute.add(("system", isl.system.id))
            entities_to_recompute.add(("initiative", isl.initiative.id))

            ci = ChallengeInitiativeLink.query.filter_by(initiative_id=isl.initiative_id).first()
            if ci and ci.challenge:
                entities_to_recompute.add(("challenge", ci.challenge.id))
                if ci.challenge.space:
                    entities_to_recompute.add(("space", ci.challenge.space.id))

        if not entities_to_recompute:
            return RollupComputeService.recompute_organization(organization_id)

        # Delete only affected cache entries
        values_deleted = 0
        for etype, eid in entities_to_recompute:
            deleted = RollupCacheEntry.query.filter_by(
                organization_id=organization_id, entity_type=etype, entity_id=eid
            ).delete(synchronize_session=False)
            values_deleted += deleted
        db.session.commit()

        # Get value types for recomputation
        value_types = (
            ValueType.query.filter_by(organization_id=organization_id, is_active=True)
            .order_by(ValueType.display_order).all()
        )
        non_formula_vts = [vt for vt in value_types if not vt.is_formula()]
        now = datetime.utcnow()
        values_cached = 0

        # Recompute each affected entity
        for etype, eid in entities_to_recompute:
            if etype == "kpi":
                # Recompute KPI consensus
                kpi = KPI.query.get(eid)
                if not kpi or kpi.is_archived:
                    continue
                isl = kpi.initiative_system_link
                if not isl:
                    continue
                # Use the cache_kpi logic from recompute_organization
                for vt in value_types:
                    config = next((c for c in kpi.value_type_configs if c.value_type_id == vt.id), None)
                    if not config and not vt.is_formula():
                        continue
                    if not config:
                        from app.models import KPIValueTypeConfig
                        config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=vt.id, calculation_type="manual")
                        config.value_type = vt
                        config.kpi = kpi
                    try:
                        consensus = config.get_consensus_value()
                    except Exception:
                        continue
                    val = consensus.get("value") if consensus else None
                    formatted = None
                    color = None
                    if val is not None:
                        try:
                            formatted = current_app.jinja_env.filters["format_value"](val, vt, config)
                            color = config.get_value_color(val) if hasattr(config, "get_value_color") else None
                        except Exception:
                            formatted = str(val)
                    entry = RollupCacheEntry(
                        organization_id=organization_id, entity_type="kpi", entity_id=eid,
                        value_type_id=vt.id, value=float(val) if val is not None else None,
                        formatted_value=formatted, unit_label=vt.unit_label, color=color,
                        consensus_status=consensus.get("status") if consensus else "no_data",
                        consensus_count=consensus.get("count") if consensus else 0,
                        calculation_type=config.calculation_type if hasattr(config, "calculation_type") else "manual",
                        has_target=config.target_value is not None if hasattr(config, "target_value") else False,
                        computed_at=now,
                    )
                    db.session.add(entry)
                    values_cached += 1

            elif etype in ("system", "initiative", "challenge", "space"):
                # Recompute rollup for this entity
                if etype == "system":
                    isl = InitiativeSystemLink.query.filter(
                        InitiativeSystemLink.system_id == eid
                    ).first()
                    if not isl:
                        continue
                    entity_obj = isl
                    color_config_getter = lambda vt_id, sl=isl: sl.get_color_config(vt_id)
                elif etype == "initiative":
                    from app.models import Initiative
                    entity_obj = Initiative.query.get(eid)
                    if not entity_obj:
                        continue
                    color_config_getter = lambda vt_id, ini=entity_obj: ini.get_color_config(vt_id)
                elif etype == "challenge":
                    entity_obj = Challenge.query.get(eid)
                    if not entity_obj:
                        continue
                    color_config_getter = lambda vt_id, ch=entity_obj: ch.get_color_config(vt_id)
                elif etype == "space":
                    entity_obj = Space.query.get(eid)
                    if not entity_obj:
                        continue
                    color_config_getter = lambda vt_id, sp=entity_obj: sp.get_color_config(vt_id)

                # Compute rollups for non-formula VTs
                rollup_dict = {}
                for vt in non_formula_vts:
                    rollup_data = entity_obj.get_rollup_value(vt.id)
                    if rollup_data and rollup_data.get("value") is not None:
                        color_config = color_config_getter(vt.id)
                        try:
                            formatted = current_app.jinja_env.filters["format_value"](rollup_data["value"], vt, color_config)
                        except Exception:
                            formatted = str(rollup_data["value"])
                        try:
                            color = color_config.get_value_color(rollup_data["value"]) if color_config and hasattr(color_config, "get_value_color") else current_app.jinja_env.filters["default_value_color"](rollup_data["value"])
                        except Exception:
                            color = "#6c757d"
                        entry = RollupCacheEntry(
                            organization_id=organization_id, entity_type=etype, entity_id=eid,
                            value_type_id=vt.id, value=float(rollup_data["value"]),
                            formatted_value=formatted, unit_label=vt.unit_label,
                            color=color or "#6c757d", formula=rollup_data.get("formula"),
                            is_complete=rollup_data.get("is_complete", False),
                            count_total=rollup_data.get("count_total", 0),
                            count_included=rollup_data.get("count_included", 0),
                            list_label=vt.get_list_option_label(rollup_data["value"]) if vt.is_list() else None,
                            list_color=vt.get_list_option_color(rollup_data["value"]) if vt.is_list() else None,
                            computed_at=now,
                        )
                        db.session.add(entry)
                        rollup_dict[vt.id] = {"value": rollup_data["value"], "formatted_value": formatted}
                        values_cached += 1

                # Formula VTs
                for vt in value_types:
                    if not vt.is_formula() or vt.id in rollup_dict:
                        continue
                    try:
                        result = RollupComputeService._compute_formula(vt, rollup_dict, value_types)
                        if result is not None:
                            cc = color_config_getter(vt.id)
                            try:
                                fmt = current_app.jinja_env.filters["format_value"](result, vt, cc)
                            except Exception:
                                fmt = str(result)
                            entry = RollupCacheEntry(
                                organization_id=organization_id, entity_type=etype, entity_id=eid,
                                value_type_id=vt.id, value=float(result), formatted_value=fmt,
                                unit_label=vt.unit_label, formula="formula", is_complete=True,
                                computed_at=now,
                            )
                            db.session.add(entry)
                            values_cached += 1
                    except Exception:
                        pass

        # Mark fresh
        from app.models.system_setting import SystemSetting
        SystemSetting.mark_rollup_cache_fresh(organization_id)
        db.session.commit()

        duration_ms = int((time.time() - start) * 1000)
        return {
            "entities_computed": len(entities_to_recompute),
            "values_cached": values_cached,
            "values_deleted": values_deleted,
            "duration_ms": duration_ms,
            "mode": "incremental",
        }

    @staticmethod
    def get_cache_stats(organization_id):
        """Get cache statistics for an organization."""
        total = RollupCacheEntry.query.filter_by(organization_id=organization_id).count()
        if total == 0:
            return {"total": 0, "computed_at": None}
        latest = (
            RollupCacheEntry.query.filter_by(organization_id=organization_id)
            .order_by(RollupCacheEntry.computed_at.desc())
            .first()
        )
        return {
            "total": total,
            "computed_at": latest.computed_at if latest else None,
        }
