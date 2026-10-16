"""Expandir autenticação; não modificar tabelas editoriais."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("auth_rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_rate_limits_expires_at", "auth_rate_limits", ["expires_at"])
    op.create_table("password_resets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("admin_id", sa.UUID(), sa.ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)))
    op.create_index("ix_password_resets_admin_id", "password_resets", ["admin_id"])
    op.create_index("ix_password_resets_expires_at", "password_resets", ["expires_at"])


def downgrade():
    # Somente tabelas introduzidas nesta revisão; backup obrigatório antes de uso.
    op.drop_table("password_resets")
    op.drop_table("auth_rate_limits")
