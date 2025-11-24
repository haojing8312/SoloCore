from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ScriptStyle(str, Enum):
    """脚本风格枚举"""

    DEFAULT = "default"  # 默认风格
    PRODUCT_GEEK = "product_geek"  # 产品极客风格


class PersonaType(str, Enum):
    """人设类型枚举"""

    CUSTOM = "custom"  # 自定义人设


class GenerationStatus(str, Enum):
    """生成状态枚举"""

    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class PersonaBase(BaseModel):
    """用户人设基础模型"""

    name: str = Field(..., description="人设名称")
    persona_type: PersonaType = Field(..., description="人设类型")
    style: str = Field(..., description="风格描述")
    target_audience: str = Field(..., description="目标受众")
    characteristics: str = Field(..., description="特点描述")
    tone: str = Field(default="专业、通俗易懂", description="语调风格")
    keywords: List[str] = Field(default=[], description="关键词")
    custom_prompts: Dict[str, str] = Field(default={}, description="自定义提示词")


class PersonaCreate(PersonaBase):
    """创建人设请求模型"""

    pass


class PersonaUpdate(BaseModel):
    """更新人设请求模型"""

    name: Optional[str] = None
    style: Optional[str] = None
    target_audience: Optional[str] = None
    characteristics: Optional[str] = None
    tone: Optional[str] = None
    keywords: Optional[List[str]] = None
    custom_prompts: Optional[Dict[str, str]] = None


class Persona(PersonaBase):
    """人设模型"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    is_preset: bool = Field(default=False, description="是否为预设人设")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class PersonaInDB(Persona):
    """数据库中的人设模型"""

    pass


class ScriptContentBase(BaseModel):
    """脚本内容基础模型"""

    task_id: str = Field(..., description="任务ID")
    persona_id: Optional[str] = Field(None, description="人设ID")
    script_style: ScriptStyle = Field(..., description="脚本风格")
    generation_status: GenerationStatus = Field(
        default=GenerationStatus.PENDING, description="生成状态"
    )

    # 脚本内容
    titles: List[str] = Field(default=[], description="备选标题列表")
    narration: str = Field(default="", description="口播文案")
    material_mapping: Dict[str, Any] = Field(default={}, description="素材对应关系")
    description: str = Field(default="", description="视频简介")
    tags: List[str] = Field(default=[], description="标签列表")

    # 元数据
    estimated_duration: Optional[int] = Field(None, description="预计时长(秒)")
    word_count: int = Field(default=0, description="字数统计")
    material_count: int = Field(default=0, description="使用素材数量")

    # 生成信息
    generation_prompt: str = Field(default="", description="生成提示词")
    ai_response: str = Field(default="", description="AI原始响应")
    error_message: Optional[str] = Field(None, description="错误信息")


class ScriptContentCreate(BaseModel):
    """创建脚本内容请求模型"""

    task_id: str
    persona_id: Optional[str] = None
    script_style: ScriptStyle
    custom_persona: Optional[Dict[str, Any]] = None


class ScriptContentUpdate(BaseModel):
    """更新脚本内容请求模型"""

    titles: Optional[List[str]] = None
    narration: Optional[str] = None
    material_mapping: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    generation_status: Optional[GenerationStatus] = None
    error_message: Optional[str] = None


class ScriptContent(ScriptContentBase):
    """脚本内容模型"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScriptContentInDB(ScriptContent):
    """数据库中的脚本内容模型"""

    pass


class ScriptGenerationResult(BaseModel):
    """单个脚本生成结果模型"""

    script_id: str = Field(..., description="脚本ID")
    task_id: str = Field(..., description="任务ID")
    style: ScriptStyle = Field(..., description="脚本风格")
    persona_id: Optional[str] = Field(None, description="人设ID")
    titles: List[str] = Field(default=[], description="备选标题列表")
    narration: str = Field(default="", description="口播文案")
    material_mapping: Dict[str, Any] = Field(default={}, description="素材对应关系")
    description: str = Field(default="", description="视频简介")
    tags: List[str] = Field(default=[], description="标签列表")
    estimated_duration: int = Field(default=0, description="预计时长(秒)")
    word_count: int = Field(default=0, description="字数统计")
    material_count: int = Field(default=0, description="使用素材数量")
    generation_status: GenerationStatus = Field(..., description="生成状态")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")


class ScriptGenerationBatch(BaseModel):
    """批量脚本生成结果模型"""

    task_id: str = Field(..., description="任务ID")
    topic: str = Field(..., description="生成主题")
    persona_id: Optional[str] = Field(None, description="人设ID")
    requested_styles: List[ScriptStyle] = Field(..., description="请求的脚本风格列表")
    successful_results: List[ScriptGenerationResult] = Field(
        default=[], description="成功生成的结果"
    )
    failed_results: List[Dict[str, Any]] = Field(default=[], description="失败的结果")
    total_count: int = Field(..., description="总数量")
    success_count: int = Field(..., description="成功数量")
    failure_count: int = Field(..., description="失败数量")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")


class ScriptStats(BaseModel):
    """脚本统计模型"""

    total_scripts: int = Field(default=0, description="总脚本数")
    pending_scripts: int = Field(default=0, description="待处理脚本数")
    processing_scripts: int = Field(default=0, description="处理中脚本数")
    completed_scripts: int = Field(default=0, description="已完成脚本数")
    failed_scripts: int = Field(default=0, description="失败脚本数")

    # 按风格统计
    style_distribution: Dict[str, int] = Field(default={}, description="风格分布")

    # 按人设统计
    persona_usage: Dict[str, int] = Field(default={}, description="人设使用统计")

    # 质量统计
    average_word_count: float = Field(default=0.0, description="平均字数")
    average_duration: float = Field(default=0.0, description="平均时长")
    average_material_count: float = Field(default=0.0, description="平均素材数量")


# 预设人设配置
PRESET_PERSONAS = {}


class ScriptGenerationRequest(BaseModel):
    """脚本生成请求模型"""

    task_id: str
    topic: str
    persona_id: Optional[str] = None
    styles: Optional[List[ScriptStyle]] = None
    user_requirements: Optional[str] = None
    material_context: Optional[Dict[str, Any]] = None
