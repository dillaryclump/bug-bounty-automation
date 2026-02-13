"""Add scope_history table

Revision ID: 005
Revises: 004
Create Date: 2024-01-XX
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scope_history table."""
    
    # Create scope_change_type enum
    scope_change_type = postgresql.ENUM(
        'added',
        'removed',
        'modified',
        name='scopechangetype',
        create_type=True
    )
    scope_change_type.create(op.get_bind(), checkfirst=True)
    
    # Create scope_history table
    op.create_table(
        'scope_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('in_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('out_of_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('checksum', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('checked_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(
        'ix_scope_history_program_id',
        'scope_history',
        ['program_id']
    )
    op.create_index(
        'ix_scope_history_checked_at',
        'scope_history',
        ['checked_at']
    )
    op.create_index(
        'ix_scope_history_checksum',
        'scope_history',
        ['checksum']
    )


def downgrade() -> None:
    """Remove scope_history table."""
    op.drop_index('ix_scope_history_checksum', table_name='scope_history')
    op.drop_index('ix_scope_history_checked_at', table_name='scope_history')
    op.drop_index('ix_scope_history_program_id', table_name='scope_history')
    op.drop_table('scope_history')
    
    # Drop enum
    scope_change_type = postgresql.ENUM(
        'added',
        'removed',
        'modified',
        name='scopechangetype'
    )
    scope_change_type.drop(op.get_bind(), checkfirst=True)
