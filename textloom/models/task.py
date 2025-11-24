from datetime import datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from models.material_analysis import MaterialAnalysisInDB


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    PARTIAL_SUCCESS = "partial_success"  # 部分成功（多子任务场景）
    CANCELLED = "cancelled"  # 已取消


class TaskType(str, Enum):
    """任务类型枚举"""

    MATERIAL_PROCESSING = "material_processing"  # 素材处理
    VIDEO_GENERATION = "video_generation"  # 视频生成
    CONTENT_ANALYSIS = "content_analysis"  # 内容分析
    TEXT_TO_VIDEO = "text_to_video"  # 文本转视频（完整流程）


class MediaType(str, Enum):
    """媒体类型枚举"""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


# 基础任务模型
class TaskBase(BaseModel):
    """任务基础模型"""

    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: TaskType = Field(..., description="任务类型")
    source_file: Optional[str] = Field(None, description="源文件路径")
    file_path: Optional[str] = Field(None, description="文件路径")
    workspace_dir: Optional[str] = Field(None, description="工作目录")
    script_style_type: Optional[str] = Field(
        None, description="脚本风格类型，如default或product_geek"
    )


class TaskCreate(TaskBase):
    """创建任务的请求模型"""

    pass


class TaskUpdate(BaseModel):
    """更新任务的请求模型"""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100, description="任务进度(0-100)")
    error_message: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    course_media_id: Optional[int] = None


class Task(TaskBase):
    """任务模型"""

    id: UUID = Field(default_factory=uuid4, description="任务ID")
    creator_id: Optional[str] = Field(None, description="创建者ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="任务进度(0-100)")
    current_stage: Optional[str] = Field(None, description="当前任务阶段")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")

    # Celery集成字段
    celery_task_id: Optional[str] = Field(None, description="Celery任务ID")
    worker_name: Optional[str] = Field(None, description="执行任务的Worker名称")
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")
    error_traceback: Optional[str] = Field(None, description="详细错误堆栈信息")

    # 脚本生成结果字段
    script_title: Optional[str] = Field(None, description="脚本标题")
    script_description: Optional[str] = Field(None, description="脚本描述")
    script_narration: Optional[str] = Field(None, description="脚本旁白内容")
    script_tags: Optional[List[str]] = Field(default=[], description="脚本标签")
    script_estimated_duration: Optional[int] = Field(
        None, description="脚本预计时长(秒)"
    )
    script_word_count: Optional[int] = Field(None, description="脚本字数")
    script_material_count: Optional[int] = Field(None, description="脚本使用素材数量")
    # 素材计数（仅接口返回用，不入库）
    markdown_count: Optional[int] = Field(None, description="提交的Markdown数量")
    image_count: Optional[int] = Field(None, description="提交的图片数量")
    video_count: Optional[int] = Field(None, description="提交的视频数量")

    # 视频生成结果字段（单视频模式，保持向后兼容）
    video_url: Optional[str] = Field(None, description="生成的视频URL")
    thumbnail_url: Optional[str] = Field(None, description="视频缩略图URL")
    video_duration: Optional[int] = Field(None, description="视频实际时长(秒)")
    video_file_size: Optional[int] = Field(None, description="视频文件大小(字节)")
    video_quality: Optional[str] = Field(None, description="视频质量")
    course_media_id: Optional[int] = Field(None, description="视频合成服务的媒体ID")

    # 多视频生成支持字段
    is_multi_video_task: bool = Field(default=False, description="是否为多视频生成任务")
    multi_video_count: Optional[int] = Field(None, description="多视频生成数量")
    multi_video_urls: Optional[List[str]] = Field(
        default=[], description="多视频URL列表"
    )
    sub_videos_completed: int = Field(default=0, description="已完成的子视频数量")
    multi_video_results: Optional[List[dict]] = Field(
        default=[], description="多视频生成结果列表"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "处理文章素材",
                "description": "提取并下载文章中的图片和视频",
                "task_type": "material_processing",
                "status": "processing",
                "progress": 50,
                "source_file": "/path/to/article.md",
                "workspace_dir": "/path/to/workspace",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:30:00Z",
            }
        }


class TaskInDB(Task):
    """数据库中的任务模型"""

    pass


