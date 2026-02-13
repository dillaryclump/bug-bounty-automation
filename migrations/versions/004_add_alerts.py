"""add_alerts_table

Revision ID: 004_add_alerts
Revises: 003_base_schema
Create Date: 2026-02-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_alerts'
down_revision = '003_base_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add alerts table for notification tracking."""
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('program_id', sa.Integer(), nullable=True),
        sa.Column('vulnerability_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('destination', sa.String(length=500), nullable=False),
        sa.Column('sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vulnerability_id'], ['vulnerabilities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_alert_type_created', 'alerts', ['alert_type', 'created_at'])
    op.create_index('idx_alert_sent_success', 'alerts', ['sent', 'success'])
    op.create_index('idx_alert_channel_sent', 'alerts', ['channel', 'sent_at'])
    op.create_index('idx_alert_severity', 'alerts', ['severity'])
    op.create_index('idx_alert_program', 'alerts', ['program_id'])


def downgrade() -> None:
    """Remove alerts table."""
    
    # Drop indexes
    op.drop_index('idx_alert_program', table_name='alerts')
    op.drop_index('idx_alert_severity', table_name='alerts')
    op.drop_index('idx_alert_channel_sent', table_name='alerts')
    op.drop_index('idx_alert_sent_success', table_name='alerts')
    op.drop_index('idx_alert_type_created', table_name='alerts')
    
    # Drop table
    op.drop_table('alerts')
