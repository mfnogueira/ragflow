"""Create answers table.

Revision ID: 004
Revises: 003
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create answers table."""
    op.create_table(
        'answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('generation_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('llm_model_used', sa.String(100), nullable=False),
        sa.Column('token_count_input', sa.Integer(), nullable=False, default=0),
        sa.Column('token_count_output', sa.Integer(), nullable=False, default=0),
        sa.Column('retrieval_latency_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('generation_latency_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_latency_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, default=False),
        sa.Column('validation_status', sa.String(20), nullable=False, default='passed'),
        sa.Column('escalation_flag', sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column('redaction_flag', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, default={}),
        sa.ForeignKeyConstraint(['query_id'], ['queries.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('idx_answers_generation_timestamp', 'answers', ['generation_timestamp'])
    op.create_index('idx_answers_confidence_score', 'answers', ['confidence_score'])


def downgrade() -> None:
    """Drop answers table."""
    op.drop_index('idx_answers_confidence_score')
    op.drop_index('idx_answers_generation_timestamp')
    op.drop_table('answers')
