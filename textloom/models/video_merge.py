from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SubtitlesStyle(BaseModel):
    """字幕样式配置"""

    enable: bool = True
    color: str = "#ffffff"
    name: str = "DejaVu Sans"
    size: float = 76.8
    w: float = 1079.4666666666667
    h: float = 85.33333333333333
    x: float = 0
    y: float = 1706.6666666666667
    depth: int = 500
    style: Dict[str, Any] = {
        "borderStyle": True,
        "outline": 0,
        "outlineColor": "#3B3B3B",
    }


class AudioDriver(BaseModel):
    """音频驱动配置"""

    audioUrl: str = ""


class Background(BaseModel):
    """背景配置"""

    backgroundType: int = 1
    cover: str = ""
    depth: int = 0
    duration: int = 0
    entityId: str = ""
    height: int = 1920
    isCustome: bool = False
    pptRemark: str = ""  # 包含口播稿及素材标记
    src: str = ""
    width: int = 1080


class Component(BaseModel):
    """媒体组件"""

    businessId: str
    category: int  # 2=数字人, 9=视频素材
    cover: str = ""
    depth: int = 200
    digitbotType: int = 0
    entityId: str
    entityType: int = 0
    height: int
    marginLeft: int = 0
    marker: bool = False
    matting: int = 0
    name: str
    originHeight: int
    originWidth: int
    src: str
    status: int = 0
    top: int
    width: int
    style: str = ""


class TextDriver(BaseModel):
    """文本驱动配置"""

    pitch: float = 1.0
    speed: float = 1.0
    textJson: str  # 口播稿内容
    volume: float = 1.0


class Voice(BaseModel):
    """声音配置"""

    entityId: str
    name: str
    voiceId: int
    voiceType: int = 0


class Scene(BaseModel):
    """场景信息"""

    audioDriver: AudioDriver
    background: Background
    businessId: str
    components: List[Component]
    driverType: int = 1
    orderNo: int
    textDriver: TextDriver
    voice: Voice


class VideoMergeRequest(BaseModel):
    """视频合成请求"""

    accountId: int
    name: str = "未命名草稿"
    aspect: str = "9:16"
    duration: int = 0
    height: int = 1920
    width: int = 1080
    pageMode: int = 4
    matting: int = 1
    subtitlesStyle: SubtitlesStyle
    scenes: List[Scene]


class VideoMergeResponse(BaseModel):
    """视频合成响应"""

    success: bool
    courseMediaId: int


class SceneInfo(BaseModel):
    """场景信息的数据模型"""

    order_no: Optional[int] = 0
    subtitles_url: Optional[str] = None
    digital_human: Optional[str] = None
    ppt_images: Optional[str] = None
    duration: Optional[int] = 0


class MediaResultResponse(BaseModel):
    """媒体结果响应的数据模型"""

    courseMediaId: int
    status: int
    subtitles_url: Optional[str] = None
    merge_video: Optional[str] = None
    snapshot_url: Optional[str] = None
    duration: int
    completion_percentage: Optional[float] = 0.0
    failure_reasons: Optional[str] = None
    finish_time: Optional[str] = None
    scenes: Optional[List[SceneInfo]] = None
