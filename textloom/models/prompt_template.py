from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TemplateType(str, Enum):
    """模板类型枚举"""

    SYSTEM = "system"  # 系统提示词
    SCRIPT_CONTENT = "script_content"  # 脚本内容生成
    METADATA = "metadata"  # 元数据生成
    COMMON = "common"  # 通用模板


class TemplateStyle(str, Enum):
    """模板风格枚举"""

    DEFAULT = "default"  # 默认
    PROFESSIONAL = "professional"  # 专业型
    VIRAL = "viral"  # 抖音爆款型
    BALANCED = "balanced"  # 平衡型


class PromptTemplateBase(BaseModel):
    """提示词模板基础模型"""

    name: str = Field(..., description="模板名称")
    template_type: TemplateType = Field(..., description="模板类型")
    template_style: TemplateStyle = Field(..., description="模板风格")
    content: str = Field(..., description="模板内容")
    description: str = Field(default="", description="模板描述")
    variables: List[str] = Field(default=[], description="模板变量列表")
    is_active: bool = Field(default=True, description="是否激活")
    version: str = Field(default="1.0", description="版本号")


class PromptTemplateCreate(PromptTemplateBase):
    """创建提示词模板请求模型"""

    pass


class PromptTemplateUpdate(BaseModel):
    """更新提示词模板请求模型"""

    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = None


class PromptTemplate(PromptTemplateBase):
    """提示词模板模型"""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class PromptTemplateInDB(PromptTemplate):
    """数据库中的提示词模板模型"""

    pass


