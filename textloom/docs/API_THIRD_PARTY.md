# TextLoom 第三方集成 API 文档

## 概述

TextLoom 是一个智能文本转视频生成系统，提供 RESTful API 接口，支持将 Markdown 文档和媒体资源转换为专业视频内容。

### 基础信息

- **Base URL**: `http://your-domain:48095`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 核心功能

- 智能文本转视频生成
- 多素材类型支持（Markdown、图片、视频）
- 多视频风格生成（支持并行处理）
- 子任务独立管理和状态跟踪
- 实时进度跟踪
- 文件上传与存储管理

## 处理流程

TextLoom 采用五阶段处理流程，每个阶段都有明确的输入、处理逻辑和输出结果，便于第三方服务精准展示处理进度：

### 阶段1: 素材处理 (0-25%)
**目标**: 收集和预处理所有输入媒体资源
**处理内容**:
- 下载所有 `media_urls` 中的文件
- 验证文件格式和完整性
- 提取媒体元数据（尺寸、时长、格式等）
- 生成本地存储路径和云存储URL

**阶段成果**:
- 所有媒体文件本地化存储
- 媒体项目记录（可通过任务详情接口查询）
- 文件统计：markdown_count、image_count、video_count

**状态指示器**:
- `current_stage`: "material_processing"
- `stage_message`: "正在下载第X个文件..."
- `progress`: 0-25%

### 阶段2: 素材分析 (25-50%)
**目标**: 深度分析素材内容，生成结构化描述
**处理内容**:
- Markdown文档内容提取和结构化
- 图片视觉内容AI识别和描述
- 视频关键帧提取和内容理解
- 生成素材间的关联关系

**阶段成果**:
- 素材分析报告（material_analyses字段）
- 每个素材的详细描述和标签
- 内容主题和风格识别结果

**状态指示器**:
- `current_stage`: "material_analysis"  
- `stage_message`: "正在分析第X个素材..."
- `progress`: 25-50%

### 阶段3: 子任务拆分 (50-55%)
**目标**: 根据multi_video_count创建并行处理的子任务
**处理内容**:
- 根据设定数量创建子视频任务
- 为每个子任务分配脚本风格
- 初始化子任务数据库记录
- 准备并行处理环境

**阶段成果**:
- 创建N个子任务记录（sub_video_tasks字段）
- 每个子任务有独立的ID和初始状态
- 脚本风格分配（default、product_geek等）

**状态指示器**:
- `current_stage`: "subtask_creation"
- `stage_message`: "创建第X个子任务..."
- `progress`: 50-55%

### 阶段4: 脚本生成 (55-75%)
**目标**: 并行为每个子任务生成个性化脚本
**处理内容**:
- 基于素材分析结果生成脚本大纲
- 应用不同的脚本风格和人设特征
- 生成详细的分镜头脚本
- 并行处理多个子任务脚本

**阶段成果**:
- 每个子任务包含完整脚本内容（script_data字段）
- 脚本ID关联（script_id字段）
- 分镜头描述和时长规划

**状态指示器**:
- `current_stage`: "script_generation"
- `stage_message`: "并行生成脚本: 完成X/Y个"
- `progress`: 55-75%

**子任务状态变化**:
- `pending` → `script_generating` → `script_ready` (成功)
- `pending` → `script_generating` → `script_failed` (失败)

### 阶段5: 视频合成 (75-100%)
**目标**: 并行生成最终视频，包含字幕处理
**处理内容**:
- 基于脚本进行视频合成
- 添加背景音乐和音效
- 生成动态字幕（如果启用）
- 输出最终视频文件

**阶段成果**:
- 完整的视频文件（video_url字段）
- 视频缩略图（thumbnail_url字段）
- 视频时长和元数据（duration字段）
- 云存储访问链接

**状态指示器**:
- `current_stage`: "video_generation"
- `stage_message`: "并行生成视频: 完成X/Y个"
- `progress`: 75-100%

**子任务状态变化**:
- `script_ready` → `video_generating` → `processing_subtitles` → `completed` (成功)
- `script_ready` → `video_generating` → `failed` (失败)

