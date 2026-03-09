"""
Test error pages - REMOVE THIS FILE IN PRODUCTION

Provides routes to test custom error pages.
"""

from flask import Blueprint, abort
from flask_login import login_required

bp = Blueprint("test_errors", __name__, url_prefix="/test-errors")


@bp.route("/404")
def test_404():
    """Test 404 error page"""
    abort(404)


@bp.route("/500")
def test_500():
    """Test 500 error page"""
    # Trigger an actual error
    raise Exception("This is a test error to demonstrate the 500 error page")


@bp.route("/403")
@login_required
def test_403():
    """Test 403 error page"""
    abort(403)
