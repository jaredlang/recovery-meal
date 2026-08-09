"""v2 account, tracking, favorites, and images

Revision ID: 0002_v2_experience
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_v2_experience"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    json_type = postgresql.JSONB()
    op.add_column("user_profile", sa.Column("display_name", sa.String(120), nullable=False, server_default="Athlete"))
    op.add_column("user_profile", sa.Column("email", sa.String(254), nullable=True))
    op.add_column("user_profile", sa.Column("timezone", sa.String(80), nullable=False, server_default="UTC"))
    op.add_column("user_profile", sa.Column("avatar_filename", sa.String(255), nullable=True))
    op.add_column("meal_recommendation", sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("meal_recommendation", sa.Column("image_status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("meal_recommendation", sa.Column("image_filename", sa.String(255), nullable=True))
    op.create_table(
        "favorite_meal",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("profile_id", uuid, sa.ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_id", uuid, sa.ForeignKey("meal_recommendation.id", ondelete="SET NULL"), nullable=True),
        sa.Column("snapshot", json_type, nullable=False),
        sa.Column("image_filename", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("profile_id", "recommendation_id", name="uq_favorite_profile_recommendation"),
    )


def downgrade() -> None:
    op.drop_table("favorite_meal")
    op.drop_column("meal_recommendation", "image_filename")
    op.drop_column("meal_recommendation", "image_status")
    op.drop_column("meal_recommendation", "selected_at")
    op.drop_column("user_profile", "avatar_filename")
    op.drop_column("user_profile", "timezone")
    op.drop_column("user_profile", "email")
    op.drop_column("user_profile", "display_name")