# 默认提示词模板配置
DEFAULT_PROMPT_TEMPLATES = [
    # 系统提示词模板
    {
        "name": "默认系统提示词",
        "template_type": TemplateType.SYSTEM,
        "template_style": TemplateStyle.DEFAULT,
        "content": "你是一个专业的自媒体文案专家。",
        "description": "默认的系统提示词",
        "variables": [],
    },
    {
        "name": "专业型系统提示词",
        "template_type": TemplateType.SYSTEM,
        "template_style": TemplateStyle.PROFESSIONAL,
        "content": "你是一个专业的自媒体文案专家，擅长创作具有深度和专业性的技术内容。",
        "description": "专业型风格的系统提示词",
        "variables": [],
    },
    {
        "name": "抖音爆款型系统提示词",
        "template_type": TemplateType.SYSTEM,
        "template_style": TemplateStyle.VIRAL,
        "content": "你是一个专业的自媒体文案专家，擅长创作爆款短视频内容，语言生动有趣。",
        "description": "抖音爆款型风格的系统提示词",
        "variables": [],
    },
    {
        "name": "平衡型系统提示词",
        "template_type": TemplateType.SYSTEM,
        "template_style": TemplateStyle.BALANCED,
        "content": "你是一个专业的自媒体文案专家，擅长创作既专业又通俗易懂的内容。",
        "description": "平衡型风格的系统提示词",
        "variables": [],
    },
    # 脚本内容生成提示词模板
    {
        "name": "专业型脚本内容生成",
        "template_type": TemplateType.SCRIPT_CONTENT,
        "template_style": TemplateStyle.PROFESSIONAL,
        "content": """风格要求：
- 使用专业术语和准确的技术描述，展现专业深度
- 深入分析技术原理和实现机制，提供独到见解
- 保持逻辑清晰，层次分明，有理有据
- 使用专业的语气和表达方式，建立权威感
- 尽量使用提供的所有素材，尤其是 GIF 动图或视频素材，以保证内容的详尽和可视化效果
- 在结尾提供进阶资源或深度思考
- 控制视频时长在300秒以内，内容密度高
- 在脚本中加入技术演示或案例分析环节""",
        "description": "专业型风格的脚本内容生成提示词",
        "variables": ["materials", "text_content"],
    },
    {
        "name": "抖音爆款型脚本内容生成",
        "template_type": TemplateType.SCRIPT_CONTENT,
        "template_style": TemplateStyle.VIRAL,
        "content": """风格要求：
- 使用超级夸张的开场白，如"震惊！这个AI模型太牛了！"
- 大量使用"超级牛掰"、"性价比炸裂"、"太厉害了吧"等夸张表达
- 将技术内容简化为3个超级吸引人的亮点
- 制造悬念和惊喜，保持高能量感
- 在结尾加入强烈的互动引导，如"不信你们试试看！"
- 最多使用10个素材，尽量使用 GIF 动图或视频素材，以保证内容的详尽和可视化效果
- 控制视频时长在60秒，节奏快速
- 在脚本中加入夸张的反应和表情描述""",
        "description": "抖音爆款型风格的脚本内容生成提示词",
        "variables": ["materials", "text_content"],
    },
    {
        "name": "平衡型脚本内容生成",
        "template_type": TemplateType.SCRIPT_CONTENT,
        "template_style": TemplateStyle.BALANCED,
        "content": """风格要求：
- 使用直接、简洁的开场白，快速吸引观众注意力，如"朋友们好"、"今天给大家介绍"等亲切开场
- 在开头就提出一个令人惊讶或有价值的信息，制造好奇心
- 使用"超级牛掰"、"性价比炸裂"等生动表达，增强情感共鸣
- 将复杂技术简化为3-5个核心要点，用通俗易懂的语言解释
- 在结尾加入互动引导，如"资料已放到知识库"、"点赞关注，持续分享"等
- 加入一些独家见解或个人观点，展现专业深度
- 最多使用10个素材，尽量使用 GIF 动图或视频素材，以保证内容的详尽和可视化效果
- 控制视频时长在90秒，保持节奏紧凑""",
        "description": "平衡型风格的脚本内容生成提示词",
        "variables": ["materials", "text_content"],
    },
    # 通用脚本内容生成提示词
    {
        "name": "通用脚本内容生成",
        "template_type": TemplateType.COMMON,
        "template_style": TemplateStyle.DEFAULT,
        "content": """要求：
1. 创建一个符合指定风格和时长的口播文案，分为合适的段落
2. 每个段落后标注应该使用的素材，以及素材对应的口播语句
3. 使用"素材1"、"素材2"等标识符标识引用的素材
4. 每个素材后必须添加"素材对应文案"，明确指出素材展示时对应的口播内容

输出格式：
```
## 口播文案

### [场景标题1]
[口播文案内容...]
[素材: 素材1]
[素材对应文案: 这个素材展示时，我正在说"...这句话..."]

### [场景标题2]
[口播文案内容...]
[素材: 素材3]
[素材对应文案: 这个素材展示时，我正在说"...这句话..."]

### [场景标题...]
[口播文案内容...]
[素材: 素材5]
[素材对应文案: 这个素材展示时，我正在说"...这句话..."]

### 结尾
[口播文案内容...]
[素材: 素材1]
[素材对应文案: 这个素材展示时，我正在说"...这句话..."]
```

注意：
1. 只有在需要展示素材时才标注素材，不是每句话都需要对应素材
2. 请使用"素材1"、"素材2"等标识符引用素材，不要直接使用路径
3. 素材对应文案必须是口播文案中的一部分，确保素材展示时，口播内容与素材对应文案完全一致
4. 口播文案中应包含素材对应文案的内容，使整个脚本连贯一致""",
        "description": "通用的脚本内容生成提示词",
        "variables": ["materials", "text_content", "style_requirements"],
    },
    # 元数据生成提示词模板
    {
        "name": "专业型元数据生成",
        "template_type": TemplateType.METADATA,
        "template_style": TemplateStyle.PROFESSIONAL,
        "content": """风格要求：
- 标题要专业且有吸引力，突出技术价值
- 简介要深入、专业，包含技术亮点和应用价值
- 标签要包含专业术语和技术领域关键词""",
        "description": "专业型风格的元数据生成提示词",
        "variables": ["script_content", "text_content"],
    },
    {
        "name": "抖音爆款型元数据生成",
        "template_type": TemplateType.METADATA,
        "template_style": TemplateStyle.VIRAL,
        "content": """风格要求：
- 标题必须使用惊叹词、数字或对比元素，制造强烈好奇心
- 简介要夸张、吸引人，制造悬念
- 标签要包含热门话题和吸引眼球的关键词""",
        "description": "抖音爆款型风格的元数据生成提示词",
        "variables": ["script_content", "text_content"],
    },
    {
        "name": "平衡型元数据生成",
        "template_type": TemplateType.METADATA,
        "template_style": TemplateStyle.BALANCED,
        "content": """风格要求：
- 标题要有爆点，可以使用数字、惊叹词或对比元素
- 简介要简洁明了，突出核心价值
- 标签要覆盖技术领域和热门话题""",
        "description": "平衡型风格的元数据生成提示词",
        "variables": ["script_content", "text_content"],
    },
    # 通用元数据生成提示词
    {
        "name": "通用元数据生成",
        "template_type": TemplateType.COMMON,
        "template_style": TemplateStyle.DEFAULT,
        "content": """请生成：
1. 5个符合指定风格的备选标题
2. 视频简介（简洁有力，可包含参考内容来源如文章地址、GitHub地址等）
3. 最多10个相关话题标签（带#号，用空格分隔）

输出格式：
```
## 备选标题
1. [标题1]
2. [标题2]
3. [标题3]
4. [标题4]
5. [标题5]

## 视频简介
[视频简介内容]

## 标签
#标签1 #标签2 #标签3 ...
```""",
        "description": "通用的元数据生成提示词",
        "variables": ["script_content", "text_content", "style_requirements"],
    },
]
