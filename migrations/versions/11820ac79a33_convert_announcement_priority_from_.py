"""Convert announcement priority from integer to string

Revision ID: 11820ac79a33
Revises: 2a5d95b0bd03
Create Date: 2025-06-30 02:52:19.001363

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '11820ac79a33'
down_revision = '2a5d95b0bd03'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add a temporary column for new priority values
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority_temp', sa.String(length=10), nullable=True))
    
    # Step 2: Convert existing integer priorities to string values
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE announcements 
        SET priority_temp = CASE 
            WHEN priority >= 7 THEN 'high'
            WHEN priority >= 4 THEN 'medium'
            ELSE 'low'
        END
    """))
    
    # Step 3: Drop the old priority column and rename temp column
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.drop_column('priority')
        batch_op.alter_column('priority_temp',
               new_column_name='priority',
               type_=sa.String(length=10),
               nullable=False,
               server_default='low')


def downgrade():
    # Step 1: Add a temporary integer column
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority_temp', mysql.INTEGER(), nullable=True))
    
    # Step 2: Convert string priorities back to integer values
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE announcements 
        SET priority_temp = CASE 
            WHEN priority = 'high' THEN 8
            WHEN priority = 'medium' THEN 5
            ELSE 1
        END
    """))
    
    # Step 3: Drop the string column and rename temp column
    with op.batch_alter_table('announcements', schema=None) as batch_op:
        batch_op.drop_column('priority')
        batch_op.alter_column('priority_temp',
               new_column_name='priority',
               type_=mysql.INTEGER(),
               nullable=False,
               server_default='0')
