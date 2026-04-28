"""
Logo routes - Serve entity logos from database
"""

from flask import Blueprint, Response, abort

from app.models import KPI, Challenge, EntityTypeDefault, Initiative, Organization, Space, System

bp = Blueprint("logo", __name__, url_prefix="/api/logo")


@bp.route("/organization/<int:entity_id>")
def organization_logo(entity_id):
    """Serve organization logo from database"""
    org = Organization.query.get_or_404(entity_id)
    if not org.logo_data or not org.logo_mime_type:
        abort(404)
    return Response(org.logo_data, mimetype=org.logo_mime_type)


@bp.route("/space/<int:entity_id>")
def space_logo(entity_id):
    """Serve space logo from database"""
    space = Space.query.get_or_404(entity_id)
    if not space.logo_data or not space.logo_mime_type:
        abort(404)
    return Response(space.logo_data, mimetype=space.logo_mime_type)


@bp.route("/challenge/<int:entity_id>")
def challenge_logo(entity_id):
    """Serve challenge logo from database"""
    challenge = Challenge.query.get_or_404(entity_id)
    if not challenge.logo_data or not challenge.logo_mime_type:
        abort(404)
    return Response(challenge.logo_data, mimetype=challenge.logo_mime_type)


@bp.route("/initiative/<int:entity_id>")
def initiative_logo(entity_id):
    """Serve initiative logo from database"""
    initiative = Initiative.query.get_or_404(entity_id)
    if not initiative.logo_data or not initiative.logo_mime_type:
        abort(404)
    return Response(initiative.logo_data, mimetype=initiative.logo_mime_type)


@bp.route("/system/<int:entity_id>")
def system_logo(entity_id):
    """Serve system logo from database"""
    system = System.query.get_or_404(entity_id)
    if not system.logo_data or not system.logo_mime_type:
        abort(404)
    return Response(system.logo_data, mimetype=system.logo_mime_type)


@bp.route("/kpi/<int:entity_id>")
def kpi_logo(entity_id):
    """Serve KPI logo from database"""
    kpi = KPI.query.get_or_404(entity_id)
    if not kpi.logo_data or not kpi.logo_mime_type:
        abort(404)
    return Response(kpi.logo_data, mimetype=kpi.logo_mime_type)


@bp.route("/entity-default/<int:default_id>")
def entity_default_logo(default_id):
    """Serve EntityTypeDefault logo from database"""
    default = EntityTypeDefault.query.get_or_404(default_id)
    if not default.default_logo_data or not default.default_logo_mime_type:
        abort(404)
    return Response(default.default_logo_data, mimetype=default.default_logo_mime_type)
