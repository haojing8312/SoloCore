"""add thumbnail_url and duration to sub_video_tasks

Revision ID: 8f1c2d9a7b21
Revises: 30aa2810635a
Create Date: 2025-08-13 18:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1c2d9a7b21"
down_revision: Union[str, Sequence[str], None] = "30aa2810635a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 为 sub_video_tasks 新增缩略图与时长字段
    op.add_column(
        "sub_video_tasks",
        sa.Column("thumbnail_url", sa.Text(), nullable=True, comment="视频缩略图URL"),
        schema="textloom_core",
    )
    op.add_column(
        "sub_video_tasks",
        sa.Column("duration", sa.Integer(), nullable=True, comment="时长(秒)"),
        schema="textloom_core",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sub_video_tasks", "duration", schema="textloom_core")
    op.drop_column("sub_video_tasks", "thumbnail_url", schema="textloom_core")
