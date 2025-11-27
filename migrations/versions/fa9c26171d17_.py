"""empty message

Revision ID: fa9c26171d17
Revises: bdba8715479d
Create Date: 2025-11-22 12:24:20.996820

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'fa9c26171d17'
down_revision = 'bdba8715479d'
branch_labels = None
depends_on = None


def upgrade():
    # ---- appointment table ----
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('availability_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('diagnosis', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('prescription', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('treatment_notes', sa.Text(), nullable=True))

        # Named FK (fix)
        batch_op.create_foreign_key(
            'fk_appointment_availability_id',
            'doctor_availability',
            ['availability_id'],
            ['id']
        )

    # ---- doctor table ----
    with op.batch_alter_table('doctor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('availability', sa.Text(), nullable=True))
        batch_op.drop_column('availability_json')

    # ---- doctor_availability table ----
    with op.batch_alter_table('doctor_availability', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slot_capacity', sa.Integer(), nullable=True))

    # ---- patient table ----
    with op.batch_alter_table('patient', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('address', sa.Text(), nullable=True))

    # ---- treatment table ----
    with op.batch_alter_table('treatment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # ---- user table ----
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_photo', sa.String(length=256), nullable=True))


def downgrade():
    # ---- user table ----
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('profile_photo')

    # ---- treatment table ----
    with op.batch_alter_table('treatment', schema=None) as batch_op:
        batch_op.drop_column('created_at')

    # ---- patient table ----
    with op.batch_alter_table('patient', schema=None) as batch_op:
        batch_op.drop_column('address')
        batch_op.drop_column('name')

    # ---- doctor_availability table ----
    with op.batch_alter_table('doctor_availability', schema=None) as batch_op:
        batch_op.drop_column('slot_capacity')

    # ---- doctor table ----
    with op.batch_alter_table('doctor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('availability_json', sqlite.JSON(), nullable=True))
        batch_op.drop_column('availability')

    # ---- appointment table ----
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.drop_constraint('fk_appointment_availability_id', type_='foreignkey')
        batch_op.drop_column('treatment_notes')
        batch_op.drop_column('prescription')
        batch_op.drop_column('diagnosis')
        batch_op.drop_column('availability_id')
