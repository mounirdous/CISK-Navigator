"""create initial superadmin

Revision ID: 9f8e7d6c5b4a
Revises: 39e615da65b9
Create Date: 2026-03-10 12:00:00.000000

"""

import os
from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash
from datetime import datetime


# revision identifiers, used by Alembic.
revision = "9f8e7d6c5b4a"
down_revision = "39e615da65b9"
branch_labels = None
depends_on = None


def upgrade():
    """
    Create initial super admin user if no super admin exists.
    
    Uses environment variable INITIAL_ADMIN_PASSWORD or defaults to 'admin123'
    Username: admin
    
    THIS IS ONLY FOR INITIAL SETUP - Change password after first login!
    """
    conn = op.get_bind()
    
    # Check if any super admin exists
    result = conn.execute(sa.text(
        "SELECT COUNT(*) FROM users WHERE is_super_admin = true"
    ))
    count = result.scalar()
    
    if count == 0:
        # No super admin exists, create one
        initial_password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'admin123')
        password_hash = generate_password_hash(initial_password)
        
        conn.execute(sa.text("""
            INSERT INTO users 
            (login, email, display_name, password_hash, is_active, is_super_admin, is_global_admin, created_at, updated_at, must_change_password)
            VALUES 
            (:login, :email, :display_name, :password_hash, :is_active, :is_super_admin, :is_global_admin, :created_at, :updated_at, :must_change_password)
        """), {
            'login': 'admin',
            'email': 'admin@cisknavigator.com',
            'display_name': 'System Administrator',
            'password_hash': password_hash,
            'is_active': True,
            'is_super_admin': True,
            'is_global_admin': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'must_change_password': True
        })
        
        print("✓ Initial super admin created: 'admin'")
        print("⚠️  SECURITY: Change password immediately after first login!")
    else:
        print(f"✓ Super admin already exists (found {count}), skipping creation")


def downgrade():
    """
    Remove the initial admin user (only if it still has default credentials).
    """
    conn = op.get_bind()
    
    # Only remove if login is 'admin' and email is the default
    conn.execute(sa.text("""
        DELETE FROM users 
        WHERE login = 'admin' 
        AND email = 'admin@cisknavigator.com'
    """))
