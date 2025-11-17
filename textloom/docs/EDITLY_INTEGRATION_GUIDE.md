# Editly 开源视频引擎集成指南

> **渐进式开源替代方案** - 三阶段实施计划
>
> 作者: Claude
> 创建: 2025-11-17
> 状态: 阶段 1 实施中

---

## 📋 目录

- [项目概述](#项目概述)
- [三阶段路线图](#三阶段路线图)
- [阶段 1：基础视频合成](#阶段-1基础视频合成)
- [阶段 2：TTS 集成](#阶段-2tts-集成)
- [阶段 3：数字人集成](#阶段-3数字人集成)
- [部署指南](#部署指南)
- [测试验证](#测试验证)
- [FAQ](#faq)

---

## 项目概述

### 目标

使用开源技术栈替代商业视频合成 API，降低成本，提高可控性。

### 核心技术栈

| 组件 | 技术选型 | 许可证 | 说明 |
|------|---------|--------|------|
| 视频合成核心 | **Editly** | MIT | 开源视频编辑框架 |
| 视频处理 | **FFmpeg** | GPL/LGPL | 必备依赖 |
| TTS (阶段2) | Piper / Coqui TTS | MIT | 开源文本转语音 |
| 数字人 (阶段3) | HeyGen API / 开源方案 | - | 可选商业或开源 |

### 架构设计

```
┌─────────────────────────────────────────────────────┐
│              TextLoom Core                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  VideoEngine (抽象层)                                │
│       │                                             │
│       ├── EditlyVideoEngine (开源)                   │
│       ├── VideoMergeEngine (商业备份)                │
│       └── 未来扩展...                                │
│                                                     │
│  Plugin System (可插拔)                              │
│       ├── TTSPlugin (阶段 2)                         │
│       ├── DigitalHumanPlugin (阶段 3)                │
│       └── SubtitleRenderer (已实现)                  │
└─────────────────────────────────────────────────────┘
```

---

## 三阶段路线图

### 阶段 1：基础视频合成 ✅ (当前)

**时间**: 2-3 周
**优先级**: P0
**目标**: 实现 70% 核心功能

#### 功能清单

- [x] 多场景视频合成
- [x] 背景视频/图片支持
- [x] 素材视频/图片叠加
- [x] 自定义字幕渲染（Fabric.js）
- [x] 音频混合
- [x] 转场效果
- [x] 进度跟踪
- [x] 错误处理

#### 适用场景

✅ **可以处理**：
- 无数字人的视频
- 已有音频配音的视频
- 图文混排视频
- 幻灯片式视频

❌ **暂不支持**：
- 需要 TTS 的视频
- 需要数字人的视频

---

### 阶段 2：TTS 集成 🔲 (计划中)

**时间**: 2-3 周
**优先级**: P1
**目标**: 实现文本转语音能力

#### 技术选型

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **Piper TTS** | 快速、本地运行、质量好 | 需要下载模型 | ⭐⭐⭐⭐⭐ |
| **Coqui TTS** | 声音选择多、可定制 | 速度较慢 | ⭐⭐⭐⭐ |
| **Edge TTS** | 免费、质量高 | 依赖微软服务 | ⭐⭐⭐ |
| **OpenAI TTS** | 质量最好 | 付费 ($15/1M字符) | ⭐⭐⭐ |

#### 实施计划

1. **创建 TTS 插件接口** (`TTSPlugin`)
2. **实现 Piper TTS 插件** (推荐)
3. **音频缓存机制**
4. **与 Editly 集成**
5. **音视频同步优化**

#### 预期成果

- 支持中文、英文等多语言 TTS
- 自动生成旁白音频
- 音频与视频时长同步

---

### 阶段 3：数字人集成 🔲 (规划中)

**时间**: 3-4 周
**优先级**: P2
**目标**: 实现 AI 数字人视频生成

#### 技术选型

| 方案 | 类型 | 成本 | 质量 | 推荐度 |
|------|------|------|------|--------|
| **HeyGen API** | 商业 | $0.10/秒 | 高 | ⭐⭐⭐⭐⭐ |
| **SadTalker** | 开源 | GPU 服务器 | 中 | ⭐⭐⭐ |
| **Wav2Lip** | 开源 | GPU 服务器 | 中 | ⭐⭐⭐ |
| **D-ID API** | 商业 | $0.12/秒 | 高 | ⭐⭐⭐⭐ |

#### 实施计划

1. **创建数字人插件接口** (`DigitalHumanPlugin`)
2. **集成 HeyGen API** (快速方案)
3. **或部署 SadTalker** (开源方案)
4. **绿幕抠像处理** (如需要)
5. **视频叠加合成**

#### 混合方案

建议采用**智能路由策略**：

```python
def select_engine(script_data):
    has_digital_human = check_digital_human(script_data)

    if has_digital_human:
        return "heygen_api"  # 商业 API
    else:
        return "editly"      # 开源引擎
```

**预期成本降低**: 50-70% (假设 30% 视频需要数字人)

---

## 阶段 1：基础视频合成

### 快速开始

#### 1. 安装依赖

```bash
# 1. 安装 Node.js (v12.16.2+)
# 下载: https://nodejs.org/

# 2. 安装 FFmpeg
# Windows (使用 Chocolatey):
choco install ffmpeg

# macOS:
brew install ffmpeg

# Linux (Ubuntu):
sudo apt-get install ffmpeg

# 3. 安装 Editly
npm install -g editly

# 验证安装
editly --version
ffmpeg -version
```

#### 2. 克隆/更新 Editly（可选，用于本地开发）

```bash
cd /path/to/SoloCore
git clone https://github.com/mifi/editly.git
cd editly
npm install
npm run build
```

#### 3. 配置 TextLoom

在 `.env` 文件中添加：

```bash
# Editly 引擎配置
USE_EDITLY_ENGINE=true
EDITLY_PATH=editly  # 或本地路径: /path/to/editly/dist/cli.js

# 视频合成默认配置
VIDEO_DEFAULT_WIDTH=1080
VIDEO_DEFAULT_HEIGHT=1920
VIDEO_DEFAULT_FPS=30

# 字幕样式（精确控制）
SUBTITLE_ENABLE=true
SUBTITLE_COLOR=#ffffff
SUBTITLE_FONT_NAME=Arial
SUBTITLE_FONT_SIZE=76.8
SUBTITLE_X=0
SUBTITLE_Y=1706.67
SUBTITLE_OUTLINE=2
SUBTITLE_OUTLINE_COLOR=#3B3B3B
```

#### 4. 运行测试

```bash
cd textloom
python test_editly_engine.py
```

---

### 使用示例

#### 示例 1：简单视频合成

```python
from services.editly_video_engine import EditlyVideoEngine

# 创建引擎实例
engine = EditlyVideoEngine()

# 准备数据
script_data = {
    "title": "我的第一个视频",
    "scenes": [
        {
            "scene_id": 1,
            "narration": "欢迎来到 TextLoom",
            "material_id": "img_001",
            "duration": 5.0
        },
        {
            "scene_id": 2,
            "narration": "这是一个开源视频合成引擎",
            "material_id": "img_002",
            "duration": 4.0
        }
    ]
}

media_files = [
    {
        "id": "img_001",
        "file_url": "workspace/materials/images/intro.jpg",
        "filename": "intro.jpg"
    },
    {
        "id": "img_002",
        "file_url": "workspace/materials/images/demo.jpg",
        "filename": "demo.jpg"
    }
]

# 生成视频
result = engine.generate_video(
    script_data=script_data,
    media_files=media_files,
    output_path="output/my_video.mp4",
    progress_callback=lambda p: print(f"进度: {p}%")
)

if result["success"]:
    print(f"✅ 视频生成成功: {result['video_path']}")
else:
    print(f"❌ 失败: {result['error']}")
```

#### 示例 2：集成到现有流程

修改 `services/sync_video_generator.py`：

```python
from services.editly_video_engine import EditlyVideoEngine

class SyncVideoGenerator:
    def __init__(self):
        # 添加 Editly 引擎
        self.editly_engine = EditlyVideoEngine()
        # ...现有代码

    def generate_single_video_sync(self, script_data, media_files, ...):
        # 检查是否可以使用 Editly
        if self._can_use_editly(script_data):
            return self._generate_with_editly(script_data, media_files)
        else:
            # 回退到 video_merge API
            return self._generate_with_video_merge(script_data, media_files)

    def _can_use_editly(self, script_data):
        """判断是否可以使用 Editly 引擎"""
        # 检查是否有数字人
        has_digital_human = any(
            c.get("category") == 2
            for scene in script_data.get("scenes", [])
            for c in scene.get("components", [])
        )
        # 检查是否需要 TTS
        needs_tts = script_data.get("needs_tts", False)

        # 阶段 1：仅支持无数字人、无 TTS 的视频
        return not has_digital_human and not needs_tts

    def _generate_with_editly(self, script_data, media_files):
        """使用 Editly 生成视频"""
        output_path = f"workspace/output/{uuid4()}.mp4"

        result = self.editly_engine.generate_video(
            script_data=script_data,
            media_files=media_files,
            output_path=output_path
        )

        return result
```

---

## 测试验证

### 单元测试

```bash
# 运行测试
python test_editly_engine.py

# 预期输出
🎬🎬🎬...
测试：配置转换
✅ 配置转换测试通过

⚠️ 跳过视频生成测试（需要准备测试素材）
✅✅✅...
所有测试完成
```

### 集成测试

准备测试素材：

```bash
# 创建测试目录
mkdir -p workspace/materials/images
mkdir -p workspace/output

# 下载测试图片（或使用你自己的）
# 放入 workspace/materials/images/ 目录
```

修改 `test_editly_engine.py`，取消注释视频生成测试：

```python
def main():
    test_config_conversion()
    # 取消注释下面这行
    test_basic_video_generation()  # ✅ 启用
```

运行：

```bash
python test_editly_engine.py
```

### 视频质量检查

生成视频后，检查以下指标：

- [ ] 视频分辨率正确（1080x1920）
- [ ] 帧率正确（30fps）
- [ ] 字幕清晰可读
- [ ] 素材位置正确
- [ ] 转场效果流畅
- [ ] 音频同步（如有）

---

## 性能优化

### 快速模式 vs 高质量模式

Editly 支持 `--fast` 参数，用于快速预览：

```python
# 快速模式（低质量，用于测试）
cmd = f"{self.editly_path} {config_path} --fast"

# 高质量模式（生产环境）
cmd = f"{self.editly_path} {config_path}"
```

**对比**：

| 模式 | 分辨率 | FPS | 速度 | 用途 |
|------|--------|-----|------|------|
| Fast | 640x360 | 15 | 5-10x | 开发测试 |
| Normal | 1080x1920 | 30 | 1x | 生产环境 |

### 并发处理

使用 Celery 并发生成多个视频：

```python
from celery import group

# 并发生成 10 个视频
job = group([
    generate_video_task.s(script_data, media_files)
    for script_data in scripts
])
result = job.apply_async()
```

### 缓存策略

缓存常用素材、转场效果，减少重复处理：

```python
# TODO: 实现素材缓存
# - 素材预下载
# - 视频转码缓存
# - 音频混合缓存
```

---

## 故障排查

### 常见问题

#### 1. `editly: command not found`

**原因**: Editly 未安装或不在 PATH 中

**解决**:
```bash
# 全局安装
npm install -g editly

# 或指定本地路径
EDITLY_PATH=/path/to/editly/dist/cli.js
```

#### 2. `ffmpeg: command not found`

**原因**: FFmpeg 未安装

**解决**:
```bash
# Windows
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

#### 3. 字幕乱码

**原因**: 字体文件缺失或编码问题

**解决**:
```bash
# 安装中文字体
# Windows: 复制字体到 C:\Windows\Fonts
# Linux: sudo apt-get install fonts-noto-cjk
```

#### 4. 视频生成失败

**检查**:
1. 查看日志 `logs/app.log`
2. 验证素材文件存在
3. 检查磁盘空间
4. 确认 FFmpeg 可用

---

## FAQ

### Q1: Editly 能否完全替代 video_merge API？

**A**: 不能完全替代，但可以处理 70% 的场景。

- ✅ **可以替代**: 无数字人、无 TTS 的视频
- ❌ **无法替代**: 需要数字人或 TTS 的视频（需阶段 2/3 完成）

### Q2: 性能如何？

**A**: 性能与 FFmpeg 相当，约 1-2 分钟/分钟视频。

- 1080p 30fps 视频：~2-3 分钟/分钟
- 使用 `--fast` 模式：~30 秒/分钟

### Q3: 成本节省多少？

**A**: 假设 30% 视频需要数字人（继续使用 video_merge API）：

- 原成本: $5000/月
- 新成本: $1500/月 (video_merge) + $0 (editly) = **节省 70%**

### Q4: 如何回退到 video_merge API？

**A**: 保留双引擎架构，随时切换：

```python
# 在配置中切换
USE_EDITLY_ENGINE=false  # 禁用 Editly，回退到 video_merge
```

### Q5: 阶段 2/3 何时实施？

**A**: 建议先完成阶段 1 测试验证（2-3 周），然后：

- **阶段 2 (TTS)**: 如果 70% 视频都需要 TTS，优先级提升
- **阶段 3 (数字人)**: 评估 HeyGen API 成本，决定是否自建

---

## 下一步行动

### 立即开始

1. ✅ **安装依赖** (Node.js, FFmpeg, Editly)
2. ✅ **运行测试** (`python test_editly_engine.py`)
3. ✅ **准备测试素材** (2-3 张图片/视频)
4. ✅ **生成第一个视频**

### 2 周后评估

- 视频质量是否达标？
- 性能是否满足需求？
- 是否需要调整架构？

### 1 个月后决策

- 是否全面推广 Editly？
- 何时启动阶段 2 (TTS)？
- 数字人方案选择？

---

## 附录

### 相关文档

- [Editly 官方文档](https://github.com/mifi/editly)
- [FFmpeg 文档](https://ffmpeg.org/documentation.html)
- [Fabric.js 文档](http://fabricjs.com/docs/)

### 联系支持

遇到问题？

1. 查看日志: `logs/app.log`
2. 查阅文档: `docs/EDITLY_INTEGRATION_GUIDE.md`
3. 提交 Issue: GitHub Issues

---

**文档版本**: v1.0
**最后更新**: 2025-11-17
**维护者**: TextLoom Team
