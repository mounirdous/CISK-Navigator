"""
Application configuration
"""

import os
from pathlib import Path

basedir = Path(__file__).parent.parent


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # Database URI - handle Render's postgres:// and use psycopg3
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render provides postgres://, SQLAlchemy needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        # Use psycopg3 driver (modern, compatible with Python 3.14)
        if database_url.startswith("postgresql://") and "+" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    # CRITICAL: In production, DATABASE_URL MUST be set - never fall back to SQLite!
    if os.environ.get("FLASK_ENV") == "production" and not database_url:
        raise RuntimeError(
            "CRITICAL ERROR: DATABASE_URL environment variable is not set in production! "
            "This would create a new SQLite database and DESTROY all your data. "
            "Please set DATABASE_URL in your Render environment variables."
        )

    SQLALCHEMY_DATABASE_URI = database_url or f'sqlite:///{basedir / "cisk.db"}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database engine options
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # WTF Forms
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
