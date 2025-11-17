# Editly 开源视频引擎 - 快速开始

> 🎬 5 分钟快速部署开源视频合成引擎

---

## 🚀 一键部署

### Windows

```bash
cd textloom
scripts\setup_editly.bat
```

### macOS / Linux

```bash
cd textloom
chmod +x scripts/setup_editly.sh
./scripts/setup_editly.sh
```

---

## 📦 手动安装

### 1. 安装 Node.js

下载并安装 Node.js (v12.16.2+):
👉 https://nodejs.org/

验证安装:
```bash
node --version
```

### 2. 安装 FFmpeg

**Windows** (使用 Chocolatey):
```bash
choco install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

**Linux** (Ubuntu):
```bash
sudo apt-get install ffmpeg
```

验证安装:
```bash
ffmpeg -version
```

### 3. 安装 Editly

```bash
npm install -g editly
```

验证安装:
```bash
editly --version
```

---

## 🎯 快速测试

### 1. 准备测试素材

```bash
# 创建目录
mkdir -p workspace/materials/images

# 生成测试图片 (使用 FFmpeg)
ffmpeg -f lavfi -i color=c=blue:s=1080x1920:d=1 -frames:v 1 workspace/materials/images/sample1.jpg -y
ffmpeg -f lavfi -i color=c=red:s=1080x1920:d=1 -frames:v 1 workspace/materials/images/sample2.jpg -y
```

### 2. 运行测试脚本

```bash
cd textloom
python test_editly_engine.py
```

### 3. 查看生成的视频

```bash
# 视频输出路径
workspace/output/test_editly_output.mp4
```

---

## 💡 快速示例

### Python 代码

```python
from services.editly_video_engine import EditlyVideoEngine

# 创建引擎
engine = EditlyVideoEngine()

# 准备数据
script_data = {
    "scenes": [
        {
            "scene_id": 1,
            "narration": "欢迎来到 TextLoom",
            "material_id": "img_001",
            "duration": 5.0
        }
    ]
}

media_files = [
    {
        "id": "img_001",
        "file_url": "workspace/materials/images/sample1.jpg",
        "filename": "sample1.jpg"
    }
]

# 生成视频
result = engine.generate_video(
    script_data=script_data,
    media_files=media_files,
    output_path="output/my_video.mp4"
)

print(f"✅ 视频路径: {result['video_path']}")
```

---

## 📚 详细文档

完整文档请查看:
👉 [`docs/EDITLY_INTEGRATION_GUIDE.md`](docs/EDITLY_INTEGRATION_GUIDE.md)

---

## 🎯 三阶段路线图

### ✅ 阶段 1: 基础视频合成 (当前)
- 多场景合成
- 背景视频/图片
- 素材叠加
- 自定义字幕
- 音频混合

### 🔲 阶段 2: TTS 集成 (2-3 周)
- Piper TTS (开源)
- 音频缓存
- 音视频同步

### 🔲 阶段 3: 数字人集成 (3-4 周)
- HeyGen API (商业)
- SadTalker (开源备选)

---

## 💰 成本对比

| 方案 | 月成本 (1000 视频) | 说明 |
|------|------------------|------|
| 纯 video_merge API | $5000 | 现状 |
| **混合方案 (推荐)** | **$1500** | **节省 70%** |
| 纯开源 | $0 | 需 GPU 服务器 |

---

## ❓ 常见问题

### Q: 能完全替代 video_merge API 吗？

A: 阶段 1 可替代 70% 场景（无数字人、无 TTS 的视频）

### Q: 性能如何？

A: 约 2-3 分钟生成 1 分钟视频（1080p 30fps）

### Q: 如何集成到现有流程？

A: 参考文档中的"集成到现有流程"章节

---

## 🆘 获取帮助

- 📖 文档: `docs/EDITLY_INTEGRATION_GUIDE.md`
- 🐛 问题: 查看日志 `logs/app.log`
- 💬 支持: GitHub Issues

---

**开始构建吧！🚀**

```bash
# 一键部署
scripts/setup_editly.bat  # Windows
# 或
./scripts/setup_editly.sh  # macOS/Linux

# 运行测试
python test_editly_engine.py

# 生成你的第一个视频！
```
