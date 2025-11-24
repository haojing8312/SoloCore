from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from sqlalchemy.orm import RelationshipProperty

# Type alias for SQLAlchemy base class
Base: DeclarativeMeta = declarative_base()


class UserTable(Base):
    """用户表"""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        {"schema": "textloom_core"},
    )

    # Primary key
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # User credentials
    username: Mapped[str] = Column(
        String(50), nullable=False, unique=True, comment="用户名"
    )
    email: Mapped[str] = Column(
        String(100), nullable=False, unique=True, comment="邮箱"
    )
    full_name: Mapped[Optional[str]] = Column(
        String(100), nullable=True, comment="全名"
    )
    hashed_password: Mapped[str] = Column(
        String(255), nullable=False, comment="哈希密码"
    )

    # User status
    is_active: Mapped[bool] = Column(Boolean, default=True, comment="是否激活")
    is_superuser: Mapped[bool] = Column(Boolean, default=False, comment="是否超级用户")
    is_verified: Mapped[bool] = Column(Boolean, default=False, comment="是否验证邮箱")

    # User configuration
    preferences: Mapped[Dict[str, Any]] = Column(
        JSON, default=dict, comment="用户偏好设置"
    )
    avatar_url: Mapped[Optional[str]] = Column(
        String(500), nullable=True, comment="头像URL"
    )
    timezone: Mapped[str] = Column(String(50), default="UTC", comment="时区")
    language: Mapped[str] = Column(String(10), default="zh-CN", comment="语言偏好")

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )
    last_login_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=True, comment="最后登录时间"
    )

    # JWT related
    token_version: Mapped[int] = Column(
        Integer, default=1, comment="Token版本号，用于刷新时废除旧token"
    )

    # API Key related
    api_key: Mapped[Optional[str]] = Column(
        String(255), nullable=True, unique=True, comment="API密钥，用于第三方系统认证"
    )
    api_key_enabled: Mapped[bool] = Column(
        Boolean, default=False, comment="是否启用API密钥认证"
    )
    user_type: Mapped[str] = Column(
        String(50), default="admin_user", comment="用户类型：api_user/admin_user"
    )
    api_quota_limit: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="API调用配额限制（每月）"
    )
    api_quota_used: Mapped[int] = Column(
        Integer, default=0, comment="已使用的API调用次数（当月）"
    )
    quota_reset_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=True, comment="配额重置时间"
    )

    # Relationships
    if TYPE_CHECKING:
        tasks: RelationshipProperty[List[TaskTable]]
    else:
        tasks = relationship("TaskTable", back_populates="creator", lazy="dynamic")


class RefreshTokenTable(Base):
    """刷新Token表"""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_jti", "jti"),
        {"schema": "textloom_core"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID",
    )
    jti = Column(String(36), nullable=False, unique=True, comment="JWT ID，用于撤销")
    token_hash = Column(String(255), nullable=False, comment="Token哈希值")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    is_revoked = Column(Boolean, default=False, comment="是否已撤销")
    device_info = Column(String(200), nullable=True, comment="设备信息")
    ip_address = Column(String(45), nullable=True, comment="IP地址")

    # 关系
    user = relationship("UserTable", backref="refresh_tokens")


