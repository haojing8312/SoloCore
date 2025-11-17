# TextLoom 开源视频引擎实施路线图

> **完全开源方案** - 四阶段渐进式实施计划
>
> 作者: Claude + 用户
> 创建: 2025-11-17
> 状态: 准备启动

---

## 🎯 总体目标

使用开源技术栈替代商业视频合成 API，实现：
- ✅ **100% 开源** - 无商业 API 依赖
- ✅ **成本降低 90%+** - 仅需 GPU 服务器成本
- ✅ **完全可控** - 数据和技术自主

---

## 📊 四阶段实施计划

### 阶段 1️⃣：测试验证 Editly 基础功能

**时间**: 3-5 天
**目标**: 验证 Editly 能否满足基础视频合成需求
**优先级**: 🔴 P0 - 必须完成

#### 1.1 安装和配置

**任务清单**:
- [ ] 安装 Node.js (v14+ LTS)
- [ ] 安装 FFmpeg
- [ ] 安装 Editly 依赖
  ```bash
  cd editly
  npm install
  npm run build
  ```
- [ ] 验证 Editly CLI 可用
  ```bash
  node dist/cli.js --version
  ```

**验收标准**:
- Editly 命令能正常执行
- FFmpeg 版本 >= 4.0

#### 1.2 基础功能测试

**测试场景**:

##### 测试 1: 图片幻灯片
```json5
// test_slideshow.json5
{
  outPath: "output/test1_slideshow.mp4",
  width: 1080,
  height: 1920,
  fps: 30,
  clips: [
    {
      duration: 3,
      layers: [
        { type: "fill-color", color: "#0066cc" },
        {
          type: "title",
          text: "测试标题",
          textColor: "#ffffff"
        }
      ]
    },
    {
      duration: 3,
      layers: [
        {
          type: "image",
          path: "workspace/materials/images/sample1.jpg"
        }
      ]
    }
  ]
}
```

运行:
```bash
node editly/dist/cli.js test_slideshow.json5
```

**验收标准**:
- ✅ 视频生成成功
- ✅ 分辨率正确 (1080x1920)
- ✅ 帧率正确 (30fps)
- ✅ 标题清晰可读

##### 测试 2: 视频拼接 + 转场
```json5
// test_transitions.json5
{
  outPath: "output/test2_transitions.mp4",
  clips: [
    {
      duration: 2,
      transition: { name: "fade", duration: 0.5 },
      layers: [
        { type: "video", path: "test_video1.mp4" }
      ]
    },
    {
      duration: 2,
      transition: { name: "crosswarp", duration: 0.5 },
      layers: [
        { type: "video", path: "test_video2.mp4" }
      ]
    }
  ]
}
```

**验收标准**:
- ✅ 转场效果流畅
- ✅ 无黑屏或卡顿
- ✅ 时长准确

##### 测试 3: 自定义字幕 (Fabric.js)
```json5
// test_subtitle.json5
{
  outPath: "output/test3_subtitle.mp4",
  clips: [
    {
      duration: 5,
      layers: [
        { type: "fill-color", color: "#000000" },
        {
          type: "fabric",
          func: `
            ({ fabric, canvas, params }) => {
              const text = new fabric.Text('自定义字幕测试', {
                left: 100,
                top: 1700,
                fontSize: 60,
                fill: '#ffffff',
                stroke: '#000000',
                strokeWidth: 2
              });
              canvas.add(text);
            }
          `
        }
      ]
    }
  ]
}
```

**验收标准**:
- ✅ 字幕位置精确
- ✅ 字体大小正确
- ✅ 描边效果清晰

##### 测试 4: 音频混合
```json5
// test_audio.json5
{
  outPath: "output/test4_audio.mp4",
  audioFilePath: "background_music.mp3",
  clips: [
    {
      duration: 5,
      layers: [
        { type: "video", path: "test_video.mp4" }
      ]
    }
  ],
  keepSourceAudio: true,
  clipsAudioVolume: 0.7
}
```

**验收标准**:
- ✅ 背景音乐正常播放
- ✅ 原视频音频保留
- ✅ 音量平衡合理

#### 1.3 性能测试

**测试指标**:

| 视频规格 | 时长 | 预期生成时间 | 实际时间 | 通过 |
|---------|------|------------|---------|------|
| 1080x1920 @ 30fps | 30s | < 2 分钟 | _______ | ☐ |
| 1080x1920 @ 30fps | 60s | < 4 分钟 | _______ | ☐ |
| 720x1280 @ 30fps | 30s | < 1 分钟 | _______ | ☐ |