# 媒体素材模型
class MediaItemBase(BaseModel):
    """媒体项目基础模型"""

    original_url: str = Field(..., description="原始URL")
    media_type: MediaType = Field(..., description="媒体类型")
    filename: Optional[str] = Field(None, description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    # 新增：分辨率 (图片/视频)，格式例如 "1920x1080"
    resolution: Optional[str] = Field(None, description="分辨率")

    # 上下文信息
    context_before: Optional[str] = Field(
        None, description="素材前面的文本内容(用于理解语义)"
    )
    context_after: Optional[str] = Field(
        None, description="素材后面的文本内容(用于理解语义)"
    )
    position_in_content: Optional[int] = Field(
        None, description="素材在文章中的位置索引"
    )
    surrounding_paragraph: Optional[str] = Field(
        None, description="素材所在段落的完整内容"
    )
    caption: Optional[str] = Field(None, description="素材图注/alt文本(如有)")


class MediaItemCreate(MediaItemBase):
    """创建媒体项目的请求模型"""

    task_id: UUID = Field(..., description="关联的任务ID")


class MediaItemUpdate(BaseModel):
    """更新媒体项目的请求模型"""

    local_path: Optional[str] = None
    cloud_url: Optional[str] = None
    upload_status: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    download_status: Optional[str] = None
    error_message: Optional[str] = None


class MediaItem(MediaItemBase):
    """媒体项目模型"""

    id: UUID = Field(default_factory=uuid4, description="媒体项目ID")
    task_id: UUID = Field(..., description="关联的任务ID")
    file_url: Optional[str] = Field(None, description="云存储URL")
    local_path: Optional[str] = Field(None, description="本地文件路径")
    cloud_url: Optional[str] = Field(None, description="云存储URL(废弃，使用file_url)")
    upload_status: str = Field(default="pending", description="云存储上传状态")
    download_status: str = Field(default="pending", description="下载状态")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    downloaded_at: Optional[datetime] = Field(None, description="下载完成时间")
    uploaded_at: Optional[datetime] = Field(None, description="上传完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174001",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "original_url": "https://example.com/image.jpg",
                "media_type": "image",
                "filename": "image_20240101_120000.jpg",
                "local_path": "/workspace/materials/images/image_20240101_120000.jpg",
                "file_size": 1024000,
                "mime_type": "image/jpeg",
                "download_status": "completed",
                "created_at": "2024-01-01T00:00:00Z",
                "downloaded_at": "2024-01-01T00:01:00Z",
            }
        }


class MediaItemInDB(MediaItem):
    """数据库中的媒体项目模型"""

    pass


# 任务统计模型
class TaskStats(BaseModel):
    """任务统计模型"""

    total_tasks: int = Field(default=0, description="总任务数")
    pending_tasks: int = Field(default=0, description="待处理任务数")
    processing_tasks: int = Field(default=0, description="处理中任务数")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")
    total_media_items: int = Field(default=0, description="总媒体项目数")
    downloaded_media_items: int = Field(default=0, description="已下载媒体项目数")
    average_processing_time: float = Field(default=0.0, description="平均处理时间(秒)")


# 子视频任务模型
class SubVideoTask(BaseModel):
    """子视频任务模型"""

    sub_task_id: str = Field(..., description="子任务唯一标识")
    parent_task_id: UUID = Field(..., description="父任务ID")
    script_style: str = Field(..., description="脚本风格")
    script_id: Optional[str] = Field(None, description="脚本ID")
    script_data: Optional[dict] = Field(None, description="脚本数据")
    video_url: Optional[str] = Field(None, description="生成的视频URL")
    thumbnail_url: Optional[str] = Field(None, description="视频缩略图URL")
    duration: Optional[int] = Field(None, description="时长(秒)")
    course_media_id: Optional[int] = Field(None, description="视频合成服务的媒体ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="子任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="子任务进度(0-100)")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    completed_at: Optional[datetime] = Field(None, description="完成时间")


# 任务详情模型（包含关联的媒体项目）
class TaskDetail(Task):
    """任务详情模型（包含媒体项目）"""

    media_items: List[MediaItem] = Field(default=[], description="关联的媒体项目列表")
    sub_video_tasks: List[SubVideoTask] = Field(
        default=[], description="子视频任务列表"
    )
    material_analyses: Optional[List[dict]] = Field(default=[], description="素材分析列表")
    script_content: Optional[dict] = Field(None, description="脚本内容")
