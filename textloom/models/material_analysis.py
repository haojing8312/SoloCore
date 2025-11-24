from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    """分析状态枚举"""

    PENDING = "pending"  # 待分析
    PROCESSING = "processing"  # 分析中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class QualityLevel(str, Enum):
    """质量等级枚举"""

    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    AVERAGE = "average"  # 一般
    POOR = "poor"  # 较差


class MaterialAnalysisBase(BaseModel):
    """素材分析基础模型"""

    media_item_id: Optional[UUID] = Field(None, description="关联的媒体项目ID")
    original_url: Optional[str] = Field(None, description="原始URL")
    file_url: Optional[str] = Field(None, description="云存储URL")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小")
    analysis_status: AnalysisStatus = Field(
        default=AnalysisStatus.PENDING, description="分析状态"
    )

    # AI分析结果
    description: Optional[str] = Field(None, description="AI生成的内容描述")
    tags: List[str] = Field(default=[], description="内容标签列表")
    quality_level: Optional[QualityLevel] = Field(None, description="质量等级")
    quality_score: Optional[float] = Field(
        None, ge=0, le=100, description="质量评分(0-100)"
    )

    # 上下文分析结果
    contextual_description: Optional[str] = Field(
        None, description="基于上下文的内容描述"
    )
    contextual_purpose: Optional[str] = Field(
        None, description="基于上下文推断的用途和目的"
    )
    semantic_relevance: Optional[float] = Field(
        None, ge=0, le=100, description="与上下文的语义相关性评分"
    )
    content_role: Optional[str] = Field(
        None, description="在内容中的作用角色(例如：主要展示、辅助说明、案例演示等)"
    )

    # 技术信息
    resolution: Optional[str] = Field(None, description="分辨率")
    duration: Optional[float] = Field(None, description="时长(秒)")
    file_format: Optional[str] = Field(None, description="文件格式")

    # 云存储信息
    cloud_url: Optional[str] = Field(None, description="云存储公网URL")
    upload_status: str = Field(default="pending", description="上传状态")

    # 创作辅助
    voiceover_script: Optional[str] = Field(None, description="口播稿建议")
    contextual_voiceover_script: Optional[str] = Field(
        None, description="基于上下文的口播稿建议"
    )
    usage_suggestions: List[str] = Field(default=[], description="使用建议")

    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")


class MaterialAnalysisCreate(MaterialAnalysisBase):
    """创建素材分析的请求模型"""

    pass


class MaterialAnalysisUpdate(BaseModel):
    """更新素材分析的请求模型"""

    analysis_status: Optional[AnalysisStatus] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    quality_level: Optional[QualityLevel] = None
    quality_score: Optional[float] = None

    # 上下文分析字段
    contextual_description: Optional[str] = None
    contextual_purpose: Optional[str] = None
    semantic_relevance: Optional[float] = None
    content_role: Optional[str] = None

    resolution: Optional[str] = None
    duration: Optional[float] = None
    file_format: Optional[str] = None
    cloud_url: Optional[str] = None
    upload_status: Optional[str] = None
    voiceover_script: Optional[str] = None
    contextual_voiceover_script: Optional[str] = None
    usage_suggestions: Optional[List[str]] = None
    error_message: Optional[str] = None


class MaterialAnalysis(MaterialAnalysisBase):
    """素材分析模型"""

    id: UUID = Field(default_factory=uuid4, description="分析记录ID")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    analyzed_at: Optional[datetime] = Field(None, description="分析完成时间")

    # 原始AI响应（用于调试）
    raw_ai_response: Optional[str] = Field(None, description="原始AI响应内容")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174001",
                "media_item_id": "123e4567-e89b-12d3-a456-426614174000",
                "analysis_status": "completed",
                "description": "一张美丽的自然风景照片，展示了蓝天白云下的绿色草原",
                "tags": ["自然", "风景", "草原", "蓝天", "白云"],
                "quality_level": "good",
                "quality_score": 85.5,
                "resolution": "1920x1080",
                "file_format": "JPEG",
                "cloud_url": "https://example.com/images/photo.jpg",
                "upload_status": "completed",
                "voiceover_script": "这片绿色的草原在蓝天白云的映衬下显得格外美丽",
                "usage_suggestions": ["可用作背景素材", "适合自然主题视频"],
                "created_at": "2024-01-01T00:00:00Z",
                "analyzed_at": "2024-01-01T00:01:00Z",
            }
        }


class MaterialAnalysisInDB(MaterialAnalysis):
    """数据库中的素材分析模型"""

    pass


# 视频关键帧分析模型
class VideoKeyFrame(BaseModel):
    """视频关键帧模型"""

    timestamp: str = Field(..., description="时间戳(格式: HH:MM:SS)")
    frame_path: Optional[str] = Field(None, description="关键帧图片路径")
    cloud_url: Optional[str] = Field(None, description="关键帧云存储URL")
    description: Optional[str] = Field(None, description="关键帧内容描述")
    tags: List[str] = Field(default=[], description="关键帧标签")
    confidence_score: Optional[float] = Field(
        None, ge=0, le=1, description="置信度评分"
    )


class VideoAnalysis(BaseModel):
    """视频分析扩展模型"""

    analysis_id: UUID = Field(..., description="关联的分析记录ID")
    keyframes: List[VideoKeyFrame] = Field(default=[], description="关键帧列表")
    scene_changes: List[str] = Field(default=[], description="场景变化时间点")
    dominant_colors: List[str] = Field(default=[], description="主要颜色")
    motion_intensity: Optional[str] = Field(
        None, description="运动强度(low/medium/high)"
    )
    audio_features: Optional[Dict[str, Any]] = Field(None, description="音频特征")


# 分析统计模型
class AnalysisStats(BaseModel):
    """分析统计模型"""

    total_analyses: int = Field(default=0, description="总分析数")
    pending_analyses: int = Field(default=0, description="待分析数")
    processing_analyses: int = Field(default=0, description="分析中数")
    completed_analyses: int = Field(default=0, description="已完成数")
    failed_analyses: int = Field(default=0, description="失败数")

    # 质量分布
    excellent_count: int = Field(default=0, description="优秀质量数量")
    good_count: int = Field(default=0, description="良好质量数量")
    average_count: int = Field(default=0, description="一般质量数量")
    poor_count: int = Field(default=0, description="较差质量数量")

    # 上传统计
    uploaded_count: int = Field(default=0, description="已上传云存储数量")
    upload_failed_count: int = Field(default=0, description="上传失败数量")
