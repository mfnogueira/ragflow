"""Create documents table.

Revision ID: 001
Revises:
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create documents table."""
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_format', sa.String(10), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('collection_name', sa.String(100), nullable=False, index=True),
        sa.Column('language_code', sa.String(10), nullable=False, default='pt-BR'),
        sa.Column('status', sa.String(30), nullable=False, default='pending', index=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, default=0),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, default={}),
    )

    # Create indexes
    op.create_index('idx_documents_uploaded_at', 'documents', ['uploaded_at'])
    op.create_index('idx_documents_collection_status', 'documents', ['collection_name', 'status'])


def downgrade() -> None:
    """Drop documents table."""
    op.drop_index('idx_documents_collection_status')
    op.drop_index('idx_documents_uploaded_at')
    op.drop_table('documents')
