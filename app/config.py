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

    # CRITICAL: DATABASE_URL should be set, but allow SQLite as absolute last resort
    # (This fallback should never be used - DevelopmentConfig overrides with PostgreSQL)
    if not database_url:
        import warnings

        warnings.warn(
            "WARNING: DATABASE_URL not set! Using SQLite fallback. "
            "This should only happen during initial setup. "
            "For normal operation, use PostgreSQL by setting DATABASE_URL or using DevelopmentConfig.",
            RuntimeWarning,
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

    # Mapbox (for geographic visualizations)
    # Get free token at: https://account.mapbox.com/access-tokens/
    # Free tier: 50,000 map loads/month
    MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True

    # ENFORCE PostgreSQL - NEVER use SQLite in development
    # Override the base Config's database URI with PostgreSQL explicitly
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Handle postgres:// -> postgresql:// conversion
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        # Use psycopg3 driver
        if database_url.startswith("postgresql://") and "+" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Default to local PostgreSQL - NO SQLite fallback!
        SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://localhost/cisknavigator"


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
