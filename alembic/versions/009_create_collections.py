"""Create collections table.

Revision ID: 009
Revises: 008
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create collections table."""
    op.create_table(
        'collections',
        sa.Column('name', sa.String(100), primary_key=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('vector_dimensionality', sa.Integer(), nullable=False),
        sa.Column('distance_metric', sa.String(20), nullable=False, default='cosine'),
        sa.Column('document_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_vector_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('retention_policy_days', sa.Integer(), nullable=True),
        sa.Column('metadata_schema', postgresql.JSONB(), nullable=True),
    )

    # Create indexes
    op.create_index('idx_collections_created_at', 'collections', ['created_at'])

    # Insert default collection
    op.execute(
        """
        INSERT INTO collections (name, description, vector_dimensionality, distance_metric, document_count, total_vector_count)
        VALUES ('olist_reviews', 'Olist order reviews from Kaggle dataset', 1536, 'cosine', 0, 0)
        """
    )


def downgrade() -> None:
    """Drop collections table."""
    op.drop_index('idx_collections_created_at')
    op.drop_table('collections')
