from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VideoProjectStatus(str, Enum):
    """视频项目状态枚举"""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoProjectBase(BaseModel):
    """视频项目基础模型"""

    title: str = Field(..., description="视频项目标题", min_length=1, max_length=200)
    status: VideoProjectStatus = Field(
        default=VideoProjectStatus.PROCESSING, description="项目状态"
    )
    video_url: Optional[str] = Field(None, description="视频文件URL")


class VideoProjectCreate(VideoProjectBase):
    """创建视频项目模型"""

    pass


class VideoProjectUpdate(BaseModel):
    """更新视频项目模型"""

    title: Optional[str] = Field(
        None, description="视频项目标题", min_length=1, max_length=200
    )
    status: Optional[VideoProjectStatus] = Field(None, description="项目状态")
    video_url: Optional[str] = Field(None, description="视频文件URL")


class VideoProject(VideoProjectBase):
    """视频项目响应模型"""

    id: UUID = Field(default_factory=uuid4, description="项目唯一标识符")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "title": "我的视频项目",
                "status": "processing",
                "video_url": "https://example.com/video.mp4",
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2023-12-01T10:00:00",
            }
        }


class VideoProjectInDB(VideoProject):
    """数据库中的视频项目模型"""

    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="更新时间"
    )
