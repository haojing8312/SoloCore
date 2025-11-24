from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class VideoGenerationStatus(str, Enum):
    """视频生成状态枚举"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class VideoQuality(str, Enum):
    """视频质量枚举"""

    LOW = "low"  # 低质量 480p
    MEDIUM = "medium"  # 中等质量 720p
    HIGH = "high"  # 高质量 1080p
    ULTRA = "ultra"  # 超高质量 4K


class VideoGenerationRequest(BaseModel):
    """视频生成请求模型"""

    script_id: str = Field(..., description="脚本ID")
    title: str = Field(..., description="视频标题")
    narration: str = Field(..., description="口播稿内容")
    material_mapping: Dict[str, Any] = Field(..., description="素材对应关系")
    description: Optional[str] = Field(None, description="视频描述")
    tags: Optional[List[str]] = Field(default=[], description="视频标签")

    # 视频配置参数
    quality: VideoQuality = Field(default=VideoQuality.MEDIUM, description="视频质量")
    duration: Optional[int] = Field(None, description="期望时长(秒)")
    background_music: Optional[str] = Field(None, description="背景音乐类型")
    voice_style: Optional[str] = Field(default="natural", description="语音风格")
    subtitle_enabled: bool = Field(default=True, description="是否启用字幕")

    # 用户自定义参数
    custom_config: Optional[Dict[str, Any]] = Field(
        default={}, description="自定义配置"
    )


class VideoGenerationTask(BaseModel):
    """视频生成任务模型"""

    task_id: str = Field(default_factory=lambda: str(uuid4()), description="任务ID")
    script_id: str = Field(..., description="脚本ID")
    user_id: str = Field(..., description="用户ID")
    status: VideoGenerationStatus = Field(
        default=VideoGenerationStatus.PENDING, description="任务状态"
    )

    # 请求参数
    title: str = Field(..., description="视频标题")
    narration: str = Field(..., description="口播稿内容")
    material_mapping: Dict[str, Any] = Field(..., description="素材对应关系")
    description: Optional[str] = Field(None, description="视频描述")
    tags: List[str] = Field(default=[], description="视频标签")
    quality: VideoQuality = Field(default=VideoQuality.MEDIUM, description="视频质量")
    duration: Optional[int] = Field(None, description="期望时长(秒)")
    background_music: Optional[str] = Field(None, description="背景音乐类型")
    voice_style: str = Field(default="natural", description="语音风格")
    subtitle_enabled: bool = Field(default=True, description="是否启用字幕")
    custom_config: Dict[str, Any] = Field(default={}, description="自定义配置")

    # 任务进度信息
    progress: float = Field(default=0.0, description="任务进度 0-100")
    current_step: Optional[str] = Field(None, description="当前处理步骤")
    estimated_completion_time: Optional[datetime] = Field(
        None, description="预计完成时间"
    )

    # 结果信息
    video_url: Optional[str] = Field(None, description="生成的视频URL")
    thumbnail_url: Optional[str] = Field(None, description="视频缩略图URL")
    actual_duration: Optional[int] = Field(None, description="实际视频时长(秒)")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    started_at: Optional[datetime] = Field(None, description="开始处理时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


class VideoGenerationResult(BaseModel):
    """视频生成结果模型"""

    task_id: str = Field(..., description="任务ID")
    status: VideoGenerationStatus = Field(..., description="任务状态")
    progress: float = Field(..., description="任务进度")
    current_step: Optional[str] = Field(None, description="当前处理步骤")

    # 成功结果
    video_url: Optional[str] = Field(None, description="生成的视频URL")
    thumbnail_url: Optional[str] = Field(None, description="视频缩略图URL")
    actual_duration: Optional[int] = Field(None, description="实际视频时长(秒)")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")

    # 时间信息
    estimated_completion_time: Optional[datetime] = Field(
        None, description="预计完成时间"
    )
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class VideoGenerationStats(BaseModel):
    """视频生成统计模型"""

    total_tasks: int = Field(default=0, description="总任务数")
    pending_tasks: int = Field(default=0, description="待处理任务数")
    processing_tasks: int = Field(default=0, description="处理中任务数")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")
    cancelled_tasks: int = Field(default=0, description="取消任务数")

    # 质量分布统计
    quality_distribution: Dict[str, int] = Field(default={}, description="质量分布")

    # 性能统计
    average_processing_time: float = Field(
        default=0.0, description="平均处理时间(分钟)"
    )
    average_file_size: float = Field(default=0.0, description="平均文件大小(MB)")
    success_rate: float = Field(default=0.0, description="成功率")


class VideoGenerationTaskInDB(VideoGenerationTask):
    """数据库中的视频生成任务模型"""

    class Config:
        from_attributes = True
