"""
Unified Presets API — one interface for all save/load features.
Delegates to existing models: UserFilterPreset, SavedSearch, SavedChart.
"""

import json
from functools import wraps

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required

from app.extensions import db
from app.models import SavedChart, SavedSearch, UserFilterPreset

bp = Blueprint("presets_api", __name__, url_prefix="/api")

VALID_FEATURES = {"workspace", "action_items", "search", "pivot"}


def organization_required(f):
    """Decorator to require organization context"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("organization_id") is None:
            return jsonify({"error": "Organization context required"}), 403
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/user-presets")
@login_required
@organization_required
def get_presets():
    """Get all presets for current user, filtered by feature."""
    feature = request.args.get("feature", "workspace")
    if feature not in VALID_FEATURES:
        return jsonify({"error": f"Invalid feature: {feature}"}), 400

    org_id = session.get("organization_id")

    if feature in ("workspace", "action_items"):
        presets = (
            UserFilterPreset.query.filter_by(
                user_id=current_user.id, organization_id=org_id, feature=feature
            )
            .order_by(UserFilterPreset.name)
            .all()
        )
        return jsonify([
            {
                "id": p.id,
                "name": p.name,
                "config": p.filters,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "is_active": False,
            }
            for p in presets
        ])

    elif feature == "search":
        searches = SavedSearch.get_user_searches(current_user.id, org_id)
        return jsonify([
            {
                "id": s.id,
                "name": s.name,
                "config": {"query": s.query, "filters": s.filters or {}},
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "is_active": s.is_default,
            }
            for s in searches
        ])

    elif feature == "pivot":
        charts = (
            SavedChart.query.filter_by(
                created_by_user_id=current_user.id, organization_id=org_id
            )
            .order_by(SavedChart.name)
            .all()
        )
        return jsonify([
            {
                "id": c.id,
                "name": c.name,
                "config": {
                    "year_start": c.year_start,
                    "year_end": c.year_end,
                    "view_type": c.view_type,
                    "chart_type": c.chart_type,
                    "space_id": c.space_id,
                    "value_type_id": c.value_type_id,
                    "period_filter": c.period_filter,
                    "config_ids_colors": c.get_config_colors(),
                    "description": c.description,
                },
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "is_active": False,
            }
            for c in charts
        ])

    return jsonify([])


@bp.route("/user-presets", methods=["POST"])
@login_required
@organization_required
def create_preset():
    """Create a new preset."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    feature = data.get("feature", "workspace")
    name = (data.get("name") or "").strip()
    config = data.get("config", {})

    if feature not in VALID_FEATURES:
        return jsonify({"error": f"Invalid feature: {feature}"}), 400
    if not name:
        return jsonify({"error": "Preset name is required"}), 400

    org_id = session.get("organization_id")

    if feature in ("workspace", "action_items"):
        existing = UserFilterPreset.query.filter_by(
            user_id=current_user.id, organization_id=org_id, feature=feature, name=name
        ).first()
        if existing:
            if not data.get("overwrite"):
                return jsonify({"error": f"A preset named '{name}' already exists", "exists": True}), 409
            # Overwrite existing preset
            existing.filters = config
            db.session.commit()
            return jsonify({"id": existing.id, "name": existing.name, "success": True}), 200

        preset = UserFilterPreset(
            user_id=current_user.id,
            organization_id=org_id,
            feature=feature,
            name=name,
            filters=config,
        )
        db.session.add(preset)
        db.session.commit()
        return jsonify({"id": preset.id, "name": preset.name, "success": True}), 201

    elif feature == "search":
        existing = SavedSearch.query.filter_by(
            user_id=current_user.id, organization_id=org_id, name=name
        ).first()
        if existing:
            if not data.get("overwrite"):
                return jsonify({"error": f"A preset named '{name}' already exists", "exists": True}), 409
            existing.query = config.get("query", "")
            existing.filters = config.get("filters", {})
            db.session.commit()
            return jsonify({"id": existing.id, "name": existing.name, "success": True}), 200

        preset = SavedSearch(
            user_id=current_user.id,
            organization_id=org_id,
            name=name,
            query=config.get("query", ""),
            filters=config.get("filters", {}),
        )
        db.session.add(preset)
        db.session.commit()
        return jsonify({"id": preset.id, "name": preset.name, "success": True}), 201

    elif feature == "pivot":
        existing = SavedChart.query.filter_by(
            created_by_user_id=current_user.id, organization_id=org_id, name=name
        ).first()
        if existing:
            if not data.get("overwrite"):
                return jsonify({"error": f"A preset named '{name}' already exists", "exists": True}), 409
            existing.description = config.get("description", "")
            existing.year_start = config.get("year_start", 2024)
            existing.year_end = config.get("year_end", 2026)
            existing.view_type = config.get("view_type", "monthly")
            existing.chart_type = config.get("chart_type", "line")
            existing.space_id = config.get("space_id")
            existing.value_type_id = config.get("value_type_id")
            existing.period_filter = config.get("period_filter")
            existing.config_ids_colors = json.dumps(config.get("config_ids_colors", {}))
            db.session.commit()
            return jsonify({"id": existing.id, "name": existing.name, "success": True}), 200

        preset = SavedChart(
            created_by_user_id=current_user.id,
            organization_id=org_id,
            name=name,
            description=config.get("description", ""),
            year_start=config.get("year_start", 2024),
            year_end=config.get("year_end", 2026),
            view_type=config.get("view_type", "monthly"),
            chart_type=config.get("chart_type", "line"),
            space_id=config.get("space_id"),
            value_type_id=config.get("value_type_id"),
            period_filter=config.get("period_filter"),
            config_ids_colors=json.dumps(config.get("config_ids_colors", {})),
        )
        db.session.add(preset)
        db.session.commit()
        return jsonify({"id": preset.id, "name": preset.name, "success": True}), 201

    return jsonify({"error": "Unhandled feature"}), 400


@bp.route("/user-presets/<int:preset_id>", methods=["DELETE"])
@login_required
@organization_required
def delete_preset(preset_id):
    """Delete a preset by ID."""
    feature = request.args.get("feature", "workspace")
    if feature not in VALID_FEATURES:
        return jsonify({"error": f"Invalid feature: {feature}"}), 400

    org_id = session.get("organization_id")

    if feature in ("workspace", "action_items"):
        preset = UserFilterPreset.query.get(preset_id)
        if not preset:
            return jsonify({"error": "Preset not found"}), 404
        if preset.user_id != current_user.id or preset.organization_id != org_id:
            return jsonify({"error": "Access denied"}), 403
        db.session.delete(preset)
        db.session.commit()
        return jsonify({"success": True})

    elif feature == "search":
        preset = SavedSearch.query.get(preset_id)
        if not preset:
            return jsonify({"error": "Preset not found"}), 404
        if preset.user_id != current_user.id or preset.organization_id != org_id:
            return jsonify({"error": "Access denied"}), 403
        db.session.delete(preset)
        db.session.commit()
        return jsonify({"success": True})

    elif feature == "pivot":
        preset = SavedChart.query.get(preset_id)
        if not preset:
            return jsonify({"error": "Preset not found"}), 404
        if preset.created_by_user_id != current_user.id or preset.organization_id != org_id:
            return jsonify({"error": "Access denied"}), 403
        db.session.delete(preset)
        db.session.commit()
        return jsonify({"success": True})

    return jsonify({"error": "Unhandled feature"}), 400
