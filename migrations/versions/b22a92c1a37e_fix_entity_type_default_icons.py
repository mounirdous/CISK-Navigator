"""fix_entity_type_default_icons

Revision ID: b22a92c1a37e
Revises: 5da7a6743629
Create Date: 2026-03-14 19:22:28.049371

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b22a92c1a37e"
down_revision = "5da7a6743629"
branch_labels = None
depends_on = None


def upgrade():
    """Fix entity type default icons to use correct symbols instead of emoji"""
    # Update Space icon: 🎯 -> 🏢
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = '🏢'
        WHERE entity_type = 'space' AND default_icon = '🎯'
        """
    )

    # Update Challenge icon: ⚡ -> ƒ
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = 'ƒ'
        WHERE entity_type = 'challenge' AND default_icon = '⚡'
        """
    )

    # Update Initiative icon: 🚀 -> δ
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = 'δ'
        WHERE entity_type = 'initiative' AND default_icon = '🚀'
        """
    )

    # Update System icon: ⚙️ -> Φ
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = 'Φ'
        WHERE entity_type = 'system' AND default_icon = '⚙️'
        """
    )

    # Update KPI icon: 📊 -> Ψ
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = 'Ψ'
        WHERE entity_type = 'kpi' AND default_icon = '📊'
        """
    )


def downgrade():
    """Revert to old emoji icons"""
    # Revert Space icon
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = '🎯'
        WHERE entity_type = 'space' AND default_icon = '🏢'
        """
    )

    # Revert Challenge icon
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = '⚡'
        WHERE entity_type = 'challenge' AND default_icon = 'ƒ'
        """
    )

    # Revert Initiative icon
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = '🚀'
        WHERE entity_type = 'initiative' AND default_icon = 'δ'
        """
    )

    # Revert System icon
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = '⚙️'
        WHERE entity_type = 'system' AND default_icon = 'Φ'
        """
    )

    # Revert KPI icon
    op.execute(
        """
        UPDATE entity_type_defaults
        SET default_icon = '📊'
        WHERE entity_type = 'kpi' AND default_icon = 'Ψ'
        """
    )
