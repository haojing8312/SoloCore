"""add_current_stage_to_tasks

Revision ID: f90ca5d807de
Revises: da536ca717f2
Create Date: 2025-09-03 13:59:30.785773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f90ca5d807de'
down_revision: Union[str, Sequence[str], None] = 'da536ca717f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 current_stage 字段到 tasks 表
    op.add_column(
        'tasks',
        sa.Column('current_stage', sa.String(length=50), nullable=True, comment='当前任务阶段'),
        schema='textloom_core'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 current_stage 字段
    op.drop_column('tasks', 'current_stage', schema='textloom_core')
