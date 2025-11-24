# 动态字幕功能文档

## 概述

动态字幕功能基于简化的字幕渲染器实现（提取自pycaps核心功能），为生成的视频添加动态字幕效果，无需GPU依赖。

## 功能特性

- **外部字幕支持**: 支持SRT格式字幕文件，无需音频转录
- **多种样式模板**: 内置默认、现代、社交媒体等多种样式
- **丰富动画效果**: 支持淡入、上滑、弹出、打字机等动画
- **自定义样式**: 支持CSS自定义样式和配置
- **无缝集成**: 集成到现有视频生成流水线中
- **存储支持**: 支持本地、MinIO、华为OBS等存储方式

## 安装配置

### 1. 安装依赖

```bash
# 确保FFmpeg已安装并在PATH中
ffmpeg -version

# Ubuntu/Debian安装FFmpeg
sudo apt update && sudo apt install ffmpeg

# 系统依赖已通过uv自动管理
uv sync
```

### 2. 环境配置

在`.env`文件中添加以下配置：

```env
# 动态字幕配置
DYNAMIC_SUBTITLE_ENABLED=true
DYNAMIC_SUBTITLE_STYLE=default
DYNAMIC_SUBTITLE_ANIMATION=fade_in
DYNAMIC_SUBTITLE_FONT_SIZE=24
DYNAMIC_SUBTITLE_FONT_COLOR=#FFFFFF

# 存储配置（选择一种）
STORAGE_TYPE=local
LOCAL_STORAGE_DIR=./uploads
LOCAL_STORAGE_BASE_URL=http://localhost:8000/uploads

# 或使用MinIO
# STORAGE_TYPE=minio
# MINIO_ENDPOINT=localhost:9000
# MINIO_ACCESS_KEY=your_access_key
# MINIO_SECRET_KEY=your_secret_key
# MINIO_BUCKET=textloom

# 或使用华为OBS
# STORAGE_TYPE=obs
# OBS_ENDPOINT=your-region.obs.myhuaweicloud.com
# OBS_ACCESS_KEY=your_access_key
# OBS_SECRET_KEY=your_secret_key
# OBS_BUCKET=textloom
```

## 使用方式

### 1. 自动处理（推荐）

当视频生成完成后，如果启用了动态字幕功能，系统会自动：
1. 检测到视频生成完成
2. 触发动态字幕处理任务
3. 下载原视频和字幕文件
4. 使用pycaps生成带动态字幕的视频
5. 上传处理后的视频
6. 更新任务状态和视频URL

### 2. API接口使用

#### 获取支持的样式和动画

```bash
# 获取可用模板
curl -X GET "http://localhost:8000/dynamic-subtitles/templates"

# 获取支持的动画效果
curl -X GET "http://localhost:8000/dynamic-subtitles/animations"

# 获取预设配置
curl -X GET "http://localhost:8000/dynamic-subtitles/presets"
```

#### 手动处理视频字幕

```bash
curl -X POST "http://localhost:8000/dynamic-subtitles/process" \
  -H "Content-Type: application/json" \
  -H "x-test-token: your_test_token" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "subtitles_url": "https://example.com/subtitles.srt",
    "style_config": {
      "font_size": 28,
      "font_color": "#FFFFFF",
      "animation": "fade_in",
      "style": "modern"
    }
  }'
```

#### 检查pycaps状态

```bash
curl -X GET "http://localhost:8000/dynamic-subtitles/test/pycaps-status" \
  -H "x-test-token: your_test_token"
```

## 样式模板

### 1. 默认样式 (default)
- 简洁的白色字幕
- 黑色半透明背景
- 适合大多数场景

### 2. 现代风格 (modern)
- 无背景纯文本
- 渐变色高亮效果
- 平滑的动画过渡

### 3. 社交媒体风格 (social)
- 大字体粗体显示
- 多层文字阴影效果
- 夸张的动画和颜色

### 4. 高亮样式 (highlight)
- 重点词语金色高亮
- 适中的字体大小
- 柔和的动画效果

## 动画效果

- `fade_in`: 淡入效果
- `slide_up`: 上滑效果
- `pop`: 弹出效果
- `typewriter`: 打字机效果
- `neon`: 霓虹灯效果（仅社交媒体风格）

## 架构说明

### 处理流程

1. **视频生成完成检测**
   - video_merge_polling.py监控视频合成状态
   - 检测到完成后更新状态为`processing_subtitles`

2. **动态字幕任务触发**
   - 异步触发`process_dynamic_subtitles_task`
   - 传递视频URL、字幕URL等参数

3. **字幕处理执行**
   - DynamicSubtitleService下载视频和字幕文件
   - 使用pycaps生成动态字幕视频
   - 上传处理后的视频到存储服务

4. **状态更新完成**
   - 更新子任务状态为`completed`
   - 更新video_url为新的视频地址

### 关键组件

- `DynamicSubtitleService`: 核心处理服务
- `DynamicSubtitleTemplateManager`: 模板管理器
- `process_dynamic_subtitles_task`: Celery异步任务
- `storage_utils`: 存储工具类

## 故障排查

### 1. pycaps安装问题

```bash
# 检查Python版本（需要3.10-3.12）
python --version

# 重新安装pycaps
pip uninstall pycaps -y
pip install git+https://github.com/francozanardi/pycaps.git

# 检查依赖
pip install playwright Pillow numpy opencv-python pydub
```

### 2. FFmpeg问题

```bash
# 检查FFmpeg
ffmpeg -version

# Ubuntu/Debian安装
sudo apt update
sudo apt install ffmpeg

# macOS安装
brew install ffmpeg

# Windows安装
# 下载FFmpeg并添加到PATH
```

### 3. Playwright问题

```bash
# 重新安装浏览器
playwright install chromium

# 或安装所有浏览器
playwright install
```

### 4. 存储问题

- 检查存储配置是否正确
- 确认存储服务可访问
- 查看日志中的详细错误信息

### 5. 性能优化

- 调整`CELERY_WORKER_CONCURRENCY`控制并发数
- 配置合适的临时目录和存储
- 监控磁盘空间使用

## 日志位置

- 主日志: `logs/app.log`
- 字幕服务日志: 搜索`dynamic_subtitle`相关条目
- Celery任务日志: 搜索`process_dynamic_subtitles`相关条目

## API文档

启动服务后访问 http://localhost:8000/docs 查看完整的API文档，包括动态字幕相关的所有接口。