### 并行处理特性
- **脚本生成阶段**: 最多3个子任务并行处理
- **视频合成阶段**: 最多3个子任务并行处理  
- **状态同步**: 子任务状态变化自动更新主任务进度
- **容错机制**: 部分子任务失败不影响其他子任务继续处理
- **独立处理**: 每个子任务有独立的脚本、状态和结果

---

## 认证机制

### API Key 认证

所有业务接口均需要 API Key 认证，请联系管理员获取。

**请求头格式**:
```
X-API-Key: your-api-key
Content-Type: application/json
```

---

## 核心接口

### 1. 创建视频任务

**POST** `/tasks/create-video-task`

创建文本转视频任务，支持多素材URL输入和多视频生成。

**请求头**:
```
X-API-Key: your-api-key
Content-Type: multipart/form-data
```

**请求参数** (form-data):
```
media_urls: List[str] - 素材URL列表（必填，最多50个）
title: str - 任务标题（必填）
description: str - 任务描述（可选）
mode: str - 视频合成模式（可选，"single_scene"/"multi_scene"，默认"multi_scene"）
script_style: str - 脚本风格（可选，"default"/"product_geek"，默认"default"）
persona_id: int - 人设ID（可选）
multi_video_count: int - 生成视频数量（可选，1-5，默认3）
media_meta: str - 素材元数据JSON（可选）
```

**支持的媒体类型**:
- **Markdown**: `.md`, `.markdown`, `.txt`
- **图片**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`
- **视频**: `.mp4`, `.mov`, `.mkv`, `.avi`, `.wmv`, `.flv`, `.webm`

**media_meta 格式示例**:
```json
{
  "https://example.com/image1.jpg": "产品展示图片，显示了新款手机的外观设计",
  "https://example.com/video1.mp4": "产品演示视频，展示了核心功能"
}
```

**响应示例**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "AI产品介绍视频",
  "description": "基于最新AI技术的产品演示",
  "task_type": "text_to_video",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "started_at": null,
  "completed_at": null,
  "workspace_dir": "/workspace/task_xxx",
  "video_url": null,
  "thumbnail_url": null,
  "video_duration": 0,
  "error_message": null,
  "is_multi_video_task": true,
  "multi_video_summary": {
    "total_videos": 3,
    "completed_count": 0,
    "failed_count": 0,
    "processing_count": 0,
    "pending_count": 3
  },
  "current_stage": "material_processing"
}
```

**返回值字段说明**:
- `task_id`: 任务唯一标识符（UUID格式）
- `title`: 任务标题
- `description`: 任务描述
- `task_type`: 任务类型，枚举值："text_to_video" | "video_generation" | "dynamic_subtitle"
- `status`: 任务状态，枚举值："pending" | "processing" | "completed" | "failed" | "cancelled" | "partial_success"
- `progress`: 任务进度，整数类型，范围0-100
- `current_stage`: 当前处理阶段，枚举值："material_processing" | "material_analysis" | "subtask_creation" | "script_generation" | "video_generation" | "completed"
- `created_at`: 任务创建时间（ISO 8601格式）
- `updated_at`: 任务最后更新时间（ISO 8601格式）
- `started_at`: 任务开始处理时间（未开始为null）
- `completed_at`: 任务完成时间（未完成为null）
- `workspace_dir`: 工作目录路径
- `video_url`: 主视频文件URL（未生成时为null）
- `thumbnail_url`: 视频缩略图URL（未生成时为null）
- `video_duration`: 视频时长（毫秒，未生成时为0）
- `error_message`: 错误信息（无错误时为null）
- `is_multi_video_task`: 是否为多视频任务（布尔值）
- `multi_video_summary`: 多视频任务统计信息（对象）
  - `total_videos`: 总视频数量
  - `completed_count`: 已完成数量
  - `failed_count`: 失败数量
  - `processing_count`: 处理中数量
  - `pending_count`: 待处理数量
