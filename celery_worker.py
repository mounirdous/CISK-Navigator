"""
Celery worker entry point
Run with: celery -A celery_worker worker --loglevel=info --pool=solo
"""

from dotenv import load_dotenv
load_dotenv()

from app import create_app

# Create Flask app first to get config
flask_app = create_app()

# Get the celery instance from the app
celery = flask_app.celery

# Import tasks so Celery discovers them
import app.tasks  # noqa: F401, E402