**硬件要求**:
- CPU: 4 核以上
- 内存: 8GB+
- 磁盘: 10GB+ 可用空间

#### 1.4 阶段 1 交付物

- [ ] Editly 功能测试报告 (Markdown)
- [ ] 5 个测试视频样本
- [ ] 性能基准数据
- [ ] 问题和限制清单

**Go/No-Go 决策**:
- ✅ **Go**: 所有基础测试通过，性能满足需求
- ❌ **No-Go**: 关键功能缺失或性能不达标 → 重新评估方案

---

### 阶段 2️⃣：开源 TTS 集成

**时间**: 1-2 周
**目标**: 集成开源 TTS，实现文本转语音
**优先级**: 🟡 P1

#### 2.1 TTS 技术选型

##### 方案 A: GPT-SoVITS (推荐 ⭐⭐⭐⭐⭐)

**项目地址**: https://github.com/RVC-Boss/GPT-SoVITS

**优点**:
- ✅ **中文效果极佳** - 专为中文优化
- ✅ **声音克隆** - 5 秒样本即可克隆声音
- ✅ **情感丰富** - 支持多种情感表达
- ✅ **活跃维护** - 社区活跃，更新频繁
- ✅ **本地部署** - 完全离线运行

**缺点**:
- ⚠️ 需要 GPU (推荐 NVIDIA RTX 3060+)
- ⚠️ 模型较大 (约 2GB)
- ⚠️ 推理速度中等 (1s 音频约需 2-3s)

**硬件要求**:
```
GPU: NVIDIA RTX 3060 (12GB VRAM) 或更高
CPU: 8 核+
内存: 16GB+
磁盘: 10GB+ (模型 + 缓存)
```

**安装步骤**:
```bash
# 1. 克隆项目
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS

# 2. 创建 Python 环境
conda create -n gptsovits python=3.10
conda activate gptsovits

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载预训练模型
python download_models.py

# 5. 启动 API 服务
python api.py
```

**API 示例**:
```python
import requests

response = requests.post(
    "http://localhost:9880/tts",
    json={
        "text": "这是一段测试语音",
        "text_language": "zh",
        "ref_audio_path": "reference.wav",  # 参考音频（声音克隆）
        "prompt_text": "参考音频的文本",
        "prompt_language": "zh",
        "top_k": 5,
        "top_p": 1,
        "temperature": 1
    }
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

##### 方案 B: Piper TTS (备选 ⭐⭐⭐⭐)

**项目地址**: https://github.com/rhasspy/piper

**优点**:
- ✅ **极快速度** - 实时率 > 1 (比实时快)
- ✅ **低资源** - CPU 即可运行
- ✅ **多语言** - 40+ 语言
- ✅ **模型小** - 10-50MB

**缺点**:
- ⚠️ 中文声音选择较少
- ⚠️ 情感表达一般
- ⚠️ 无声音克隆功能

**适用场景**: 对速度要求高，对声音质量要求一般

##### 方案 C: Coqui TTS (备选 ⭐⭐⭐)

**项目地址**: https://github.com/coqui-ai/TTS

**优点**:
- ✅ 多模型支持 (Tacotron2, VITS 等)
- ✅ 声音克隆
- ✅ 情感控制

**缺点**:
- ⚠️ 项目已停止维护 (2023年)
- ⚠️ 中文支持一般
- ⚠️ 安装复杂

**推荐指数**: 低

#### 2.2 GPT-SoVITS 集成方案（推荐）

##### 2.2.1 创建 TTS 插件接口

```python
# textloom/services/tts/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class TTSEngine(ABC):
    """TTS 引擎抽象基类"""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_config: Dict[str, Any],
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        合成语音

        Args:
            text: 要合成的文本
            voice_config: 声音配置（声音ID、参考音频等）
            output_path: 输出音频路径

        Returns:
            {
                "success": bool,
                "audio_path": str,
                "duration": float,
                "error": str (可选)
            }
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> list:
        """获取可用的声音列表"""
        pass
```

##### 2.2.2 实现 GPT-SoVITS 引擎

```python
# textloom/services/tts/gptsovits_engine.py
import requests
import time
from pathlib import Path
from typing import Dict, Any