class VideoProjectTable(Base):
    """视频项目表"""

    __tablename__ = "video_projects"
    __table_args__ = {"schema": "textloom_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, comment="项目标题")
    status = Column(
        String(50), nullable=False, default="processing", comment="项目状态"
    )
    video_url = Column(Text, nullable=True, comment="视频URL")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class TaskTable(Base):
    """任务表"""

    __tablename__ = "tasks"
    __table_args__ = {"schema": "textloom_core"}

    # Primary key
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Basic task info
    title: Mapped[str] = Column(String(255), nullable=False, comment="任务标题")
    description: Mapped[Optional[str]] = Column(Text, nullable=True, comment="任务描述")
    creator_id: Mapped[Optional[uuid.UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.users.id"),
        nullable=True,
        comment="创建者ID",
    )
    legacy_creator_id: Mapped[Optional[str]] = Column(
        String(100), nullable=True, comment="遗留创建者ID（向后兼容）"
    )
    task_type: Mapped[str] = Column(String(50), nullable=False, comment="任务类型")
    status: Mapped[str] = Column(
        String(50), nullable=False, default="pending", comment="任务状态"
    )
    progress: Mapped[int] = Column(
        Integer, nullable=False, default=0, comment="任务进度"
    )
    current_stage: Mapped[Optional[str]] = Column(
        String(50), nullable=True, comment="当前任务阶段"
    )

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=True, comment="更新时间"
    )
    started_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=True, comment="开始时间"
    )
    completed_at: Mapped[Optional[datetime]] = Column(
        DateTime, nullable=True, comment="完成时间"
    )

    # Error handling
    error_message: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="错误信息"
    )

    # Celery integration
    celery_task_id: Mapped[Optional[str]] = Column(
        String(255), nullable=True, comment="Celery任务ID"
    )
    worker_name: Mapped[Optional[str]] = Column(
        String(100), nullable=True, comment="执行任务的Worker名称"
    )
    retry_count: Mapped[int] = Column(Integer, default=0, comment="重试次数")
    max_retries: Mapped[int] = Column(Integer, default=3, comment="最大重试次数")
    error_traceback: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="详细错误堆栈信息"
    )

    # Script generation results
    script_title: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="脚本标题"
    )
    script_description: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="脚本描述"
    )
    script_narration: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="脚本旁白内容"
    )
    script_tags: Mapped[List[str]] = Column(JSON, default=list, comment="脚本标签")
    script_estimated_duration: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="脚本预计时长(秒)"
    )
    script_word_count: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="脚本字数"
    )
    script_material_count: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="脚本使用素材数量"
    )

    # Video generation results
    video_url: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="生成的视频URL"
    )
    thumbnail_url: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="视频缩略图URL"
    )
    video_duration: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="视频实际时长(秒)"
    )
    video_file_size: Mapped[Optional[int]] = Column(
        Integer, nullable=True, comment="视频文件大小(字节)"
    )
    video_quality: Mapped[Optional[str]] = Column(
        String(50), nullable=True, comment="视频质量"
    )
    course_media_id: Mapped[Optional[int]] = Column(
        BigInteger,
        nullable=True,
        comment="视频合成服务的媒体ID（使用BIGINT以兼容大数ID）",
    )

    # File and workspace
    file_path: Mapped[Optional[str]] = Column(Text, nullable=True, comment="文件路径")
    source_file: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="源文件路径"
    )
    workspace_dir: Mapped[Optional[str]] = Column(
        Text, nullable=True, comment="工作目录"
    )
    script_style_type: Mapped[Optional[str]] = Column(
        String(50), nullable=True, comment="脚本风格类型"
    )

    # Relationships
    if TYPE_CHECKING:
        creator: RelationshipProperty[Optional[UserTable]]
        media_items: RelationshipProperty[List[MediaItemTable]]
        material_analyses: RelationshipProperty[List[MaterialAnalysisTable]]
        script_contents: RelationshipProperty[List[ScriptContentTable]]
        sub_video_tasks: RelationshipProperty[List[SubVideoTaskTable]]
    else:
        creator = relationship("UserTable", back_populates="tasks")
        media_items = relationship(
            "MediaItemTable", back_populates="task", lazy="dynamic"
        )
        material_analyses = relationship(
            "MaterialAnalysisTable", back_populates="task", lazy="dynamic"
        )
        script_contents = relationship(
            "ScriptContentTable", back_populates="task", lazy="dynamic"
        )


class MediaItemTable(Base):
    """媒体素材表"""

    __tablename__ = "media_items"
    __table_args__ = {"schema": "textloom_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.tasks.id"),
        nullable=False,
        comment="关联任务ID",
    )
    filename = Column(String(255), nullable=False, comment="文件名")
    original_url = Column(Text, nullable=False, comment="原始URL")
    file_url = Column(Text, nullable=True, comment="云存储URL")
    local_path = Column(Text, nullable=True, comment="本地文件路径")
    cloud_url = Column(Text, nullable=True, comment="云存储URL(另一个)")
    file_size = Column(Integer, nullable=True, comment="文件大小(字节)")
    media_type = Column(String(50), nullable=False, comment="媒体类型")
    mime_type = Column(String(100), nullable=True, comment="MIME类型")
    # 新增：分辨率 (图片/视频专用，如 1920x1080)
    resolution = Column(String(20), nullable=True, comment="分辨率")
    duration = Column(Integer, nullable=True, comment="时长(秒)")
    # 下载和上传状态
    download_status = Column(String(20), nullable=True, default="pending", comment="下载状态")
    upload_status = Column(String(20), nullable=True, default="pending", comment="上传状态")
    downloaded_at = Column(DateTime, nullable=True, comment="下载完成时间")
    uploaded_at = Column(DateTime, nullable=True, comment="上传完成时间")
    error_message = Column(Text, nullable=True, comment="错误信息")
    # 三明治上下文字段
    context_before = Column(Text, nullable=True, comment="前一自然段落")
    context_after = Column(Text, nullable=True, comment="后一自然段落")
    surrounding_paragraph = Column(Text, nullable=True, comment="所在段落全文")
    caption = Column(Text, nullable=True, comment="图注/alt文本")
    position_in_content = Column(Integer, nullable=True, comment="在全文中的位置索引")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )

    # 关系
    task = relationship("TaskTable", back_populates="media_items")