```

### 2. 统一任务查询接口

**GET** `/tasks/{task_id}`

统一的任务信息查询接口，支持按需返回不同阶段的数据，既可以获取基础状态信息，也可以查询详细的阶段成果数据。

**请求头**:
```
X-API-Key: your-api-key
```

**路径参数**:
- `task_id`: UUID格式的任务ID

**查询参数**:
- `include_stages`: 可选，指定要包含的阶段数据，用逗号分隔。可选值：
  - `subtasks` - 子任务列表信息
  - `media` - 素材文件信息
  - `analysis` - 素材分析结果
  - `scripts` - 脚本内容信息
  - `videos` - 视频结果信息
- `detail_level`: 可选，详情级别。可选值：
  - `basic` - 基础信息（默认）
  - `full` - 完整信息

**响应说明**:
- 接口始终返回核心任务状态信息（status、progress、current_stage等）
- 根据 `include_stages` 参数按需返回阶段数据

### 🎯 阶段化调用逻辑建议

TextLoom按照5个阶段顺序执行任务，第三方服务可以根据 `current_stage` 智能地决定需要同步哪些阶段数据到自己的系统中：

#### 阶段1: 素材处理阶段 (0-25%)
- **current_stage**: `"material_processing"`
- **stage_message**: `"正在下载第X个文件..."` / `"正在处理第X个素材..."`
- **建议调用**: 仅基础查询即可，素材数据尚未完成
```bash
GET /tasks/{task_id}
```

#### 阶段2: 素材分析阶段 (25-50%)
- **current_stage**: `"material_analysis"`  
- **stage_message**: `"正在分析第X个素材..."` / `"AI正在理解素材内容..."`
- **建议调用**: 可开始获取素材文件信息
```bash
GET /tasks/{task_id}?include_stages=media
```
- **同步建议**: 将 `media` 数据同步到本地素材表，为后续展示做准备

#### 阶段3: 子任务创建阶段 (50-55%)
- **current_stage**: `"subtask_creation"`
- **stage_message**: `"创建第X个子任务..."` / `"准备并行处理环境..."`
- **建议调用**: 获取子任务列表和素材分析结果
```bash
GET /tasks/{task_id}?include_stages=subtasks,media,analysis
```
- **同步建议**: 
  - 将 `analysis` 数据同步到素材分析表
  - 将 `subtasks` 数据同步到子任务表，准备展示子任务进度

#### 阶段4: 脚本生成阶段 (55-75%)
- **current_stage**: `"script_generation"`
- **stage_message**: `"并行生成脚本: 完成X/Y个"` / `"正在生成第X个视频脚本..."`
- **建议调用**: 重点获取子任务和脚本进度
```bash
GET /tasks/{task_id}?include_stages=subtasks,scripts
```
- **同步建议**: 
  - 定期更新 `subtasks` 状态（pending → script_generating → script_generated）
  - 将完成的 `scripts` 数据同步到脚本表
  - 可以开始展示脚本预览（标题、预计时长等）

#### 阶段5: 视频生成阶段 (75-100%)
- **current_stage**: `"video_generation"`
- **stage_message**: `"并行生成视频: 完成X/Y个"` / `"正在合成第X个视频..."`
- **建议调用**: 获取所有相关信息
```bash
GET /tasks/{task_id}?include_stages=subtasks,videos
```
- **同步建议**:
  - 持续更新 `subtasks` 状态（script_generated → video_generating → completed）
  - 将完成的 `videos` 数据同步到视频结果表
  - 更新视频URL、缩略图、时长等信息

#### 任务完成后的完整同步
- **current_stage**: 保持 `"video_generation"`，但 **status**: `"completed"`
- **建议调用**: 执行一次完整数据同步
```bash
GET /tasks/{task_id}?include_stages=subtasks,media,analysis,scripts,videos&detail_level=full
```
- **同步建议**: 确保所有阶段数据都已同步到本地系统

### ⚡ 性能优化建议

1. **阶段化同步**: 不要在早期阶段查询尚未准备好的数据（如在素材处理阶段查询脚本信息）
2. **增量更新**: 根据 `updated_at` 字段判断数据是否需要重新同步
3. **错误处理**: 网络错误时使用指数退避策略，避免频繁重试
4. **资源清理**: 任务完成后及时停止轮询，避免不必要的API调用

**基础查询示例**:

**请求**: `GET /tasks/{task_id}`

**响应**（基础状态信息）:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "AI产品介绍视频",
  "description": "基于最新AI技术的产品演示",
  "task_type": "text_to_video",
  "status": "completed",
  "progress": 100,
  "current_stage": "completed",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:45:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "completed_at": "2024-01-15T10:45:00Z",
  "workspace_dir": "/workspace/task_xxx",
  "video_url": "https://storage.example.com/video1.mp4",
  "thumbnail_url": "https://storage.example.com/thumb1.jpg",
  "video_duration": 105710,
  "error_message": null,
  "is_multi_video_task": true,
  "multi_video_summary": {
    "total_videos": 3,
    "completed_count": 3,
    "failed_count": 0,
    "processing_count": 0,
    "pending_count": 0
  }
}
```

