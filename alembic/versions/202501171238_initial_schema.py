"""initial schema"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202501171238"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operators",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_load", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.UniqueConstraint("name", name="uq_operators_name"),
    )
    op.create_index("ix_operators_id", "operators", ["id"], unique=False)

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("external_id", name="uq_leads_external_id"),
    )
    op.create_index("ix_leads_id", "leads", ["id"], unique=False)
    op.create_index("ix_leads_external_id", "leads", ["external_id"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.UniqueConstraint("name", name="uq_sources_name"),
        sa.UniqueConstraint("code", name="uq_sources_code"),
    )
    op.create_index("ix_sources_id", "sources", ["id"], unique=False)

    op.create_table(
        "source_operator_configs",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["operators.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("source_id", "operator_id", name="uix_source_operator"),
    )
    op.create_index(
        "ix_source_operator_configs_source_id",
        "source_operator_configs",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_source_operator_configs_operator_id",
        "source_operator_configs",
        ["operator_id"],
        unique=False,
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["operators.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_contacts_id", "contacts", ["id"], unique=False)
    op.create_index("ix_contacts_lead_id", "contacts", ["lead_id"], unique=False)
    op.create_index("ix_contacts_source_id", "contacts", ["source_id"], unique=False)
    op.create_index("ix_contacts_operator_id", "contacts", ["operator_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_contacts_operator_id", table_name="contacts")
    op.drop_index("ix_contacts_source_id", table_name="contacts")
    op.drop_index("ix_contacts_lead_id", table_name="contacts")
    op.drop_index("ix_contacts_id", table_name="contacts")
    op.drop_table("contacts")

    op.drop_index(
        "ix_source_operator_configs_operator_id",
        table_name="source_operator_configs",
    )
    op.drop_index(
        "ix_source_operator_configs_source_id",
        table_name="source_operator_configs",
    )
    op.drop_table("source_operator_configs")

    op.drop_index("ix_sources_id", table_name="sources")
    op.drop_table("sources")

    op.drop_index("ix_leads_external_id", table_name="leads")
    op.drop_index("ix_leads_id", table_name="leads")
    op.drop_table("leads")

    op.drop_index("ix_operators_id", table_name="operators")
    op.drop_table("operators")
