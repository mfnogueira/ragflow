"""Create chunks table.

Revision ID: 002
Revises: 001
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create chunks table (metadata only, vectors stored in Qdrant)."""
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('sequence_position', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('char_start_offset', sa.Integer(), nullable=False),
        sa.Column('char_end_offset', sa.Integer(), nullable=False),
        sa.Column('language_code', sa.String(10), nullable=False, default='pt-BR'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, default={}),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_chunks_document_sequence', 'chunks', ['document_id', 'sequence_position'])
    op.create_index('idx_chunks_created_at', 'chunks', ['created_at'])


def downgrade() -> None:
    """Drop chunks table."""
    op.drop_index('idx_chunks_created_at')
    op.drop_index('idx_chunks_document_sequence')
    op.drop_table('chunks')