from .base import TTSEngine
from utils.sync_logging import get_logger

logger = get_logger(__name__)


class GPTSoVITSEngine(TTSEngine):
    """GPT-SoVITS TTS 引擎"""

    def __init__(
        self,
        api_url: str = "http://localhost:9880",
        reference_audio_dir: str = "workspace/tts/references"
    ):
        self.api_url = api_url
        self.reference_audio_dir = Path(reference_audio_dir)
        self.reference_audio_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"GPT-SoVITS 引擎初始化: {api_url}")

    def synthesize(
        self,
        text: str,
        voice_config: Dict[str, Any],
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用 GPT-SoVITS 合成语音

        voice_config 格式:
        {
            "voice_id": "female_1",
            "ref_audio_path": "workspace/tts/references/female_1.wav",
            "ref_text": "参考音频的文本内容",
            "language": "zh",
            "top_k": 5,
            "top_p": 1.0,
            "temperature": 1.0
        }
        """
        try:
            logger.info(f"开始合成语音: {text[:50]}...")

            # 构建请求
            payload = {
                "text": text,
                "text_language": voice_config.get("language", "zh"),
                "ref_audio_path": voice_config.get("ref_audio_path"),
                "prompt_text": voice_config.get("ref_text", ""),
                "prompt_language": voice_config.get("language", "zh"),
                "top_k": voice_config.get("top_k", 5),
                "top_p": voice_config.get("top_p", 1.0),
                "temperature": voice_config.get("temperature", 1.0),
            }

            # 调用 API
            start_time = time.time()
            response = requests.post(
                f"{self.api_url}/tts",
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                raise RuntimeError(f"TTS API 调用失败: {response.status_code}")

            # 保存音频
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

            # 获取音频时长
            duration = self._get_audio_duration(output_path)
            elapsed = time.time() - start_time

            logger.info(
                f"✅ 语音合成成功: {output_path}, "
                f"时长: {duration}s, 耗时: {elapsed:.2f}s"
            )

            return {
                "success": True,
                "audio_path": output_path,
                "duration": duration,
                "synthesis_time": elapsed
            }

        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_available_voices(self) -> list:
        """获取可用的声音列表"""
        # 扫描参考音频目录
        voices = []
        for ref_audio in self.reference_audio_dir.glob("*.wav"):
            voice_id = ref_audio.stem
            voices.append({
                "voice_id": voice_id,
                "ref_audio_path": str(ref_audio),
                "language": "zh"  # 默认中文
            })
        return voices

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        import subprocess
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
```

##### 2.2.3 配置管理

在 `.env` 中添加:
```bash
# TTS 配置
TTS_ENGINE=gptsovits  # 或 piper, coqui
TTS_API_URL=http://localhost:9880
TTS_REFERENCE_AUDIO_DIR=workspace/tts/references

# GPT-SoVITS 配置
GPTSOVITS_TOP_K=5
GPTSOVITS_TOP_P=1.0
GPTSOVITS_TEMPERATURE=1.0
```

#### 2.3 声音库管理

##### 2.3.1 创建声音库

```bash
# 目录结构
workspace/tts/references/
├── male_1.wav           # 男声 1（参考音频）
├── male_1.txt           # 男声 1 参考文本
├── female_1.wav         # 女声 1
├── female_1.txt
├── child_1.wav          # 儿童声
├── child_1.txt
└── ...
```

##### 2.3.2 声音配置

```python
# textloom/config/voices.py
VOICE_LIBRARY = {
    "male_1": {
        "name": "男声-成熟稳重",
        "ref_audio_path": "workspace/tts/references/male_1.wav",
        "ref_text": "大家好，欢迎来到我的频道。",
        "language": "zh",
        "description": "适合新闻、教程类视频"
    },
    "female_1": {
        "name": "女声-温柔甜美",
        "ref_audio_path": "workspace/tts/references/female_1.wav",
        "ref_text": "今天给大家分享一个有趣的话题。",
        "language": "zh",
        "description": "适合生活、娱乐类视频"
    }
}
```

#### 2.4 集成到 Editly

```python
# textloom/services/editly_video_engine.py (更新)

class EditlyVideoEngine(VideoEngine):

    def __init__(self, tts_engine: Optional[TTSEngine] = None):
        self.tts_engine = tts_engine or self._create_default_tts_engine()
        # ...

    def _create_default_tts_engine(self):
        """创建默认 TTS 引擎"""
        from services.tts.gptsovits_engine import GPTSoVITSEngine
        return GPTSoVITSEngine()

    def generate_video(self, script_data, media_files, output_path, ...):
        # 1. 生成 TTS 音频
        audio_files = self._generate_audio_from_scenes(script_data["scenes"])

        # 2. 转换为 Editly 配置（添加音频）
        editly_config = self._convert_to_editly_config(
            script_data, media_files, output_path, audio_files
        )

        # 3. 执行 Editly
        # ...

    def _generate_audio_from_scenes(self, scenes):
        """为每个场景生成 TTS 音频"""
        audio_files = []

        for idx, scene in enumerate(scenes):
            narration = scene.get("narration", "").strip()
            if not narration:
                continue

            # 生成音频
            output_path = f"workspace/tts/output/scene_{idx+1}.wav"
            result = self.tts_engine.synthesize(
                text=narration,
                voice_config={
                    "voice_id": scene.get("voice_id", "female_1"),
                    "ref_audio_path": "workspace/tts/references/female_1.wav",
                    "ref_text": "参考文本",
                    "language": "zh"
                },
                output_path=output_path
            )

            if result["success"]:
                audio_files.append({
                    "scene_id": scene.get("scene_id"),
                    "audio_path": result["audio_path"],
                    "duration": result["duration"]
                })

        return audio_files
```

#### 2.5 阶段 2 测试

**测试场景**:

##### 测试 1: 单句 TTS
```python
from services.tts.gptsovits_engine import GPTSoVITSEngine

engine = GPTSoVITSEngine()
result = engine.synthesize(
    text="欢迎来到TextLoom，这是一个智能视频生成系统。",
    voice_config={
        "voice_id": "female_1",
        "ref_audio_path": "workspace/tts/references/female_1.wav",
        "ref_text": "参考文本",
        "language": "zh"
    },
    output_path="test_tts.wav"
)
print(result)
```

##### 测试 2: 多场景 TTS + Editly
```python
script_data = {
    "scenes": [
        {
            "scene_id": 1,
            "narration": "大家好，今天给大家介绍一个新产品。",
            "voice_id": "female_1",
            "duration": 5.0
        },
        {
            "scene_id": 2,
            "narration": "这个产品有三个主要特点。",
            "voice_id": "female_1",
            "duration": 4.0
        }
    ]
}

engine = EditlyVideoEngine()
result = engine.generate_video(
    script_data=script_data,
    media_files=[],
    output_path="test_tts_video.mp4"
)
```

#### 2.6 阶段 2 交付物

- [ ] GPT-SoVITS 部署文档
- [ ] TTS 插件代码
- [ ] 声音库（至少 3 个声音）
- [ ] 集成测试视频（3 个场景）
- [ ] 性能测试报告（TTS 速度）

---

### 阶段 3️⃣：TextLoom 适配 Editly

**时间**: 2-3 周
**目标**: 将 TextLoom 完全切换到 Editly 引擎
**优先级**: 🟡 P1

#### 3.1 架构调整

##### 3.1.1 双引擎架构（过渡期）

```python
# textloom/services/video_engine_factory.py

from enum import Enum
from typing import Optional

class VideoEngineType(Enum):
    EDITLY = "editly"
    VIDEO_MERGE = "video_merge"  # 商业 API (备份)

class VideoEngineFactory:
    """视频引擎工厂"""

    @staticmethod
    def create(
        engine_type: VideoEngineType,
        **kwargs
    ):
        if engine_type == VideoEngineType.EDITLY:
            from services.editly_video_engine import EditlyVideoEngine
            return EditlyVideoEngine(**kwargs)
        elif engine_type == VideoEngineType.VIDEO_MERGE:
            from services.sync_video_generator import SyncVideoGenerator
            return SyncVideoGenerator()
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")

# 使用
engine = VideoEngineFactory.create(
    VideoEngineType.EDITLY,
    tts_engine=tts_engine
)
```

##### 3.1.2 智能路由

```python
# textloom/services/video_engine_router.py

def select_video_engine(script_data: Dict) -> VideoEngineType:
    """
    智能选择视频引擎

    规则:
    1. 如果有数字人 → VIDEO_MERGE (阶段 4 前)
    2. 如果没有 TTS 支持 → VIDEO_MERGE
    3. 其他 → EDITLY
    """
    # 检查数字人
    has_digital_human = any(
        c.get("category") == 2
        for scene in script_data.get("scenes", [])
        for c in scene.get("components", [])
    )

    if has_digital_human:
        logger.info("检测到数字人，使用 VIDEO_MERGE 引擎")
        return VideoEngineType.VIDEO_MERGE

    # 检查 TTS
    has_tts = any(
        scene.get("narration", "").strip()
        for scene in script_data.get("scenes", [])
    )

    if has_tts and not settings.TTS_ENGINE:
        logger.warning("需要 TTS 但未配置，回退到 VIDEO_MERGE")
        return VideoEngineType.VIDEO_MERGE

    logger.info("使用 EDITLY 引擎")
    return VideoEngineType.EDITLY
```

#### 3.2 配置转换优化

##### 3.2.1 增强配置转换器

```python
# textloom/services/editly_config_converter.py

class EditlyConfigConverter:
    """TextLoom → Editly 配置转换器"""

    def convert(
        self,
        script_data: Dict,
        media_files: List[Dict],
        audio_files: List[Dict],
        output_path: str
    ) -> Dict:
        """完整配置转换"""

        editly_config = {
            "outPath": output_path,
            "width": settings.VIDEO_DEFAULT_WIDTH,
            "height": settings.VIDEO_DEFAULT_HEIGHT,
            "fps": 30,
            "clips": [],
            "audioTracks": []
        }

        # 转换场景
        for idx, scene in enumerate(script_data.get("scenes", [])):
            clip = self._convert_scene(
                scene, media_files, audio_files, idx
            )
            editly_config["clips"].append(clip)

        # 添加背景音乐
        if script_data.get("background_music"):
            editly_config["audioFilePath"] = script_data["background_music"]
            editly_config["loopAudio"] = True

        return editly_config

    def _convert_scene(self, scene, media_files, audio_files, idx):
        """转换单个场景"""
        # 详细实现...
```

#### 3.3 Celery 任务适配

```python
# textloom/tasks/video_generation_tasks.py (更新)

from services.video_engine_factory import VideoEngineFactory
from services.video_engine_router import select_video_engine

@celery_app.task(bind=True)
def generate_video_task(
    self,
    script_data: Dict,
    media_files: List[Dict],
    task_id: str,
    **kwargs
):
    """视频生成任务（支持双引擎）"""

    try:
        # 1. 选择引擎
        engine_type = select_video_engine(script_data)

        # 2. 创建引擎
        engine = VideoEngineFactory.create(engine_type)

        # 3. 生成视频
        result = engine.generate_video(
            script_data=script_data,
            media_files=media_files,
            output_path=f"workspace/output/{task_id}.mp4",
            progress_callback=lambda p: self.update_state(
                state='PROGRESS',
                meta={'progress': p}
            )
        )

        return result

    except Exception as e:
        logger.error(f"视频生成失败: {e}")
        raise
```

#### 3.4 阶段 3 测试

**完整端到端测试**:

```python
# tests/e2e/test_full_pipeline.py

def test_full_video_generation():
    """测试完整的视频生成流程"""

    # 准备数据
    script_data = {
        "title": "测试视频",
        "scenes": [
            {
                "scene_id": 1,
                "narration": "这是第一个场景",
                "material_id": "img_001",
                "voice_id": "female_1"
            },
            {
                "scene_id": 2,
                "narration": "这是第二个场景",
                "material_id": "img_002",
                "voice_id": "female_1"
            }
        ]
    }

    media_files = [
        {"id": "img_001", "file_url": "test1.jpg"},
        {"id": "img_002", "file_url": "test2.jpg"}
    ]

    # 执行生成
    task = generate_video_task.delay(script_data, media_files, "test_task")
    result = task.get(timeout=300)

    # 验证
    assert result["success"] == True
    assert Path(result["video_path"]).exists()
```

#### 3.5 阶段 3 交付物

- [ ] 双引擎架构代码
- [ ] 配置转换器
- [ ] Celery 任务适配
- [ ] 端到端测试套件
- [ ] 迁移文档
- [ ] 性能对比报告

---

### 阶段 4️⃣：数字人集成

**时间**: 3-4 周
**目标**: 集成数字人功能，实现完整视频生成
**优先级**: 🟢 P2

#### 4.1 数字人技术选型

##### 方案 A: HeyGen API (商业方案)

**注意**: HeyGen 是商业 API，不是开源的。

**价格**: 约 $0.10/秒视频
**优点**:
- ✅ 质量最高
- ✅ 稳定可靠
- ✅ API 简单

**缺点**:
- ❌ 付费服务
- ❌ 数据上传外部

**建议**: 如果预算允许，可作为首选。

##### 方案 B: SadTalker (开源 ⭐⭐⭐⭐)

**项目地址**: https://github.com/OpenTalker/SadTalker

**优点**:
- ✅ 完全开源
- ✅ 效果较好
- ✅ 本地部署

**缺点**:
- ⚠️ 需要 GPU (RTX 3090+)
- ⚠️ 生成速度慢 (1min 视频约需 5-10min)
- ⚠️ 质量不如商业方案

**硬件要求**:
```
GPU: NVIDIA RTX 3090 (24GB VRAM) 或更高
CPU: 16 核+
内存: 32GB+
```

##### 方案 C: Wav2Lip (开源 ⭐⭐⭐)

**项目地址**: https://github.com/Rudrabha/Wav2Lip

**优点**:
- ✅ 轻量级
- ✅ 速度较快
- ✅ 唇形同步准确

**缺点**:
- ⚠️ 需要预先录制视频
- ⚠️ 表情单一
- ⚠️ 分辨率有限

**推荐场景**: 对质量要求不高，追求速度

#### 4.2 推荐方案: SadTalker

##### 4.2.1 部署 SadTalker

```bash
# 1. 克隆项目
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker

# 2. 安装依赖
conda create -n sadtalker python=3.8
conda activate sadtalker
pip install -r requirements.txt

# 3. 下载模型
bash scripts/download_models.sh

# 4. 启动 API 服务 (自行封装)
python api_server.py  # 需要自己编写
```

##### 4.2.2 创建数字人插件

```python
# textloom/services/digital_human/sadtalker_engine.py

import requests
from pathlib import Path
from typing import Dict, Any

class SadTalkerEngine:
    """SadTalker 数字人引擎"""

    def __init__(self, api_url: str = "http://localhost:7860"):
        self.api_url = api_url

    def generate(
        self,
        source_image: str,
        audio_path: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成数字人视频

        Args:
            source_image: 人物图片路径
            audio_path: 音频路径
            output_path: 输出视频路径
        """
        try:
            # 调用 SadTalker API
            with open(source_image, "rb") as img_file:
                with open(audio_path, "rb") as audio_file:
                    response = requests.post(
                        f"{self.api_url}/generate",
                        files={
                            "source_image": img_file,
                            "driven_audio": audio_file
                        },
                        data={
                            "preprocess": "crop",
                            "still_mode": True,
                            "use_enhancer": True
                        },
                        timeout=600
                    )

            # 保存视频
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

            return {
                "success": True,
                "video_path": output_path
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

##### 4.2.3 集成到视频生成流程

```python
# textloom/services/editly_video_engine.py (更新)

class EditlyVideoEngine(VideoEngine):

    def __init__(
        self,
        tts_engine: Optional[TTSEngine] = None,
        digital_human_engine: Optional[Any] = None
    ):
        self.tts_engine = tts_engine
        self.digital_human_engine = digital_human_engine
        # ...

    def generate_video(self, script_data, ...):
        # 1. 生成 TTS 音频
        audio_files = self._generate_audio_from_scenes(...)

        # 2. 生成数字人视频（如果需要）
        digital_human_videos = self._generate_digital_human_videos(
            script_data["scenes"],
            audio_files
        )

        # 3. 使用数字人视频替换素材
        for scene, dh_video in zip(script_data["scenes"], digital_human_videos):
            if dh_video:
                scene["material_id"] = dh_video["video_id"]
                # 添加到 media_files
                media_files.append({
                    "id": dh_video["video_id"],
                    "file_url": dh_video["video_path"],
                    "filename": Path(dh_video["video_path"]).name
                })

        # 4. 转换为 Editly 配置
        # 5. 执行 Editly
        # ...

    def _generate_digital_human_videos(self, scenes, audio_files):
        """为需要数字人的场景生成视频"""
        results = []

        for scene, audio in zip(scenes, audio_files):
            if scene.get("use_digital_human"):
                result = self.digital_human_engine.generate(
                    source_image=scene.get("digital_human_image"),
                    audio_path=audio["audio_path"],
                    output_path=f"workspace/digital_human/{scene['scene_id']}.mp4"
                )
                results.append(result if result["success"] else None)
            else:
                results.append(None)

        return results
```

#### 4.3 阶段 4 测试

**测试场景**:

```python
# 测试数字人生成
script_data = {
    "scenes": [
        {
            "scene_id": 1,
            "narration": "大家好，我是数字人小助手。",
            "use_digital_human": True,
            "digital_human_image": "workspace/digital_human/avatar.png",
            "voice_id": "female_1"
        }
    ]
}

engine = EditlyVideoEngine(
    tts_engine=tts_engine,
    digital_human_engine=sadtalker_engine
)

result = engine.generate_video(
    script_data=script_data,
    media_files=[],
    output_path="test_digital_human.mp4"
)
```

#### 4.4 阶段 4 交付物

- [ ] SadTalker 部署文档
- [ ] 数字人插件代码
- [ ] 完整集成测试
- [ ] 数字人素材库（3-5 个角色）
- [ ] 性能和成本分析报告

---

## 📊 总体时间线

| 阶段 | 时间 | 累计 | 关键里程碑 |
|------|------|------|----------|
| 阶段 1 | 3-5 天 | 1 周 | ✅ Editly 可用 |
| 阶段 2 | 1-2 周 | 3 周 | ✅ TTS 集成 |
| 阶段 3 | 2-3 周 | 6 周 | ✅ TextLoom 迁移 |
| 阶段 4 | 3-4 周 | 10 周 | ✅ 数字人功能 |

**总计**: **8-10 周** (约 2-2.5 个月)

---

## 💰 成本分析

### 方案 A: 全开源 (推荐)

**一次性成本**:
- 开发成本: 2 人月 × $10,000 = **$20,000**

**月度成本** (GPU 服务器):
- GPU 服务器 (RTX 3090): **$300-500/月**
- 或云端 GPU (AWS p3.2xlarge): **$800-1200/月**

**年度总成本**: $20,000 + $6,000 = **$26,000**

### 方案 B: 混合方案

**月度成本**:
- TTS: 开源 (免费)
- 数字人: HeyGen API ($0.10/秒)
- 假设 30% 视频需要数字人，平均 30 秒
- 1000 视频/月 × 30% × 30 秒 × $0.10 = **$900/月**

**年度总成本**: $20,000 + $10,800 = **$30,800**

### 对比商业方案

**纯商业 API**:
- 月成本: **$5,000**
- 年成本: **$60,000**

**节省**: $60,000 - $26,000 = **$34,000/年** (**57% 节省**)

---

## 🎯 成功标准

### 阶段 1
- [ ] Editly 安装成功率 100%
- [ ] 基础测试全部通过
- [ ] 性能满足需求 (< 3min/1min 视频)

### 阶段 2
- [ ] TTS 质量评分 ≥ 4/5
- [ ] TTS 速度 < 5s/句
- [ ] 声音库 ≥ 3 个

### 阶段 3
- [ ] 迁移成功率 ≥ 95%
- [ ] 双引擎切换无缝
- [ ] 性能无明显下降

### 阶段 4
- [ ] 数字人质量可接受
- [ ] 生成速度 < 10min/1min 视频
- [ ] 整体成本降低 ≥ 50%

---

## 🚨 风险管理

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| GPU 资源不足 | 中 | 高 | 提前采购或租用云端 GPU |
| TTS 质量不达标 | 低 | 中 | 多方案对比测试 |
| 数字人效果差 | 中 | 高 | 保留 HeyGen 作为备选 |
| 开发周期超期 | 中 | 中 | 分阶段交付，优先核心功能 |

---

## 📝 下一步行动

### 本周 (Week 1)

**Day 1-2**:
- [ ] 安装 Node.js + FFmpeg
- [ ] 部署 Editly
- [ ] 运行第一个测试

**Day 3-5**:
- [ ] 完成 4 个基础测试
- [ ] 性能基准测试
- [ ] 编写测试报告

### 下周 (Week 2)

- [ ] 调研 GPT-SoVITS
- [ ] 部署 TTS 环境
- [ ] 初步集成测试

---

**准备好了吗？让我们从阶段 1 开始！** 🚀

运行这个命令启动第一阶段：
```bash
cd editly
npm install
npm run build
node dist/cli.js --version
```
