"""planned activity display labels

Revision ID: 0004_planned_activity_labels
Revises: 0003_weekly_planning
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_planned_activity_labels"
down_revision = "0003_weekly_planning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("planned_workout", sa.Column("display_activity", sa.String(120), nullable=True))
    op.add_column("planned_workout", sa.Column("normalized_activity", sa.String(40), nullable=True))
    op.execute("UPDATE planned_workout SET display_activity = activity_type, normalized_activity = activity_type")
    op.alter_column("planned_workout", "display_activity", nullable=False)
    op.alter_column("planned_workout", "normalized_activity", nullable=False)


def downgrade() -> None:
    op.drop_column("planned_workout", "normalized_activity")
    op.drop_column("planned_workout", "display_activity")