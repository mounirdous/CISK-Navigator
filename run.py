"""
CISK Navigator - Application Entry Point

Run this file to start the application:
    python run.py
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(debug=True, host='0.0.0.0', port=port)