class MaterialAnalysisTable(Base):
    """素材分析表"""

    __tablename__ = "material_analyses"
    __table_args__ = (
        UniqueConstraint(
            "task_id", "original_url", name="uq_material_analyses_task_original_url"
        ),
        {"schema": "textloom_core"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.tasks.id"),
        nullable=False,
        comment="关联任务ID",
    )
    # 可选的媒体项目外键，允许为空以兼容历史数据
    media_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.media_items.id"),
        nullable=True,
        comment="关联媒体项目ID",
    )
    original_url = Column(Text, nullable=False, comment="原始URL")
    file_url = Column(Text, nullable=True, comment="云存储URL")
    file_type = Column(String(50), nullable=False, comment="文件类型")
    file_size = Column(Integer, nullable=True, comment="文件大小")

    # 分析状态
    status = Column(String(50), nullable=False, default="pending", comment="分析状态")

    # 分析结果
    ai_description = Column(Text, nullable=True, comment="AI生成的描述")
    extracted_text = Column(Text, nullable=True, comment="提取的文本内容")
    key_objects = Column(JSON, default=list, comment="识别的关键对象")
    emotional_tone = Column(String(100), nullable=True, comment="情感基调")
    visual_style = Column(String(100), nullable=True, comment="视觉风格")
    quality_score = Column(Float, nullable=True, comment="质量评分")
    quality_level = Column(String(20), nullable=True, comment="质量级别")
    usage_suggestions = Column(JSON, default=list, comment="使用建议")

    # 视频特有字段
    duration = Column(Integer, nullable=True, comment="视频时长(秒)")
    fps = Column(Float, nullable=True, comment="帧率")
    resolution = Column(String(20), nullable=True, comment="分辨率")
    key_frames = Column(JSON, default=list, comment="关键帧信息")

    # 图像特有字段
    dimensions = Column(String(20), nullable=True, comment="图像尺寸")
    color_palette = Column(JSON, default=list, comment="主要颜色")

    # 元数据
    processing_time = Column(Float, nullable=True, comment="处理时间(秒)")
    model_version = Column(String(50), nullable=True, comment="使用的模型版本")
    error_message = Column(Text, nullable=True, comment="错误信息")

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at = Column(DateTime, nullable=True, comment="更新时间")

    # 关系
    task = relationship("TaskTable", back_populates="material_analyses")


class PersonaTable(Base):
    """用户人设表"""

    __tablename__ = "personas"
    __table_args__ = {"schema": "textloom_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, comment="人设名称")
    persona_type = Column(String(50), nullable=False, comment="人设类型")
    style = Column(String(100), nullable=True, comment="风格")
    target_audience = Column(String(100), nullable=True, comment="目标受众")
    characteristics = Column(Text, nullable=True, comment="特征描述")
    tone = Column(String(50), nullable=True, comment="语调")
    keywords = Column(Text, nullable=True, comment="关键词")
    custom_prompts = Column(JSON, default=dict, comment="自定义提示词")
    is_preset = Column(Boolean, default=False, comment="是否为预设人设")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class PromptTemplateTable(Base):
    """提示词模板表"""

    __tablename__ = "prompt_templates"
    __table_args__ = {"schema": "textloom_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_key = Column(String(100), nullable=False, unique=True, comment="模板键名")
    template_content = Column(Text, nullable=False, comment="模板内容")
    description = Column(Text, nullable=True, comment="模板描述")
    category = Column(String(50), nullable=True, comment="模板分类")
    template_type = Column(String(50), nullable=True, comment="模板类型")
    template_style = Column(String(50), nullable=True, comment="模板风格")
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )


class ScriptContentTable(Base):
    """脚本内容表"""

    __tablename__ = "script_contents"
    __table_args__ = {"schema": "textloom_core"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.tasks.id"),
        nullable=False,
        comment="关联任务ID",
    )
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("textloom_core.personas.id"),
        nullable=True,
        comment="关联人设ID",
    )
    script_style = Column(String(50), nullable=True, comment="脚本风格")
    generation_status = Column(
        String(50), nullable=False, default="pending", comment="生成状态"
    )

    # 脚本内容
    titles = Column(JSON, default=list, comment="标题列表")
    narration = Column(Text, nullable=True, comment="旁白内容")
    material_mapping = Column(JSON, default=dict, comment="素材映射")
    description = Column(Text, nullable=True, comment="脚本描述")
    tags = Column(JSON, default=list, comment="标签")
    # 新增：场景列表，保存每个场景及素材关联
    scenes = Column(JSON, default=list, comment="场景列表")

    # 元数据
    estimated_duration = Column(Integer, nullable=True, comment="预计时长(秒)")
    word_count = Column(Integer, nullable=True, comment="字数")
    material_count = Column(Integer, nullable=True, comment="素材数量")

    # 生成信息
    generation_prompt = Column(Text, nullable=True, comment="生成提示词")
    ai_response = Column(Text, nullable=True, comment="AI响应")
    error_message = Column(Text, nullable=True, comment="错误信息")

    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at = Column(DateTime, nullable=True, comment="更新时间")
    generated_at = Column(DateTime, nullable=True, comment="生成时间")

    # 关系
    task = relationship("TaskTable", back_populates="script_contents")
    persona = relationship("PersonaTable", backref="script_contents")
