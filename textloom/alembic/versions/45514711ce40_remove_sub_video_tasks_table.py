"""remove sub_video_tasks table

Revision ID: 45514711ce40
Revises: bb0347984f23
Create Date: 2025-11-24 09:52:05.983115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45514711ce40'
down_revision: Union[str, Sequence[str], None] = 'bb0347984f23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop sub_video_tasks table - SubVideoTask功能已移除，改为单视频架构"""
    op.execute("DROP TABLE IF EXISTS textloom_core.sub_video_tasks CASCADE")


def downgrade() -> None:
    """Recreate sub_video_tasks table - 仅用于回滚"""
    # 注意：仅保留表结构定义，实际业务逻辑已移除，不建议回滚
    op.execute("""
        CREATE TABLE IF NOT EXISTS textloom_core.sub_video_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            sub_task_id VARCHAR(255) NOT NULL UNIQUE,
            parent_task_id UUID NOT NULL REFERENCES textloom_core.tasks(id) ON DELETE CASCADE,
            progress INTEGER NOT NULL DEFAULT 0,
            script_style VARCHAR(50),
            script_id UUID,
            script_data JSON DEFAULT '{}',
            video_index INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            video_url TEXT,
            thumbnail_url TEXT,
            duration INTEGER,
            course_media_id BIGINT,
            error_message TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