**基础状态字段说明**:
- `task_id`: 任务唯一标识符（UUID格式）
- `title`: 任务标题
- `description`: 任务描述
- `task_type`: 任务类型，枚举值："text_to_video" | "video_generation" | "dynamic_subtitle"
- `status`: 任务状态，枚举值："pending" | "processing" | "completed" | "failed" | "cancelled" | "partial_success"
- `progress`: 任务进度，整数类型，范围0-100
- `current_stage`: 当前处理阶段，枚举值："material_processing" | "material_analysis" | "subtask_creation" | "script_generation" | "video_generation" | "completed"
- `created_at`: 任务创建时间（ISO 8601格式）
- `updated_at`: 任务最后更新时间（ISO 8601格式）
- `started_at`: 任务开始处理时间（未开始为null）
- `completed_at`: 任务完成时间（未完成为null）
- `workspace_dir`: 工作目录路径
- `video_url`: 主视频文件URL（未生成时为null）
- `thumbnail_url`: 视频缩略图URL（未生成时为null）
- `video_duration`: 视频时长（毫秒，未生成时为0）
- `error_message`: 错误信息（无错误时为null）
- `is_multi_video_task`: 是否为多视频任务（布尔值）
- `multi_video_summary`: 多视频任务统计信息（对象）
  - `total_videos`: 总视频数量
  - `completed_count`: 已完成数量
  - `failed_count`: 失败数量
  - `processing_count`: 处理中数量
  - `pending_count`: 待处理数量
