"""initial schema

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    json_type = postgresql.JSONB()
    op.create_table("user_profile",
        sa.Column("id", uuid, primary_key=True), sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(20), nullable=False), sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False), sa.Column("fitness_goal", sa.String(40), nullable=False),
        sa.Column("foods_to_avoid", json_type, nullable=False), sa.Column("favorite_foods", json_type, nullable=False),
        sa.Column("max_prep_minutes", sa.Integer(), nullable=True), sa.Column("unit_preference", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("inventory_item",
        sa.Column("id", uuid, primary_key=True), sa.Column("profile_id", uuid, sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("normalized_name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("profile_id", "normalized_name", name="uq_inventory_profile_name"),
    )
    op.create_table("workout",
        sa.Column("id", uuid, primary_key=True), sa.Column("profile_id", uuid, sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True), sa.Column("moving_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True), sa.Column("elevation_gain_meters", sa.Float(), nullable=True),
        sa.Column("avg_speed_mps", sa.Float(), nullable=True), sa.Column("avg_heart_rate", sa.Float(), nullable=True),
        sa.Column("max_heart_rate", sa.Float(), nullable=True), sa.Column("pre_exercise_weight_kg", sa.Float(), nullable=True),
        sa.Column("post_exercise_weight_kg", sa.Float(), nullable=True), sa.Column("met_value", sa.Float(), nullable=True),
        sa.Column("intensity", sa.String(20), nullable=True), sa.Column("estimated_calories_low", sa.Integer(), nullable=True),
        sa.Column("estimated_calories_high", sa.Integer(), nullable=True), sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("recovery_target",
        sa.Column("id", uuid, primary_key=True), sa.Column("workout_id", uuid, sa.ForeignKey("workout.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("protein_g_low", sa.Integer(), nullable=False), sa.Column("protein_g_high", sa.Integer(), nullable=False),
        sa.Column("carbs_g_low", sa.Integer(), nullable=False), sa.Column("carbs_g_high", sa.Integer(), nullable=False),
        sa.Column("fluid_ml_low", sa.Integer(), nullable=True), sa.Column("fluid_ml_high", sa.Integer(), nullable=True),
        sa.Column("calculation_version", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("meal_recommendation",
        sa.Column("id", uuid, primary_key=True), sa.Column("workout_id", uuid, sa.ForeignKey("workout.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False), sa.Column("name", sa.String(180), nullable=False),
        sa.Column("ingredients", json_type, nullable=False), sa.Column("preparation_steps", json_type, nullable=False),
        sa.Column("prep_minutes", sa.Integer(), nullable=False), sa.Column("estimated_calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False), sa.Column("carbs_g", sa.Integer(), nullable=False), sa.Column("fat_g", sa.Integer(), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False), sa.Column("missing_ingredients", json_type, nullable=False),
        sa.Column("recovery_match_score", sa.Float(), nullable=False), sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("meal_recommendation")
    op.drop_table("recovery_target")
    op.drop_table("workout")
    op.drop_table("inventory_item")
    op.drop_table("user_profile")

