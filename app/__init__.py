"""
CISK Navigator Application Factory
"""

import logging
import os

from flask import Flask

from app.config import config
from app.extensions import db, login_manager, migrate
from celery_app import make_celery

__version__ = "7.18.3"

# Global Celery instance (will be initialized in create_app)
celery = None

# Enable INFO level logging for aggregation service
logging.basicConfig(level=logging.INFO)
logging.getLogger("app.services.aggregation_service").setLevel(logging.INFO)


def create_app(config_name=None):
    """
    Application factory pattern.

    Creates and configures the Flask application.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Initialize Celery
    global celery
    try:
        celery = make_celery(app)
        app.celery = celery
        app.config["CELERY_ENABLED"] = True
    except Exception as e:
        # Celery initialization failed (Redis not available)
        print(f"Warning: Celery initialization failed: {e}")
        print("Test runner feature will be disabled")
        celery = None
        app.celery = None
        app.config["CELERY_ENABLED"] = False

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Enable SQLite foreign keys
    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:

        @app.before_request
        def _enable_foreign_keys():
            from sqlalchemy import event
            from sqlalchemy.engine import Engine

            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User

        try:
            return User.query.get(int(user_id))
        except Exception:
            # During migrations, schema might not match - return None to force re-login
            return None

    # Register blueprints
    from app.routes import (
        action_items,
        analytics,
        auth,
        beta,
        entity_links,
        executive,
        geography,
        global_admin,
        logo,
        map_dashboard,
        organization_admin,
        presets_api,
        stakeholders,
        super_admin,
        workspace,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(super_admin.bp)
    app.register_blueprint(global_admin.bp)
    app.register_blueprint(organization_admin.bp)
    app.register_blueprint(geography.bp)
    app.register_blueprint(workspace.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(executive.bp)
    app.register_blueprint(map_dashboard.bp)
    app.register_blueprint(logo.bp)
    app.register_blueprint(entity_links.bp)
    app.register_blueprint(action_items.bp)  # Action items and memos
    app.register_blueprint(stakeholders.bp)  # Stakeholder mapping
    app.register_blueprint(beta.bp)  # Beta feature prototypes
    app.register_blueprint(presets_api.bp)  # Unified presets API

    # Register test error routes (REMOVE IN PRODUCTION)
    if app.config.get("FLASK_ENV") == "development":
        from app.routes import test_errors

        app.register_blueprint(test_errors.bp)

    # Clear stale session org_id if the org no longer exists in the DB
    @app.before_request
    def _clear_stale_session_org():
        from flask import request, session

        if request.endpoint in ("static", None):
            return None
        org_id = session.get("organization_id")
        if not org_id:
            return None
        from app.models.organization import Organization

        if not Organization.query.get(org_id):
            session.pop("organization_id", None)
            session.pop("organization_name", None)
            session.pop("organization_logo", None)
        return None

    # Maintenance mode check (global)
    @app.before_request
    def check_maintenance_mode():
        """Block write operations during maintenance mode (except for super admins)"""
        from flask import flash, redirect, request, url_for
        from flask_login import current_user

        from app.models import SystemSetting

        # Skip check for static files and certain routes
        if request.endpoint in ["static", "auth.login", "auth.logout", None]:
            return None

        # Check if maintenance mode is active
        if SystemSetting.is_maintenance_mode():
            # Super admins can bypass maintenance mode
            if current_user.is_authenticated and current_user.is_super_admin:
                return None

            # Block write operations (POST, PUT, DELETE, PATCH)
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                flash(
                    "[MAINTENANCE] System is in maintenance mode. Write operations are temporarily disabled.",
                    "warning",
                )
                # Try to redirect to referer or dashboard
                return redirect(request.referrer or url_for("workspace.dashboard"))

        return None

    # Beta access is now opt-in via /beta landing page
    # No auto-redirect - beta testers see "Beta" menu item in nav bar

    # Action Items - Quality Dashboard
    @app.route("/action-items")
    def action_items():
        """
        Quality Dashboard - Lists all incomplete/problematic items that need attention.

        Shows:
        - Initiatives with no consensus
        - Initiatives with incomplete forms
        - Spaces without SWOT analysis
        - Systems without KPIs
        - KPIs without governance bodies
        """
        from flask import redirect, render_template, session, url_for
        from flask_login import current_user
        from flask_wtf.csrf import generate_csrf

        from app.services.action_items_service import ActionItemsService

        # Require login
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        org_id = session.get("organization_id")
        org_name = session.get("organization_name")

        # Get action items from centralized service
        action_items_data = ActionItemsService.get_action_items_details(org_id)

        return render_template(
            "workspace/action_items.html",
            org_name=org_name,
            initiatives_no_consensus=action_items_data["initiatives_no_consensus"],
            initiatives_incomplete=action_items_data["initiatives_incomplete"],
            spaces_no_swot=action_items_data["spaces_no_swot"],
            systems_without_kpis=action_items_data["systems_without_kpis"],
            kpis_without_gb=action_items_data["kpis_without_gb"],
            total_issues=action_items_data["total"],
            csrf_token=generate_csrf,
        )

    # Root route - redirect to login or dashboard
    @app.route("/")
    def index():
        """Redirect root URL to appropriate page based on authentication status"""
        from flask import redirect, session, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            # If user has organization context, go to dashboard
            if session.get("organization_id"):
                return redirect(url_for("workspace.dashboard"))
            # If authenticated but no org, go to org selection
            return redirect(url_for("auth.login"))
        # Not authenticated, go to login
        return redirect(url_for("auth.login"))

    # Disable caching in development
    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    # Context processor - inject maintenance_mode into all templates
    @app.context_processor
    def inject_maintenance_mode():
        """Make maintenance_mode, beta_enabled, app_version and csrf_token available to all templates"""
        from app.models import SystemSetting
        from flask_wtf.csrf import generate_csrf

        return {
            "maintenance_mode": SystemSetting.is_maintenance_mode(),
            "beta_enabled": SystemSetting.is_beta_enabled(),
            "tree_cache_enabled": SystemSetting.is_tree_cache_enabled(),
            "precompute_rollups_enabled": SystemSetting.is_precompute_rollups_enabled(),
            "app_version": __version__,
            "csrf_token": generate_csrf,
        }

    # Context processor - inject workspace labels and active profile for navbar
    @app.context_processor
    def inject_workspace_labels():
        """Make current user's workspace labels and active profile available."""
        from flask_login import current_user
        if not current_user.is_authenticated:
            return {"workspace_labels_map": {}, "user_labels": [], "active_profile": None, "active_profile_label_ids": []}
        from app.models import UserWorkspaceProfile, WorkspaceLabel
        labels = WorkspaceLabel.query.filter_by(user_id=current_user.id).order_by(WorkspaceLabel.name).all()
        labels_map = {l.id: {"name": l.name, "color": l.color} for l in labels}
        active_profile = UserWorkspaceProfile.query.filter_by(user_id=current_user.id, is_active=True).first()
        active_label_ids = active_profile.label_ids if active_profile else []
        return {
            "workspace_labels_map": labels_map,
            "user_labels": labels,
            "active_profile": active_profile,
            "active_profile_label_ids": active_label_ids,
        }

    # Context processor - inject entity defaults for branding
    @app.context_processor
    def inject_entity_defaults():
        """Make entity type defaults available to all templates for branding (includes logo URLs)"""
        import base64

        from flask import session

        from app.models import EntityTypeDefault

        organization_id = session.get("organization_id")

        if organization_id:
            # Query DB directly to include logo data
            defaults_raw = EntityTypeDefault.query.filter_by(organization_id=organization_id).all()
            if defaults_raw:
                entity_defaults = {}
                for d in defaults_raw:
                    logo_url = None
                    if d.default_logo_data and d.default_logo_mime_type:
                        logo_url = f"data:{d.default_logo_mime_type};base64,{base64.b64encode(d.default_logo_data).decode('utf-8')}"
                    entity_defaults[d.entity_type] = {
                        "color": d.default_color,
                        "icon": d.default_icon,
                        "logo": logo_url,
                    }
            else:
                entity_defaults = EntityTypeDefault.get_hardcoded_defaults()
        else:
            entity_defaults = EntityTypeDefault.get_hardcoded_defaults()

        return {"entity_defaults": entity_defaults}

    @app.context_processor
    def inject_impact_levels():
        """Make impact levels available to all templates"""
        from flask import session

        from app.models import ImpactLevel, Organization

        org_id = session.get("organization_id")
        if org_id:
            levels = ImpactLevel.get_org_levels(org_id)
            org = Organization.query.get(org_id) if org_id else None
            decision_tags = (org.decision_tags if org and org.decision_tags else
                             ["scope", "budget", "timeline", "resource", "technical", "governance", "other"])
            strategy_enabled = org.strategy_enabled if org else False
            if levels:
                return {"impact_levels_config": levels, "decision_tags": decision_tags, "strategy_enabled": strategy_enabled}
            return {"impact_levels_config": {}, "decision_tags": decision_tags, "strategy_enabled": strategy_enabled}
        return {"impact_levels_config": {}, "decision_tags": [], "strategy_enabled": False}

    @app.context_processor
    def inject_assistant():
        """Generate contextual assistant hints based on current page, role, and data state."""
        from flask import request, session
        from flask_login import current_user

        if not current_user.is_authenticated or not getattr(current_user, "assistant_enabled", False):
            return {"assistant_hints": [], "assistant_location": None}

        org_id = session.get("organization_id")
        path = request.path
        hints = []
        location = None

        # Helper to build hint dicts concisely
        def H(htype, icon, text, action_url=None, action_label=None, highlight=None):
            return {"type": htype, "icon": icon, "text": text, "action_url": action_url, "action_label": action_label, "highlight": highlight}

        try:
            is_admin = current_user.is_global_admin or current_user.is_super_admin or (current_user.is_org_admin(org_id) if org_id else False)

            if "/workspace" in path and "/org-admin" not in path:
                # ── WORKSPACE HOME ──
                if "/workspace/dashboard" in path:
                    location = {"page": "Workspace Home", "description": "Your workspace overview — stats, quick actions, and recent activity."}
                    if org_id:
                        from app.models import Space
                        home_spaces = Space.query.filter_by(organization_id=org_id).count()
                        if home_spaces == 0:
                            hints.append(H("action", "🏠", "Click the CISK logo (top left) to open your workspace and start building your hierarchy.", "/workspace/", "Open Workspace", highlight=".navbar-brand"))
                        else:
                            hints.append(H("action", "🏠", "Click the CISK logo (top left) to open your workspace and continue working.", "/workspace/", "Open Workspace", highlight=".navbar-brand"))
                    if is_admin:
                        hints.append(H("tip", "👥", "Invite team members from Instance Admin > Users to collaborate on this workspace."))

                # ── WORKSPACE TREE ──
                elif path.endswith("/workspace") or path.endswith("/workspace/"):
                    location = {"page": "CISK Workspace", "description": "The main tree view — your full hierarchy of Spaces, Challenges, Initiatives, Systems, and KPIs."}
                    if org_id:
                        from app.models import Space, Challenge, Initiative, KPI, ValueType
                        from app.models.system import InitiativeSystemLink
                        spaces = Space.query.filter_by(organization_id=org_id).count()
                        challenges = Challenge.query.filter_by(organization_id=org_id).count()
                        initiatives = Initiative.query.filter_by(organization_id=org_id).count()
                        value_types = ValueType.query.filter_by(organization_id=org_id).count()
                        kpis = db.session.query(KPI).join(InitiativeSystemLink).join(Initiative).filter(Initiative.organization_id == org_id).count()

                        if spaces == 0:
                            from app.models import Organization as Org
                            org_obj = Org.query.get(org_id)
                            porters_filled, porters_total, porters_status = org_obj.get_porters_completion() if org_obj else (0, 5, "empty")
                            if porters_status != "complete":
                                hints.append(H("action", "🔍", "Start with a competitive analysis! Click your workspace name in the grid, then click the Porter's Five Forces chip to map the forces shaping your topic.", "/org-admin/porters", "Open Porter's Analysis", highlight=".ws-header-cell"))
                            hints.append(H("action", "🚀", "Create your first Space to begin building your hierarchy.", "/org-admin/spaces/create", "Create Space"))
                        elif challenges == 0:
                            s = "space" if spaces == 1 else "spaces"
                            hints.append(H("action", "🎯", f"{spaces} {s} created. Now add Challenges — click Edit Mode, then + on a space. The tree will grow as you build out the hierarchy.", highlight="#wsEditModeBtn"))
                            hints.append(H("info", "💡", "Need ideas for challenges? Check the documentation for examples.", "/workspace/documentation#naming-challenges", "See examples"))
                        elif initiatives == 0:
                            c = "challenge" if challenges == 1 else "challenges"
                            hints.append(H("action", "🚀", f"{challenges} {c} defined. Create Initiatives to address them. Use Edit Mode.", highlight="#wsEditModeBtn"))
                            hints.append(H("info", "💡", "Need ideas for initiatives? Check the documentation for examples.", "/workspace/documentation#naming-initiatives", "See examples"))
                        elif value_types == 0 and is_admin:
                            hints.append(H("action", "🔎", "Great structure! Now define your Evidence Lenses (Value Types) — the perspectives through which you measure success. Click the Value Types tile on the Workspace Home.", "/org-admin/value-types", "Create Value Types"))
                            hints.append(H("info", "💡", "Not sure what to measure? Check the documentation for examples.", "/workspace/documentation#naming-value-types", "See examples"))
                        elif kpis == 0:
                            hints.append(H("action", "📊", "Structure ready! Add Systems, then KPIs to start measuring. Click Edit Mode, then + on an initiative.", highlight="#wsEditModeBtn"))
                            hints.append(H("info", "💡", "Need ideas for systems? Check the documentation for examples.", "/workspace/documentation#naming-systems", "See examples"))
                        else:
                            hints.append(H("tip", "✅", f"{spaces} spaces, {challenges} challenges, {initiatives} initiatives, {kpis} KPIs."))
                            hints.append(H("tip", "📊", "Click any KPI cell to contribute data or view details."))

                        from app.models import ImpactLevel
                        if not ImpactLevel.get_org_levels(org_id) and is_admin:
                            hints.append(H("info", "⚡", "Impact scale not configured. Set it up to enable prioritization.", "/org-admin/impact-levels", "Configure Impact"))

                        hints.append(H("tip", "🌱", "Detail level: 🌱 tree only → 🌲 with values → 🎄 full detail + impact column.", highlight="#wsTreeBtn"))
                        hints.append(H("tip", "☆", "Impact filter: cycle ☆→○→★→★★→★★★ to show entities by importance.", highlight="#wsImpactBtn"))
                        hints.append(H("tip", "🔄", "Orange refresh button = data changed. Click to reload fresh values.", highlight="#wsRefreshBtn"))
                        hints.append(H("tip", "👁️", "View menu: toggle Relevant Branches to prune the tree to only branches with data in visible columns."))
                        hints.append(H("tip", "🏷️", "Organise workspaces with labels and profiles from your Profile page. Profiles filter the Workspaces menu."))
                        hints.append(H("tip", "🐛", "Found a bug or have an idea? Use Help → Report a Bug or Request Enhancement."))
                        if is_admin:
                            hints.append(H("info", "✏️", "Edit Mode lets you add/remove/reorder entities and drag columns.", highlight="#wsEditModeBtn"))
                            hints.append(H("tip", "💾", "Save/load filter presets with My Presets.", highlight=".preset-bar"))

                # ── KPI CONTRIBUTION ──
                elif "/workspace/kpi/" in path:
                    location = {"page": "KPI Contribution", "description": "Enter or edit values for this KPI. Consensus is computed automatically from all contributors."}
                    hints.append(H("tip", "📝", "Type a contributor name — autocomplete suggests existing names to prevent typos.", highlight="#contributor_name"))
                    hints.append(H("tip", "✏️", "Click the pencil icon on any row to edit inline — no scrolling needed.", highlight=".btn-outline-primary"))
                    hints.append(H("info", "🤝", "If multiple contributors enter values, the system computes consensus (strong/weak/no consensus)."))
                    hints.append(H("tip", "🗑️", "Delete a contribution to remove it from the consensus calculation.", highlight=".btn-outline-danger"))

                # ── DECISION REGISTER ──
                elif "/workspace/decision-register" in path:
                    location = {"page": "Decision Register", "description": "Record and track decisions. Mention entities to link decisions to your CISK structure."}
                    hints.append(H("action", "➕", "Click New Decision to record one.", highlight=".btn-light"))
                    hints.append(H("tip", "🏷️", "Click tags to categorize (scope, budget, timeline...). Multiple tags allowed."))
                    hints.append(H("tip", "🔗", "Type in Entity Mentions to link to initiatives, systems, KPIs, or stakeholders."))
                    hints.append(H("tip", "📝", "Decision text supports Markdown: **bold**, - lists, ## headings."))
                    hints.append(H("tip", "🌱", "Use the tree icon to show/hide columns: 🌱 minimal → 🌲 + who/tags → 🎄 full detail.", highlight="#drDetailBtn"))
                    hints.append(H("tip", "💾", "Save filter presets to quickly recall your preferred view.", highlight=".preset-bar"))

                # ── KPI DASHBOARD ──
                elif "/workspace/kpi-dashboard" in path:
                    location = {"page": "KPI Dashboard", "description": "Performance overview — target progress, impact, consensus status for all KPIs."}
                    hints.append(H("tip", "🎯", "Green/amber/red progress bars show target achievement. Click column headers to understand.", highlight=".kd-target-bar"))
                    hints.append(H("tip", "☆", "Star filter: show only KPIs under high-importance entities.", highlight="#kdImpactBtn"))
                    hints.append(H("tip", "🔽", "Open filters to narrow by governance body or target status.", highlight="[title='Filters']"))
                    hints.append(H("tip", "🌱", "Detail level controls which columns are visible.", highlight="#kdDetailBtn"))

                # ── CHALLENGES DASHBOARD ──
                elif "/workspace/challenges-dashboard" in path:
                    location = {"page": "Challenges Dashboard", "description": "Strategic alignment — how challenges are covered by initiatives and their execution health."}
                    hints.append(H("tip", "🔴", "RAG dots show each initiative's execution status under the challenge."))
                    hints.append(H("tip", "📊", "Coverage bar: what % of initiatives have KPIs assigned."))
                    hints.append(H("tip", "☆", "Filter by impact to focus on high-priority challenges.", highlight="#cdImpactBtn"))

                # ── SYSTEMS DASHBOARD ──
                elif "/workspace/systems-dashboard" in path:
                    location = {"page": "Systems Dashboard", "description": "System health, reuse across initiatives, KPI coverage, and portal links."}
                    hints.append(H("tip", "🔗", "Systems shared across multiple initiatives show a reuse badge (e.g. '3x')."))
                    hints.append(H("tip", "🧭", "Portal chips link to other CISK workspaces — click to open."))
                    hints.append(H("tip", "🔽", "Filter by Shared, Portal, No KPIs, or With KPIs.", highlight="[title='Filters']"))

                # ── IMPACTS DASHBOARD ──
                elif "/workspace/impacts-dashboard" in path:
                    location = {"page": "Impacts Dashboard", "description": "Impact assessment coverage, distribution, and gap analysis across your hierarchy."}
                    hints.append(H("tip", "🎯", "Coverage rings show what % of entities have impact assessed."))
                    hints.append(H("tip", "🟩", "Heatmap: each cell = one entity. Color = true importance. Grey = assessed but chain incomplete. Light = not set.", highlight=".id-heatmap"))
                    hints.append(H("info", "📋", "Gaps table lists entities missing impact — fix them to complete the chain.", highlight=".id-gaps"))
                    hints.append(H("tip", "🌱", "🌱 = rings + coverage → 🌲 + heatmap + method → 🎄 + gaps table.", highlight="#idDetailBtn"))

                # ── VISIBILITY DASHBOARD ──
                elif "/workspace/visibility-dashboard" in path:
                    location = {"page": "Visibility Dashboard", "description": "Public vs private content — understand what's shared and what's restricted."}
                    hints.append(H("tip", "🟢", "Green ring = shared items visible to all. Red = private, owner-only."))
                    hints.append(H("tip", "🔒", "Private items table shows exactly what's hidden and who owns it."))

                # ── GOVERNANCE DASHBOARD ──
                elif "/workspace/governance" in path:
                    location = {"page": "Governance Dashboard", "description": "Per governance body: KPIs, actions, decisions, and initiatives they oversee."}
                    hints.append(H("tip", "🏛️", "Use the GB selector to switch between governance bodies."))
                    hints.append(H("tip", "🌱", "Detail level: 🌱 KPIs only → 🌲 + actions/decisions → 🎄 + initiatives.", highlight="#gbdDetailBtn"))

                # ── STRATEGY ──
                elif "/workspace/strategy" in path:
                    location = {"page": "Strategic Pillars", "description": "Your organization's guiding themes. Each pillar has an icon, color, and bullet points."}
                    if is_admin:
                        hints.append(H("info", "✏️", "Click Edit to modify pillars — drag to reorder, click icons to change."))

                # ── THEORY ──
                elif "/workspace/theory" in path:
                    location = {"page": "CISK Theory", "description": "The theoretical foundation — how entities, values, consensus, and impacts work together."}
                    hints.append(H("tip", "📖", "Scroll through sections to understand the CISK framework."))

                # ── DOCUMENTATION ──
                elif "/workspace/documentation" in path:
                    location = {"page": "Documentation", "description": "Complete platform guide — from getting started to advanced calculations."}
                    hints.append(H("tip", "🔍", "Use the sidebar search to quickly find a topic."))
                    hints.append(H("tip", "📖", "Use the sidebar navigation to jump between sections."))

                # ── IMPACT DOCS ──
                elif "/workspace/impact-docs" in path:
                    location = {"page": "Impact Calculation Docs", "description": "The 5 compounding methods: Simple Product, Geometric Mean, Toyota QFD, Toyota Weighted (DS/Full)."}
                    hints.append(H("tip", "📊", "Comparison table at the bottom shows how each method scores the same chains differently."))

                # ── INITIATIVE REVIEW ──
                elif "/org-admin/initiatives/" in path and "/form" in path:
                    location = {"page": "Initiative Review", "description": "Detailed initiative view with execution tracking, KPIs, actions, and decisions."}
                    hints.append(H("tip", "🔄", "Form tab = edit details. Execution tab = RAG status, progress updates, decisions.", highlight=".initiative-tab-btn"))
                    hints.append(H("tip", "🌱", "Detail level: 🌱 minimal → 🌲 key context → 🎄 everything.", highlight="#detailModeBtn"))
                    hints.append(H("tip", "◀▶", "Use prev/next arrows to navigate between initiatives without going back."))

            # ── ACTION REGISTER ──
            elif "/toolbox/actions" in path:
                location = {"page": "Action Register", "description": "Track action items and memos across the organization."}
                hints.append(H("action", "➕", "Click New Item to create an action or memo.", highlight=".btn-light.fw-semibold"))
                hints.append(H("tip", "📌", "Use @mentions in descriptions to link entities and stakeholders."))
                hints.append(H("tip", "📝", "Descriptions support Markdown: **bold**, - bullet list, ## heading, > quote."))
                hints.append(H("tip", "🌱", "Detail level: 🌱 title/status → 🌲 + dates/owner → 🎄 + GB/type/links.", highlight="#actionDetailBtn"))
                hints.append(H("tip", "☆", "Star filter: show only actions linked to high-importance entities.", highlight="#actImpactBtn"))
                hints.append(H("tip", "🔽", "Open filters for status, priority, governance body, and more.", highlight="#filters-toggle-btn"))

            # ── MAP DASHBOARD ──
            elif path.startswith("/map"):
                location = {"page": "Geographic KPI Distribution", "description": "World map showing KPI locations, country colouring, and site markers."}
                hints.append(H("tip", "🗺️", "Click on a country or marker to explore KPIs at that location."))
                hints.append(H("tip", "📍", "Configure geography (regions, countries, sites) from the Workspace Home tiles."))

            # ── STAKEHOLDERS ──
            elif "/stakeholders" in path:
                if "/network" in path or path.endswith("/stakeholders") or "organization" in path:
                    location = {"page": "Stakeholder Analysis", "description": "Map the people and roles involved in your workspace — network view, influence, and relationships."}
                    hints.append(H("tip", "👤", "Add stakeholders and define their relationships to build your network map."))
                    hints.append(H("tip", "🗺️", "Use maps to create power-vs-interest matrices for stakeholder analysis."))
                elif "/matrix" in path:
                    location = {"page": "Stakeholder Matrix", "description": "Power-vs-interest matrix for stakeholder prioritisation."}
                elif "/list" in path:
                    location = {"page": "Stakeholder List", "description": "All stakeholders in a table view."}
                else:
                    location = {"page": "Stakeholders", "description": "Manage stakeholders, relationships, and analysis maps."}

            # ── ORG ADMIN ──
            elif "/org-admin" in path:
                if path.endswith("/org-admin") or path.endswith("/org-admin/"):
                    location = {"page": "Workspace Administration", "description": "Central hub for configuring your workspace: branding, impact, geography, value types, strategy."}
                    hints.append(H("tip", "🎨", "Branding: customize colors, icons, and logos for all entity types."))
                    hints.append(H("tip", "⚡", "Impact Scale: configure the 3-level assessment and compounding method."))
                    hints.append(H("tip", "📊", "Value Types: define what gets measured — each becomes a workspace column."))
                elif "/impact-levels" in path:
                    location = {"page": "Impact Scale Configuration", "description": "Configure symbols, weights, colors for 3 impact levels, and choose a compounding method."}
                    hints.append(H("tip", "🎚️", "Choose a compounding method: Geometric Mean (balanced), Toyota QFD (sharp), or Toyota Weighted (amplified)."))
                    hints.append(H("info", "📖", "See formulas and comparison tables in the Documentation.", "/workspace/documentation#impact", "Open Documentation"))
                    hints.append(H("action", "🏠", "Done configuring? Click the CISK logo (top left) to go back to your workspace and switch to 🎄 Full Detail to see impact levels in the tree.", "/workspace/", "Go to Workspace", highlight=".navbar-brand"))
                elif "/strategy" in path:
                    location = {"page": "Strategic Pillars Editor", "description": "Define pillars with icons, accent colors, and bullet-point descriptions. Drag to reorder."}
                elif "/value-types" in path:
                    location = {"page": "Value Types", "description": "The lenses through which you measure success — each value type becomes a column in the workspace."}
                    hints.append(H("tip", "➕", "Add more value types with + New Value Type. Start with 2-4 — you can always add more later.", highlight=".btn-primary"))
                    hints.append(H("tip", "🔢", "Types available: numeric (cost, count), qualitative (risk, sentiment, level), list (custom choices), and formula (computed)."))
                    hints.append(H("info", "💡", "Not sure what to measure? Check the documentation for examples.", "/workspace/documentation#naming-value-types", "See examples"))
                    hints.append(H("action", "🏠", "Done? Click the CISK logo (top left) to go back to your workspace.", "/workspace/", "Go to Workspace", highlight=".navbar-brand"))
                elif "/kpis/create" in path or "/kpis/" in path:
                    location = {"page": "KPI Form", "description": "Configure a KPI: value types, governance bodies, targets, and calculation method."}
                elif "/systems" in path and "/create" in path:
                    location = {"page": "Create System", "description": "Define a new reusable system, process, or tool."}
                    hints.append(H("info", "💡", "Not sure what to call your system? Check the documentation for examples of tools, platforms, and processes.", "/workspace/documentation#naming-systems", "See examples"))
                elif "/systems" in path and "/edit" in path:
                    location = {"page": "Edit System", "description": "Update this system, process, or tool."}
                    hints.append(H("info", "💡", "Check the documentation for examples of tools, platforms, and processes.", "/workspace/documentation#naming-systems", "See examples"))
                elif "/initiatives" in path and "/form" in path:
                    location = {"page": "Initiative Review", "description": "Detailed initiative view with execution tracking, KPIs, actions, and decisions."}
                elif "/initiatives" in path and "/create" in path:
                    location = {"page": "Create Initiative", "description": "Define a new initiative: mission, deliverables, team, and success criteria."}
                    hints.append(H("info", "💡", "Not sure how to name your initiative? Check the documentation for examples of concrete, actionable projects.", "/workspace/documentation#naming-initiatives", "See examples"))
                elif "/initiatives" in path and "/edit" in path:
                    location = {"page": "Edit Initiative", "description": "Update this initiative: mission, deliverables, team, and success criteria."}
                    hints.append(H("info", "💡", "Check the documentation for initiative naming examples.", "/workspace/documentation#naming-initiatives", "See examples"))
                elif "/challenges" in path and "/rollup-config" in path:
                    location = {"page": "Rollup Configuration", "description": "Configure how values aggregate for this challenge."}
                elif "/challenges" in path and "/create" in path:
                    location = {"page": "Create Challenge", "description": "Define a key objective within a space."}
                    hints.append(H("info", "💡", "Not sure how to name your challenge? Check the documentation for examples across different domains.", "/workspace/documentation#naming-challenges", "See examples"))
                elif "/challenges" in path and "/edit" in path:
                    location = {"page": "Edit Challenge", "description": "Update this challenge's details, links, and impact level."}
                    hints.append(H("info", "💡", "Need inspiration? Check challenge naming examples in the documentation.", "/workspace/documentation#naming-challenges", "See examples"))
                elif "/porters" in path:
                    location = {"page": "Porter's Five Forces", "description": "Analyse the competitive forces shaping your topic: new entrants, suppliers, buyers, substitutes, and rivalry."}
                    hints.append(H("tip", "📝", "Fill in each force with bullet points or paragraphs to structure your analysis."))
                    hints.append(H("action", "🏠", "Done? Click the CISK logo (top left) to go back to your workspace.", "/workspace/", "Go to Workspace", highlight=".navbar-brand"))
                elif "/spaces" in path and "/swot" in path:
                    location = {"page": "SWOT Analysis", "description": "Map Strengths, Weaknesses, Opportunities, and Threats for this space."}
                elif "/spaces" in path:
                    location = {"page": "Spaces", "description": "Create, edit, and organise the top-level areas of your workspace."}
                    hints.append(H("info", "💡", "Not sure how to name your spaces? Check the documentation for examples across different domains.", "/workspace/documentation#naming-spaces", "See examples"))
                elif "/link-health" in path:
                    location = {"page": "Link Health", "description": "Check the status of all URLs attached to entities in this workspace."}
                elif "/links" in path:
                    location = {"page": "Workspace Links", "description": "Manage URLs and resources attached to this workspace."}
                elif "/onboarding" in path:
                    location = {"page": "Onboarding", "description": "Step-by-step guide to set up your workspace."}
                elif "/logo-manager" in path:
                    location = {"page": "Logo Manager", "description": "Upload and manage logos for each entity type."}
                elif "/branding" in path:
                    location = {"page": "Branding Manager", "description": "Set default colors, icons, and logos for each entity type (space, challenge, initiative, system, KPI)."}
                elif "/decision-tags" in path:
                    location = {"page": "Decision Tags", "description": "Configure the tag categories available in the Decision Register."}
                elif "/geography" in path:
                    location = {"page": "Geography", "description": "Configure regions, countries, and sites for location-based tracking."}
                elif "/governance" in path:
                    location = {"page": "Governance Bodies", "description": "Create and manage the committees, boards, or teams that oversee KPIs."}
                elif "/rollup" in path:
                    location = {"page": "Rollup Rules", "description": "Configure how values aggregate through the hierarchy."}
                else:
                    location = {"page": "Workspace Administration", "description": "Configure and manage your workspace settings."}

            # ── INSTANCE ADMIN ──
            elif "/global-admin" in path:
                location = {"page": "Instance Administration", "description": "Manage workspaces, users, backup/restore, and system health."}
                hints.append(H("tip", "🏢", "Create and manage workspaces from the Workspaces tab."))
                hints.append(H("tip", "💾", "Use Backup & Restore for full JSON exports with user/GB mapping on import."))

            elif "/super-admin" in path:
                location = {"page": "Super Administration", "description": "System-wide settings: maintenance mode, SSO, beta, pre-compute rollups, tree cache."}
                hints.append(H("tip", "⚡", "Pre-compute rollups: 22x faster workspace loads. Toggle ON and recompute per org.", highlight="#precomputeToggle"))
                hints.append(H("tip", "💾", "Tree cache: stores workspace data in browser localStorage for instant loads.", highlight="#treeCacheToggle"))

            if not location:
                location = {"page": "CISK Navigator", "description": "Navigate using the menu bar above."}

        except Exception:
            pass

        return {"assistant_hints": hints, "assistant_location": location}

    # Mark rollup cache stale on data-changing requests
    @app.after_request
    def mark_rollup_cache_stale_on_change(response):
        """Mark rollup cache as stale when data-modifying requests succeed.

        Only marks stale for operations that affect rollup values or structure.
        Name/description edits, branding, settings changes do NOT trigger recompute.
        """
        from flask import request as _req
        if _req.method in ("POST", "PUT", "DELETE") and response.status_code < 400:
            path = _req.path
            # Only mark stale for operations that directly change rollup values:
            # - KPI value contributions
            # - Impact level changes
            # - Rollup config changes
            # Skip everything else (entity CRUD, branding, settings, etc.)
            # Entity deletes: tree refreshes from DB; parent rollups stay
            # slightly stale until next value change or manual recompute.
            _affects_rollups = (
                "/workspace/kpi/" in path
                or "/workspace/api/kpi/" in path
                or "/workspace/api/impact" in path
                or "/workspace/contribute" in path
                or ("/org-admin/" in path and "/rollup" in path)
            )
            if _affects_rollups:
                from flask import session as _sess
                org_id = _sess.get("organization_id")
                if org_id:
                    try:
                        from app.models import SystemSetting
                        SystemSetting.mark_rollup_cache_stale(org_id, changed_path=path)
                        db.session.commit()
                        import logging as _plog; _ptl = _plog.getLogger("perf_trace"); _ptl.info(f"[PERF_TRACE] Marked rollup cache STALE for org={org_id} (path={path})")  # [PERF_TRACE]
                    except Exception:
                        pass  # Don't break the response if stale marking fails
            elif "/org-admin/" in path:
                import logging as _plog2; _plog2.getLogger("perf_trace").info(f"[PERF_TRACE] SKIP stale mark — edit-only path: {path}")  # [PERF_TRACE]
        return response

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 - Page Not Found errors"""
        from flask import render_template

        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 - Internal Server errors"""
        from flask import render_template

        db.session.rollback()  # Clean up any failed transactions
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 - Forbidden errors"""
        from flask import render_template

        return render_template("errors/403.html"), 403

    # Register Jinja2 filters
    @app.template_filter("md")
    def markdown_filter(text):
        """Render Markdown text as safe HTML."""
        if not text:
            return ""
        import markdown as _md
        from markupsafe import Markup
        html = _md.markdown(text, extensions=["nl2br", "sane_lists", "smarty"])
        return Markup(html)

    @app.template_filter("strip_md")
    def strip_markdown_filter(text):
        """Strip Markdown markers for plain text display (table snippets, search)."""
        if not text:
            return ""
        import re
        t = text
        t = re.sub(r'^#{1,6}\s+', '', t, flags=re.MULTILINE)  # headings
        t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)  # bold
        t = re.sub(r'\*(.+?)\*', r'\1', t)  # italic
        t = re.sub(r'`(.+?)`', r'\1', t)  # inline code
        t = re.sub(r'^\s*[-*+]\s+', '• ', t, flags=re.MULTILINE)  # bullets
        t = re.sub(r'^\s*\d+\.\s+', '', t, flags=re.MULTILINE)  # numbered
        t = re.sub(r'^\s*>\s?', '', t, flags=re.MULTILINE)  # blockquotes
        t = re.sub(r'\n{2,}', ' ', t)  # collapse double newlines
        t = re.sub(r'\n', ' ', t)  # single newlines to space
        return t.strip()

    @app.template_filter("format_value")
    def format_value_filter(value, value_type, config=None):
        """Format a numeric value according to its value type's decimal places and display scale"""
        if value is None:
            return ""

        # For qualitative types, return as-is
        if value_type.kind != "numeric":
            return value

        # Get display scale settings from config if provided
        divisor = 1
        suffix = ""
        if config and hasattr(config, "display_scale"):
            divisor = config.get_scale_divisor()
            suffix = config.get_scale_suffix()

        # Scale the value
        scaled_value = float(value) / divisor

        # Determine decimal places to use
        explicit_decimals = False
        if divisor > 1:
            # Using scale: check if display_decimals is explicitly set
            if config and hasattr(config, "display_decimals") and config.display_decimals is not None:
                decimal_places = config.display_decimals
                explicit_decimals = True
            else:
                # Use value type's decimal places setting (respect 0 for whole numbers)
                decimal_places = value_type.decimal_places if value_type.decimal_places is not None else 2

            # Format value
            if decimal_places == 0:
                # No decimals - format as integer (don't use rstrip which would remove significant zeros)
                formatted = f"{int(round(scaled_value))}"
            else:
                # Has decimals
                formatted = f"{scaled_value:.{decimal_places}f}"
                # Only strip trailing zeros if decimals weren't explicitly set
                if not explicit_decimals:
                    formatted = formatted.rstrip("0").rstrip(".")
        else:
            # No scaling: use original format
            if value_type.numeric_format == "integer":
                formatted = f"{int(round(scaled_value))}"
            else:
                # Decimal format
                decimal_places = value_type.decimal_places if value_type.decimal_places is not None else 2
                formatted = f"{scaled_value:.{decimal_places}f}"

        # Add suffix if present
        if suffix:
            formatted = f"{formatted}{suffix}"

        return formatted

    @app.template_filter("default_value_color")
    def default_value_color_filter(value):
        """Get default color for a numeric value based on its sign (for rollups)"""
        if value is None:
            return None
        try:
            numeric_value = float(value)
            if numeric_value > 0:
                return "#28a745"  # green
            elif numeric_value < 0:
                return "#dc3545"  # red
            else:
                return "#6c757d"  # gray
        except (ValueError, TypeError):
            return None

    # Bootstrap admin (only creates if doesn't exist)
    # Note: DO NOT use db.create_all() in production - use migrations instead!
    with app.app_context():
        # CRITICAL LOGGING: Show which database we're using
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        flask_env = app.config.get("FLASK_ENV", "development")
        print("=" * 80)
        print(f"FLASK_ENV: {flask_env}")
        if "postgresql" in db_uri:
            # Mask password for security
            safe_uri = db_uri.split("@")[1] if "@" in db_uri else db_uri
            print(f"[OK] USING POSTGRESQL: {safe_uri}")
        elif "sqlite" in db_uri:
            print(f"[WARN] USING SQLITE: {db_uri}")
            if flask_env == "production":
                print("[ERROR] SQLite should NEVER be used in production!")
        print("=" * 80)

        # Only create tables in testing/development without migrations
        if app.config.get("TESTING") or (app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite:///")):
            if flask_env == "production":
                raise RuntimeError("CRITICAL: Attempted to use SQLite in production! Check DATABASE_URL!")
            db.create_all()

        try:
            _ensure_schema_fixes()
        except Exception as e:
            print(f"Note: Skipping schema fixes: {e}")

        try:
            _bootstrap_admin()
        except Exception as e:
            # During migrations, schema might not match models yet - that's OK
            print(f"Note: Skipping bootstrap (likely during migration): {e}")

    return app


def _ensure_schema_fixes():
    """Apply schema fixes that migrations may have failed to apply (e.g. enum ADD VALUE in transactions)."""
    from sqlalchemy import text, inspect

    try:
        with db.engine.connect() as conn:
            # Fix enum values (safe to re-run — IF NOT EXISTS)
            conn.execute(text("COMMIT"))  # exit any failed transaction
            conn.execute(text("ALTER TYPE action_item_mention_entity_type ADD VALUE IF NOT EXISTS 'stakeholder'"))
            conn.execute(text("ALTER TYPE action_item_type ADD VALUE IF NOT EXISTS 'milestone'"))

            # Fix missing columns
            inspector = inspect(db.engine)
            ai_cols = {c["name"] for c in inspector.get_columns("action_items")}
            org_cols = {c["name"] for c in inspector.get_columns("organizations")}
            contrib_cols = {c["name"] for c in inspector.get_columns("contributions")}

            fixes = []
            if "is_global" not in ai_cols:
                fixes.append("ALTER TABLE action_items ADD COLUMN is_global BOOLEAN NOT NULL DEFAULT FALSE")
            if "milestone_category" not in ai_cols:
                fixes.append("ALTER TABLE action_items ADD COLUMN milestone_category VARCHAR(50)")
            if "tags" not in ai_cols:
                fixes.append("ALTER TABLE action_items ADD COLUMN tags JSON")
            if "action_tags" not in org_cols:
                fixes.append("ALTER TABLE organizations ADD COLUMN action_tags JSON")
            if "stakeholder_id" not in contrib_cols:
                fixes.append("ALTER TABLE contributions ADD COLUMN stakeholder_id INTEGER REFERENCES stakeholders(id) ON DELETE SET NULL")

            vt_cols = {c["name"] for c in inspector.get_columns("value_types")}
            if "category" not in vt_cols:
                fixes.append("ALTER TABLE value_types ADD COLUMN category VARCHAR(50)")

            org_cols2 = {c["name"] for c in inspector.get_columns("organizations")}
            if "value_type_categories" not in org_cols2:
                fixes.append("ALTER TABLE organizations ADD COLUMN value_type_categories JSON")

            gb_cols = {c["name"] for c in inspector.get_columns("governance_bodies")}
            if "is_global" not in gb_cols:
                fixes.append("ALTER TABLE governance_bodies ADD COLUMN is_global BOOLEAN NOT NULL DEFAULT FALSE")

            if fixes:
                conn.execute(text("BEGIN"))
                for fix in fixes:
                    print(f"[SCHEMA FIX] {fix}")
                    conn.execute(text(fix))
                conn.execute(text("COMMIT"))
                print(f"[SCHEMA FIX] Applied {len(fixes)} fixes")
            else:
                print("[SCHEMA FIX] Schema is up to date")
    except Exception as e:
        print(f"[SCHEMA FIX] Error (non-fatal): {e}")


def _bootstrap_admin():
    """
    Create bootstrap global administrator account if it doesn't exist.

    Login: cisk
    Password: Zurich20
    """
    from app.models import User

    # Check if any global admin exists
    existing_admin = User.query.filter_by(is_global_admin=True).first()
    if existing_admin:
        return  # Admin already exists

    # Create bootstrap admin
    admin = User(
        login="cisk",
        email="admin@cisk.local",
        display_name="CISK Administrator",
        is_active=True,
        is_global_admin=True,
        must_change_password=True,
    )
    admin.set_password("Zurich20")

    db.session.add(admin)
    db.session.commit()

    print("Bootstrap admin created: login=cisk, password=Zurich20 (must change on first login)")