```

**阶段数据查询示例**:

**请求**: `GET /tasks/{task_id}?include_stages=subtasks,scripts`

**响应**（包含子任务和脚本信息）:
```json
{
  // ... 基础信息（同上）
  "stages": {
    "subtasks": {
      "count": 3,
      "items": [
        {
          "sub_task_id": "6309c24f-4b95-4e43-83f7-214ba59d38a0_video_1",
          "video_index": 1,
          "script_style": "default",
          "status": "completed",
          "progress": 100,
          "created_at": "2025-09-03T08:42:42.596352"
        },
        {
          "sub_task_id": "6309c24f-4b95-4e43-83f7-214ba59d38a0_video_2", 
          "video_index": 2,
          "script_style": "product_geek",
          "status": "completed",
          "progress": 100,
          "created_at": "2025-09-03T08:42:42.605049"
        }
      ]
    },
    "scripts": {
      "count": 3,
      "items": [
        {
          "sub_task_id": "6309c24f-4b95-4e43-83f7-214ba59d38a0_video_1",
          "script_style": "default",
          "script_id": "bfab8f72-e7a7-42d7-bde0-07db72de8b2b",
          "status": "completed",
          "progress": 100,
          "script_summary": {
            "titles": ["default风格标题1", "default风格标题2", "default风格标题3"],
            "word_count": 19,
            "scene_count": 1,
            "estimated_duration": 15.0
          }
        }
      ]
    }
  },

**子任务字段说明**:
- `sub_task_id`: 子任务业务标识符
- `video_index`: 视频索引（整数）
- `script_style`: 脚本风格，枚举值："default" | "product_geek" | "viral" | "professional"
- `status`: 子任务状态，枚举值："pending" | "script_generating" | "script_generated" | "script_failed" | "video_generating" | "processing_subtitles" | "completed" | "failed"
- `progress`: 子任务进度，范围0-100
- `created_at`: 子任务创建时间（ISO 8601格式）

**脚本字段说明**:
- `sub_task_id`: 关联的子任务ID
- `script_style`: 脚本风格
- `script_id`: 脚本唯一ID（UUID格式）
- `status`: 脚本状态，枚举值："completed" | "failed"
- `progress`: 脚本生成进度，范围0-100
- `script_summary`: 脚本摘要信息（对象）
  - `titles`: 视频标题列表（字符串数组）
  - `word_count`: 文字总数（整数）
  - `scene_count`: 场景数量（整数）
  - `estimated_duration`: 预计视频时长（秒，浮点数）

}
```

**完整查询示例**:

**请求**: `GET /tasks/{task_id}?include_stages=subtasks,media,analysis,scripts,videos&detail_level=full`

**响应**（包含所有阶段数据）:
```json
{
  // ... 基础信息（同上）
  "stages": {
    "subtasks": {
      "count": 3,
      "items": [...]  // 子任务列表
    },
    "media": {
      "count": 20,
      "items": [
        {
          "id": "61a76d90-ebbb-44d0-b0a2-04ba3fd52d2d",
          "filename": "90d06612450c4a959a12870dacf86c05.jpg",
          "media_type": "image",
          "original_url": "https://mmbiz.qpic.cn/mmbiz_jpg/example.jpg",
          "file_size": 32509,
          "mime_type": "image/jpeg",
          "resolution": null,
          "created_at": "2025-09-03T08:40:25.766881"
        }
      ]
    },
    "analysis": {
      "count": 0,
      "items": []
    },
    "scripts": {
      "count": 3,
      "items": [...]  // 脚本列表
    },
    "videos": {
      "count": 3,
      "completed": [
        {
          "sub_task_id": "6309c24f-4b95-4e43-83f7-214ba59d38a0_video_1",
          "script_style": "default",
          "status": "completed",
          "progress": 100,
          "video_url": "https://res.bifrostv.com/easegen-core/pycaps_subtitle_xxx.mp4",
          "thumbnail_url": "https://res.bifrostv.com/easegen-core/thumbnail/xxx.png",
          "duration": 105710,
          "course_media_id": 1756889091533796000,
          "completed_at": "2025-09-03T08:58:18.083781"
        }
      ],
      "processing": [],
      "failed": []
    }
  },

**媒体项字段说明**:
- `id`: 媒体项数据库主键ID（UUID格式）
- `filename`: 文件名
- `media_type`: 媒体类型，枚举值："markdown" | "image" | "video"
- `original_url`: 原始媒体文件URL
- `file_size`: 文件大小（字节）
- `mime_type`: MIME类型（如image/jpeg, video/mp4）
- `resolution`: 分辨率（如1920x1080，图片/视频可能为null）
- `created_at`: 创建时间（ISO 8601格式）

**视频结果字段说明**:
- `sub_task_id`: 子任务业务标识符
- `script_style`: 脚本风格，枚举值："default" | "product_geek" | "viral" | "professional"
- `status`: 视频状态，枚举值："completed" | "failed"
- `progress`: 视频生成进度，范围0-100
- `video_url`: 生成的视频文件URL
- `thumbnail_url`: 视频缩略图URL
- `duration`: 视频时长（毫秒）
- `course_media_id`: 课程媒体ID（整数）
- `completed_at`: 视频完成时间（ISO 8601格式）

}
```

**素材分析字段说明**:
当前测试任务中 `analysis` 为空数组，表示未启用素材分析功能或分析数据存储在其他位置。
```

**任务状态说明**:
- `pending`: 等待处理
- `processing`: 正在处理
- `completed`: 处理完成
- `failed`: 处理失败

