"""phase 5 job verification

Revision ID: b140fb949576
Revises: ea655497a0ad
Create Date: 2026-11-13 11:13:27.853890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b140fb949576'
down_revision: Union[str, Sequence[str], None] = 'ea655497a0ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Jobs that exist before Phase 5 were already visible to students, so they become APPROVED."""
    status = postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='verification_status', create_type=False)
    op.add_column('jobs', sa.Column('verification_status', status, nullable=False, server_default='APPROVED'))
    op.alter_column('jobs', 'verification_status', server_default=None)
    op.add_column('jobs', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('verified_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_jobs_verified_by_users', 'jobs', 'users', ['verified_by'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_jobs_verified_by_users', 'jobs', type_='foreignkey')
    op.drop_column('jobs', 'verified_by')
    op.drop_column('jobs', 'rejection_reason')
    op.drop_column('jobs', 'verification_status')
