"""Create query_results table.

Revision ID: 005
Revises: 004
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create query_results table (links queries to retrieved chunks)."""
    op.create_table(
        'query_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('reranking_score', sa.Float(), nullable=True),
        sa.Column('rank_position', sa.Integer(), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata_match_flags', postgresql.JSONB(), nullable=False, default={}),
        sa.ForeignKeyConstraint(['query_id'], ['queries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_query_results_query_rank', 'query_results', ['query_id', 'rank_position'])
    op.create_index('idx_query_results_relevance', 'query_results', ['relevance_score'])


def downgrade() -> None:
    """Drop query_results table."""
    op.drop_index('idx_query_results_relevance')
    op.drop_index('idx_query_results_query_rank')
    op.drop_table('query_results')