**子任务状态流转**:
- `pending`: 子任务已创建，等待处理
- `script_generating`: 正在生成脚本
- `script_generated`: 脚本生成完成，等待视频生成
- `script_failed`: 脚本生成失败
- `video_generating`: 正在生成视频
- `processing_subtitles`: 视频生成完成，正在处理动态字幕
- `completed`: 所有处理完成（包括字幕）
- `failed`: 处理失败

### 🎯 使用建议

#### 轻量查询（仅状态信息）
```bash
curl -X GET "http://your-domain:48095/tasks/{task_id}" \
  -H "X-API-Key: your-api-key"
```
适用于：进度轮询、状态检查

#### 阶段化查询（按需获取数据）
```bash
# 获取子任务进度
curl -X GET "http://your-domain:48095/tasks/{task_id}?include_stages=subtasks" \
  -H "X-API-Key: your-api-key"

# 获取素材分析结果
curl -X GET "http://your-domain:48095/tasks/{task_id}?include_stages=media,analysis" \
  -H "X-API-Key: your-api-key"

# 获取脚本和视频结果
curl -X GET "http://your-domain:48095/tasks/{task_id}?include_stages=scripts,videos&detail_level=full" \
  -H "X-API-Key: your-api-key"
```
适用于：分阶段展示处理结果、详细信息查看

#### 完整查询（所有数据）
```bash
curl -X GET "http://your-domain:48095/tasks/{task_id}?include_stages=subtasks,media,analysis,scripts,videos&detail_level=full" \
  -H "X-API-Key: your-api-key"
```
适用于：任务完成后的详情页面、数据导出

#### 最佳实践
- **进度监控**: 使用基础查询，5-10秒轮询间隔
- **阶段展示**: 根据进度阶段按需查询对应数据
- **详情页面**: 任务完成后使用完整查询获取所有信息
- **性能考虑**: 避免频繁的完整查询，优先使用轻量查询

### 3. 重要更新说明

⚠️ **API响应格式已更新** (2025年9月更新)

基于实际接口测试，关键更改如下：

1. **主键字段更新**: `id` → `task_id`
2. **任务类型格式**: 大写改为小写下划线格式（`TEXT_TO_VIDEO` → `text_to_video`）  
3. **多视频结构**: `sub_videos_completed` 改为结构化的 `multi_video_summary` 对象
4. **阶段数据嵌套**: `include_stages` 返回数据现在嵌套在 `stages` 对象下，格式为 `{count, items}`
5. **视频时长单位**: `duration` 改为 `video_duration`，单位为毫秒
6. **新增字段**: `thumbnail_url`、`current_stage`、`is_multi_video_task`、`multi_video_summary`

**迁移建议**:
- 更新客户端代码以使用新的字段名称
- 调整阶段数据解析逻辑以处理嵌套结构
- 检查多视频任务状态时使用 `multi_video_summary` 对象
```

### 4. 文件上传

**POST** `/tasks/attachments/upload`

批量上传文件到云存储，返回可用于视频任务的URL列表。

**请求头**:
```
X-API-Key: your-api-key
Content-Type: multipart/form-data
```

**请求格式**: multipart/form-data

**请求参数**:
```
files: List[File] - 文件列表（最多50个）
```

**文件限制**:
- 单文件最大: 50MB
- 支持格式: Markdown、图片、视频文件
- 总文件数: 最多50个

**响应示例**:
```json
{
  "items": [
    {
      "filename": "document.md",
      "url": "https://storage.example.com/uploads/2024/01/15/uuid_document.md",
      "object_key": "uploads/2024/01/15/uuid_document.md",
      "media_type": "markdown",
      "size": 2048,
      "success": true
    },
    {
      "filename": "image.jpg",
      "url": "https://storage.example.com/uploads/2024/01/15/uuid_image.jpg",
      "object_key": "uploads/2024/01/15/uuid_image.jpg",
      "media_type": "image",
      "size": 102400,
      "success": true
    },
    {
      "filename": "failed_file.xyz",
      "success": false,
      "error": "不支持的文件类型"
    }
  ],
  "stats": {
    "markdown_count": 1,
    "image_count": 1,
    "video_count": 0,
    "total_size": 104448
  },
  "warnings": [
    "不支持的文件类型: failed_file.xyz"
  ]
}
```

**文件上传返回值字典说明**:
- `items`: 文件上传结果列表（对象数组）
  - `filename`: 原始文件名
  - `url`: 云存储访问URL（成功时）
  - `object_key`: 云存储对象键（成功时）
  - `media_type`: 媒体类型，枚举值："markdown" | "image" | "video"
  - `size`: 文件大小（字节，成功时）
  - `success`: 上传是否成功（布尔值）
  - `error`: 错误信息（失败时）
- `stats`: 上传统计信息（对象）
  - `markdown_count`: 成功上传的Markdown文件数量
  - `image_count`: 成功上传的图片文件数量
  - `video_count`: 成功上传的视频文件数量
  - `total_size`: 总文件大小（字节）
- `warnings`: 警告信息列表（字符串数组）
```

