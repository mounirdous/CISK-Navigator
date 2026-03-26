"""Run database migrations."""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost/cisknavigator'
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from flask_migrate import upgrade

app = create_app()
with app.app_context():
    upgrade()
    print("Database upgrade complete!")
