"""weekly planning

Revision ID: 0003_weekly_planning
Revises: 0002_v2_experience
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_weekly_planning"
down_revision = "0002_v2_experience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    json_type = postgresql.JSONB()
    op.create_table(
        "weekly_plan",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("profile_id", uuid, sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("profile_id", "starts_on", name="uq_weekly_plan_profile_start"),
    )
    op.create_table(
        "planned_workout",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("weekly_plan_id", uuid, sa.ForeignKey("weekly_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("expected_intensity", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "planned_meal_option",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("planned_workout_id", uuid, sa.ForeignKey("planned_workout.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("ingredients", json_type, nullable=False),
        sa.Column("preparation_steps", json_type, nullable=False),
        sa.Column("prep_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False),
        sa.Column("carbs_g", sa.Integer(), nullable=False),
        sa.Column("fat_g", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
        sa.Column("recovery_match_score", sa.Float(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "grocery_line",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("weekly_plan_id", uuid, sa.ForeignKey("weekly_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_key", sa.String(220), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(160), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("available_at_home", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("weekly_plan_id", "identity_key", name="uq_grocery_line_plan_identity"),
    )


def downgrade() -> None:
    op.drop_table("grocery_line")
    op.drop_table("planned_meal_option")
    op.drop_table("planned_workout")
    op.drop_table("weekly_plan")