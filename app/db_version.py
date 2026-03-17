"""
Database Schema Version

This version number tracks the database schema structure.
It should ONLY be incremented when the database schema changes
(new tables, new columns, removed columns, changed relationships, etc.)

DO NOT increment for:
- New features that don't change the schema
- UI changes
- Bug fixes
- Code refactoring

DO increment when:
- Adding/removing tables
- Adding/removing columns
- Changing column types
- Adding/removing foreign keys
- Adding/removing indexes
- Any Alembic migration that changes structure

Version History:
- 1.0 (2026-03-17): Initial DB version tracking
      Includes: Core CISK models, Stakeholder mapping, Geography, Linked KPIs, Formulas
"""

DB_SCHEMA_VERSION = "1.0"
