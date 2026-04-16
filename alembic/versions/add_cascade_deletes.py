"""Add cascade delete relationships

Revision ID: add_cascade_deletes
Revises: 6fed16a4c340
Create Date: 2026-04-15 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_cascade_deletes'
down_revision: str = '38ab08b90fd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cascade delete constraints to foreign keys."""

    # Drop existing foreign key constraints
    op.drop_constraint('hostels_owner_id_fkey', 'hostels', type_='foreignkey')
    op.drop_constraint('rooms_hostel_id_fkey', 'rooms', type_='foreignkey')
    op.drop_constraint('tenants_hostel_id_fkey', 'tenants', type_='foreignkey')
    op.drop_constraint('tenants_room_id_fkey', 'tenants', type_='foreignkey')
    op.drop_constraint('tenant_payments_tenant_id_fkey', 'tenant_payments', type_='foreignkey')

    # Recreate foreign key constraints with CASCADE DELETE
    op.create_foreign_key(
        'hostels_owner_id_fkey',
        'hostels', 'owners',
        ['owner_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'rooms_hostel_id_fkey',
        'rooms', 'hostels',
        ['hostel_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'tenants_hostel_id_fkey',
        'tenants', 'hostels',
        ['hostel_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'tenants_room_id_fkey',
        'tenants', 'rooms',
        ['room_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'tenant_payments_tenant_id_fkey',
        'tenant_payments', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Remove cascade delete constraints and restore original foreign keys."""

    # Drop cascade foreign key constraints
    op.drop_constraint('hostels_owner_id_fkey', 'hostels', type_='foreignkey')
    op.drop_constraint('rooms_hostel_id_fkey', 'rooms', type_='foreignkey')
    op.drop_constraint('tenants_hostel_id_fkey', 'tenants', type_='foreignkey')
    op.drop_constraint('tenants_room_id_fkey', 'tenants', type_='foreignkey')
    op.drop_constraint('tenant_payments_tenant_id_fkey', 'tenant_payments', type_='foreignkey')

    # Recreate original foreign key constraints without CASCADE
    op.create_foreign_key(
        'hostels_owner_id_fkey',
        'hostels', 'owners',
        ['owner_id'], ['id']
    )
    op.create_foreign_key(
        'rooms_hostel_id_fkey',
        'rooms', 'hostels',
        ['hostel_id'], ['id']
    )
    op.create_foreign_key(
        'tenants_hostel_id_fkey',
        'tenants', 'hostels',
        ['hostel_id'], ['id']
    )
    op.create_foreign_key(
        'tenants_room_id_fkey',
        'tenants', 'rooms',
        ['room_id'], ['id']
    )
    op.create_foreign_key(
        'tenant_payments_tenant_id_fkey',
        'tenant_payments', 'tenants',
        ['tenant_id'], ['id']
    )