### 5. 任务重试

**POST** `/tasks/{task_id}/retry`

重试失败的任务。

**请求头**:
```
X-API-Key: your-api-key
```

**路径参数**:
- `task_id`: UUID格式的任务ID

**响应示例**:
```json
{
  "message": "任务已重新加入处理队列",
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**任务重试返回值字段说明**:
- `message`: 操作结果消息（字符串）
- `task_id`: 重试的任务ID（UUID格式）
```


---

## 错误响应格式

所有接口在发生错误时返回统一格式：

```json
{
  "detail": "错误描述信息",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误代码

#### 认证相关
- `AUTH_API_KEY_MISSING` - 缺少API Key
- `AUTH_API_KEY_INVALID` - API Key无效或已过期
- `AUTH_API_KEY_DISABLED` - API Key已被禁用
- `AUTH_QUOTA_EXCEEDED` - 配额已用完

#### 任务相关
- `TASK_NOT_FOUND` - 任务不存在
- `TASK_CREATION_FAILED` - 任务创建失败
- `TASK_PROCESSING_ERROR` - 任务处理异常

#### 文件相关
- `FILE_TOO_LARGE` - 文件超过大小限制
- `FILE_TYPE_NOT_SUPPORTED` - 不支持的文件类型
- `FILE_UPLOAD_FAILED` - 文件上传失败

#### 素材相关
- `MEDIA_URL_INVALID` - 素材URL无效
- `MEDIA_DOWNLOAD_TIMEOUT` - 素材下载超时
- `MEDIA_ANALYSIS_FAILED` - 素材分析失败

---

## 使用流程

### 基本使用流程

1. **上传文件**（可选）
   ```bash
   curl -X POST "http://your-domain:48095/tasks/attachments/upload" \
     -H "X-API-Key: your-api-key" \
     -F "files=@document.md" \
     -F "files=@image.jpg"
   ```

2. **创建视频任务**
   ```bash
   curl -X POST "http://your-domain:48095/tasks/create-video-task" \
     -H "X-API-Key: your-api-key" \
     -F "media_urls=https://example.com/doc.md" \
     -F "media_urls=https://example.com/image.jpg" \
     -F "title=产品介绍视频" \
     -F "multi_video_count=3"
   ```

3. **查询任务状态**
   ```bash
   curl -X GET "http://your-domain:48095/tasks/{task_id}" \
     -H "X-API-Key: your-api-key"


### 最佳实践总结

#### 🎯 UI/UX 设计建议
- **阶段化展示**: 根据progress范围显示不同界面
- **实时反馈**: 5-10秒轮询间隔，及时更新状态
- **预期管理**: 显示预计完成时间和当前阶段
- **错误处理**: 优雅处理网络错误和任务失败

#### ⚡ 性能优化
- **条件轮询**: 任务完成后停止查询
- **错误重试**: 实现指数退避重试机制
- **缓存策略**: 缓存任务详情减少API调用
- **批量查询**: 多任务时考虑批量查询接口

#### 🔒 安全考虑
- **API Key管理**: 安全存储，避免前端暴露
- **HTTPS**: 生产环境必须使用HTTPS
- **错误信息**: 避免向用户暴露敏感错误信息

---

## 联系支持

如需技术支持或申请API Key，请联系系统管理员。
