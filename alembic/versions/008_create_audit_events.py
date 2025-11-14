"""Create audit_events table.

Revision ID: 008
Revises: 007
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_events table."""
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('actor', sa.String(255), nullable=False, index=True),
        sa.Column('affected_entity_type', sa.String(100), nullable=True, index=True),
        sa.Column('affected_entity_id', sa.String(100), nullable=True, index=True),
        sa.Column('severity', sa.String(20), nullable=False, default='info', index=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True, index=True),
        sa.Column('error_message', sa.String(1000), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('trace_id', sa.String(100), nullable=True, index=True),
        sa.Column('span_id', sa.String(100), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
    )

    # Create composite indexes for common queries
    op.create_index('idx_audit_events_type_timestamp', 'audit_events', ['event_type', 'timestamp'])
    op.create_index('idx_audit_events_entity', 'audit_events', ['affected_entity_type', 'affected_entity_id'])
    op.create_index('idx_audit_events_severity_timestamp', 'audit_events', ['severity', 'timestamp'])


def downgrade() -> None:
    """Drop audit_events table."""
    op.drop_index('idx_audit_events_severity_timestamp')
    op.drop_index('idx_audit_events_entity')
    op.drop_index('idx_audit_events_type_timestamp')
    op.drop_table('audit_events')
