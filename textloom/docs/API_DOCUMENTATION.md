# TextLoom API 接口文档

## 目录
- [API概述](#api概述)
- [架构说明](#架构说明)
- [认证机制](#认证机制)
- [核心视频生成接口](#核心视频生成接口)
- [任务管理接口](#任务管理接口)
- [人设管理接口](#人设管理接口)
- [动态字幕接口](#动态字幕接口)
- [文件上传接口](#文件上传接口)
- [监控和健康检查接口](#监控和健康检查接口)
- [错误代码说明](#错误代码说明)
- [示例代码和最佳实践](#示例代码和最佳实践)

---

## API概述

TextLoom 是一个基于 FastAPI 和 Celery 构建的智能文本转视频生成系统，提供强大的 RESTful API 接口，支持将 Markdown 文档和媒体资源转换为专业视频内容。

### 基础信息

- **Base URL**: `http://localhost:48095` (默认开发环境)
- **API Version**: v1.0
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **字符编码**: UTF-8

### 核心功能

- 智能文本转视频生成
- 多素材类型支持（Markdown、图片、视频）
- 分布式异步任务处理
- 多视频风格生成
- 人设化内容定制
- 专业动态字幕生成（基于PyCaps引擎）
- 实时进度跟踪
- 文件上传与存储管理

---

## 架构说明

### 系统架构

TextLoom 采用分布式微服务架构，核心组件包括：

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │     Celery      │    │     Redis       │
│   Web API       │◄──►│   Task Queue    │◄──►│  Message Broker │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   File Storage  │    │   Monitoring    │
│   Database      │    │    (MinIO/OBS)  │    │ (Prometheus)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 处理流程

视频生成采用四阶段处理流程：

1. **素材处理** (0-25%): 提取和下载媒体资源
2. **素材分析** (25-50%): AI 驱动的内容分析
3. **脚本生成** (50-75%): 基于人设生成视频脚本
4. **视频合成** (75-100%): 生成最终视频输出

### 技术特性

- **异步处理**: 基于 Celery 的分布式任务队列
- **多实例支持**: 横向扩展的 Worker 节点
- **实时监控**: Prometheus + Grafana 监控体系
- **容错机制**: 自动重试和错误恢复
- **进度追踪**: 实时任务状态和进度更新

---

## 认证机制

TextLoom 采用双重认证机制：API Key 为主要认证方式，JWT Token 用于管理员功能。

### 认证方式

1. **API Key认证（推荐）**
   - 第三方系统集成的主要认证方式
   - 支持配额管理和使用统计
   - 在HTTP头中传递：`X-API-Key: your-api-key`
   - 无需注册，由管理员后台分配

2. **JWT Token认证**
   - 仅用于管理员功能和后台管理
   - 支持访问令牌和刷新令牌机制
   - 用于API用户管理等管理功能

### API Key 认证

**请求头格式**:
```
X-API-Key: sk-proj-abcd1234567890abcdef1234567890abcdef12345678
Content-Type: application/json
```

**认证流程**:
1. 联系管理员申请API Key
2. 管理员在后台创建API用户并生成API Key
3. 在请求头中携带API Key进行接口调用
4. 系统自动验证API Key并记录使用情况

**权限级别**:
- **API用户**: 核心业务功能（视频生成、文件上传等）
- **管理员**: 系统管理和API用户管理
- **匿名用户**: 部分只读接口（健康检查、任务状态查询等）

### API用户管理

#### 创建API用户

**POST** `/auth/api-users`

创建新的API用户（需要管理员JWT Token认证）。

**请求头**:
```
Authorization: Bearer {admin_jwt_token}
Content-Type: application/json
```

**请求参数**:
```json
{
  "username": "string (3-50字符，唯一标识)",
  "display_name": "string (显示名称，可选)",
  "description": "string (用户描述，可选)",
  "quota_limit": "integer (配额限制，可选，默认无限制)",
  "is_active": "boolean (是否激活，可选，默认true)"
}
```

**响应示例**:
```json
{
  "id": "uuid",
  "username": "partner_company_001",
  "display_name": "合作伙伴公司A",
  "description": "第三方集成合作伙伴",
  "api_key": "sk-proj-abcd1234567890abcdef1234567890abcdef12345678",
  "quota_limit": 1000,
  "quota_used": 0,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_used_at": null
}
```

#### 获取API用户列表

**GET** `/auth/api-users`

获取所有API用户的列表（需要管理员JWT Token认证）。

**查询参数**:
- `is_active`: 筛选激活状态（可选）
- `limit`: 返回数量限制（默认50）
- `offset`: 分页偏移量（默认0）

**响应示例**:
```json
{
  "items": [
    {
      "id": "uuid",
      "username": "partner_company_001",
      "display_name": "合作伙伴公司A",
      "description": "第三方集成合作伙伴",
      "quota_limit": 1000,
      "quota_used": 150,
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_used_at": "2024-01-20T14:22:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### 获取API用户详情

**GET** `/auth/api-users/{user_id}`

获取指定API用户的详细信息和使用统计。

**响应示例**:
```json
{
  "id": "uuid",
  "username": "partner_company_001",
  "display_name": "合作伙伴公司A",
  "description": "第三方集成合作伙伴",
  "quota_limit": 1000,
  "quota_used": 150,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_used_at": "2024-01-20T14:22:00Z",
  "usage_stats": {
    "total_requests": 150,
    "successful_requests": 142,
    "failed_requests": 8,
    "last_30_days": 75,
    "today": 12
  }
}
```

#### 更新API用户

**PUT** `/auth/api-users/{user_id}`

更新API用户信息。

**请求参数**:
```json
{
  "display_name": "string (可选)",
  "description": "string (可选)",
  "quota_limit": "integer (可选)",
  "is_active": "boolean (可选)"
}
```

#### 重新生成API Key

**POST** `/auth/api-users/{user_id}/regenerate-key`

重新生成用户的API Key（旧Key将立即失效）。

**响应示例**:
```json
{
  "id": "uuid",
  "username": "partner_company_001",
  "api_key": "sk-proj-new1234567890abcdef1234567890abcdef12345678",
  "regenerated_at": "2024-01-20T15:30:00Z"
}
```

#### 禁用API用户

**POST** `/auth/api-users/{user_id}/disable`

禁用API用户（API Key将立即失效）。

**响应示例**:
```json
{
  "message": "API用户已禁用",
  "user_id": "uuid",
  "disabled_at": "2024-01-20T15:35:00Z"
}
```

#### 启用API用户

**POST** `/auth/api-users/{user_id}/enable`

启用API用户。

### 管理员JWT认证（仅限管理功能）

#### 管理员登录

**POST** `/auth/admin/login`

管理员登录获取JWT Token。

**请求参数**:
```json
{
  "username": "string (管理员用户名)",
  "password": "string (管理员密码)",
  "device_info": "string (可选，设备标识)"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "username": "admin",
    "is_superuser": true
  }
}
```

#### 令牌刷新

**POST** `/auth/refresh`

使用刷新令牌获取新的访问令牌。

**请求参数**:
```json
{
  "refresh_token": "string"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

#### 管理员登出

**POST** `/auth/logout`

管理员登出，撤销指定刷新令牌。

**请求头**:
```
Authorization: Bearer {access_token}
```

**请求参数**:
```json
{
  "refresh_token": "string"
}
```

---

## 核心视频生成接口

### 创建视频任务

**POST** `/tasks/create-video-task`

创建文本转视频任务，支持多素材URL输入和多视频生成。

**认证要求**: 需要API Key认证

**请求头**:
```
X-API-Key: your-api-key
Content-Type: multipart/form-data
```

**请求参数** (form-data):
```
media_urls: List[str] - 素材URL列表（最多50个）
title: str - 任务标题
description: str - 任务描述（可选）
mode: str - 视频合成模式（"single_scene"/"multi_scene"，默认"multi_scene"）
script_style: str - 脚本风格（"default"/"product_geek"，默认"default"）
persona_id: int - 人设ID（可选）
multi_video_count: int - 生成视频数量（1-5，默认3）
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
  "id": "uuid",
  "title": "AI产品介绍视频",
  "description": "基于最新AI技术的产品演示",
  "task_type": "TEXT_TO_VIDEO",
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "started_at": null,
  "completed_at": null,
  "file_path": "/workspace/task_xxx/source_manifest.md",
  "workspace_dir": "/workspace/task_xxx",
  "creator_id": null,
  "video_url": null,
  "error_message": null,
  "celery_task_id": "celery-task-uuid",
  "is_multi_video_task": true,
  "multi_video_count": 3,
  "multi_video_urls": [],
  "script_style_type": "default",
  "source_file": "/workspace/task_xxx/source_manifest.md",
  "markdown_count": 2,
  "image_count": 5,
  "video_count": 3
}
```

### 任务状态查询

**GET** `/tasks/{task_id}/status`

获取任务的详细状态信息，包括多视频生成进度。

**认证要求**: 可选API Key认证（建议携带以获取完整信息）

**请求头** (可选):
```
X-API-Key: your-api-key
```

**路径参数**:
- `task_id`: UUID格式的任务ID

**响应示例**:
```json
{
  "task_id": "uuid",
  "status": "processing",
  "progress": 45,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "completed_at": null,
  "error_message": null,
  "media_items_count": 8,
  "workspace_dir": "/workspace/task_xxx",
  "celery_task_id": "celery-task-uuid",
  "celery_status": "PROGRESS",
  "worker_name": "worker1@hostname",
  "retry_count": 0,
  "max_retries": 3,
  "current_stage": "script_generation",
  "stage_message": "正在生成第2个视频脚本...",
  "is_multi_video_task": true,
  "multi_video_info": {
    "total_videos": 3,
    "completed_count": 1,
    "failed_count": 0,
    "processing_count": 2,
    "completed_videos": [
      {
        "sub_task_id": "uuid-1",
        "script_style": "default",
        "status": "completed",
        "progress": 100,
        "video_url": "https://storage.example.com/video1.mp4",
        "thumbnail_url": "https://storage.example.com/thumb1.jpg",
        "duration": 120.5,
        "course_media_id": "media_id_1"
      }
    ],
    "failed_videos": [],
    "processing_videos": [
      {
        "sub_task_id": "uuid-2",
        "script_style": "product_geek",
        "status": "processing",
        "progress": 60
      },
      {
        "sub_task_id": "uuid-3",
        "script_style": "default",
        "status": "pending",
        "progress": 0
      }
    ]
  },
  "video_url": "https://storage.example.com/video1.mp4",
  "thumbnail_url": "https://storage.example.com/thumb1.jpg",
  "video_duration": 120.5
}
```

### 任务重试

**POST** `/tasks/{task_id}/retry`

重试失败的任务。

**认证要求**: 需要API Key认证

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
  "task_id": "uuid"
}
```

---

## 任务管理接口

### 获取任务列表

**GET** `/tasks/`

获取所有任务的列表。

**响应示例**:
```json
[
  {
    "id": "uuid",
    "title": "任务标题",
    "description": "任务描述",
    "task_type": "TEXT_TO_VIDEO",
    "status": "completed",
    "progress": 100,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:45:00Z",
    "started_at": "2024-01-15T10:31:00Z",
    "completed_at": "2024-01-15T10:45:00Z",
    "file_path": "/workspace/task_xxx/source_manifest.md",
    "workspace_dir": "/workspace/task_xxx",
    "creator_id": null,
    "video_url": "https://storage.example.com/output.mp4",
    "error_message": null
  }
]
```

### 获取任务详情

**GET** `/tasks/{task_id}`

获取指定任务的详细信息。

**路径参数**:
- `task_id`: UUID格式的任务ID

**响应示例**:
```json
{
  "task": {
    "id": "uuid",
    "title": "任务标题",
    "description": "任务描述",
    "task_type": "TEXT_TO_VIDEO",
    "status": "completed",
    "progress": 100,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:45:00Z",
    "started_at": "2024-01-15T10:31:00Z",
    "completed_at": "2024-01-15T10:45:00Z",
    "file_path": "/workspace/task_xxx/source_manifest.md",
    "workspace_dir": "/workspace/task_xxx",
    "creator_id": null,
    "video_url": "https://storage.example.com/output.mp4",
    "error_message": null
  },
  "media_items": [
    {
      "id": "uuid",
      "task_id": "uuid",
      "original_url": "https://example.com/image.jpg",
      "media_type": "image",
      "filename": "image.jpg",
      "file_size": 102400,
      "mime_type": "image/jpeg",
      "local_path": "/workspace/materials/images/image.jpg",
      "cloud_url": "https://storage.example.com/image.jpg",
      "upload_status": "completed",
      "download_status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "downloaded_at": "2024-01-15T10:31:00Z",
      "uploaded_at": "2024-01-15T10:45:00Z",
      "error_message": null,
      "context_before": "产品介绍文本",
      "context_after": "特性说明文本",
      "position_in_content": 150,
      "surrounding_paragraph": "这是产品的核心展示图片..."
    }
  ]
}
```

### 更新任务

**PUT** `/tasks/{task_id}`

更新任务信息。

**路径参数**:
- `task_id`: UUID格式的任务ID

**请求参数**:
```json
{
  "title": "string (可选)",
  "description": "string (可选)",
  "status": "string (可选，枚举值)"
}
```

### 删除任务

**DELETE** `/tasks/{task_id}`

删除指定任务及其相关资源。

**路径参数**:
- `task_id`: UUID格式的任务ID

**响应示例**:
```json
{
  "message": "任务删除成功",
  "task_id": "uuid"
}
```

### 获取任务统计

**GET** `/tasks/stats`

获取任务统计信息。

**响应示例**:
```json
{
  "total_tasks": 150,
  "pending_tasks": 5,
  "processing_tasks": 3,
  "completed_tasks": 140,
  "failed_tasks": 2,
  "avg_processing_time": 450.5,
  "success_rate": 93.3
}
```

### 获取任务媒体项目

**GET** `/tasks/{task_id}/media-items`

获取任务关联的所有媒体项目。

**路径参数**:
- `task_id`: UUID格式的任务ID

**响应示例**: 返回 MediaItem 数组，格式同任务详情中的 media_items。

---

## 人设管理接口

### 获取人设列表

**GET** `/personas/`

获取所有可用的人设列表。

**响应示例**:
```json
[
  {
    "id": "1",
    "name": "专业讲师",
    "persona_type": "educational",
    "style": "professional",
    "target_audience": "企业培训",
    "characteristics": "严谨专业，逻辑清晰，善于解释复杂概念",
    "tone": "正式但友好",
    "keywords": ["教育", "培训", "专业", "讲解"],
    "is_preset": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "2",
    "name": "产品极客",
    "persona_type": "product",
    "style": "enthusiastic",
    "target_audience": "技术爱好者",
    "characteristics": "对技术充满热情，喜欢深入分析产品特性",
    "tone": "轻松活泼",
    "keywords": ["科技", "产品", "创新", "评测"],
    "is_preset": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### 获取预设人设

**GET** `/personas/preset`

获取系统预设的人设列表。

**响应格式**: 同人设列表接口

### 创建自定义人设

**POST** `/personas/`

创建自定义人设配置。

**请求参数**:
```json
{
  "name": "string (人设名称)",
  "persona_type": "string (人设类型)",
  "style": "string (风格描述)",
  "target_audience": "string (目标受众)",
  "characteristics": "string (人设特征)",
  "tone": "string (语调描述)",
  "keywords": ["string"] // 关键词数组
}
```

**响应示例**:
```json
{
  "id": "custom_001",
  "name": "营销专家",
  "persona_type": "marketing",
  "style": "persuasive",
  "target_audience": "潜在客户",
  "characteristics": "善于发现产品价值，能够用通俗易懂的方式传达复杂信息",
  "tone": "友好且具有说服力",
  "keywords": ["营销", "销售", "价值", "客户"],
  "is_preset": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 更新人设

**PUT** `/personas/{persona_id}`

更新自定义人设配置（预设人设不可修改）。

**路径参数**:
- `persona_id`: 人设ID

**请求参数**: 同创建人设，所有字段可选

### 删除人设

**DELETE** `/personas/{persona_id}`

删除自定义人设（预设人设不可删除）。

**路径参数**:
- `persona_id`: 人设ID

**响应示例**:
```json
{
  "message": "人设删除成功",
  "persona_id": "custom_001"
}
```

### 获取人设详情

**GET** `/personas/{persona_id}`

获取指定人设的详细信息。

**路径参数**:
- `persona_id`: 人设ID

**响应格式**: 同人设对象结构

---

## 动态字幕接口

TextLoom 集成了 [PyCaps](https://github.com/francozanardi/pycaps) 开源动态字幕引擎，提供专业级的CSS动态字幕渲染能力。支持多种内置模板，可将视频与SRT字幕文件合成为带有动态字幕效果的视频。

### 获取PyCaps模板列表

**GET** `/dynamic-subtitles/templates`

获取可用的PyCaps模板列表。

**认证要求**: 无需认证（公开接口）

**响应示例**:
```json
{
  "success": true,
  "templates": [
    "hype",
    "minimalist", 
    "explosive",
    "vibrant"
  ],
  "total": 4
}
```

### 获取PyCaps配置状态

**GET** `/dynamic-subtitles/config`

获取PyCaps动态字幕系统的配置状态。

**认证要求**: 无需认证（公开接口）

**响应示例**:
```json
{
  "success": true,
  "config": {
    "enabled": true,
    "engine": "PyCaps",
    "version": "1.0.0",
    "supported_formats": ["srt"],
    "available_templates": 4
  }
}
```

### 处理动态字幕生成

**POST** `/dynamic-subtitles/process`

将视频文件与SRT字幕文件合成为带有动态字幕效果的视频。

**认证要求**: 需要测试Token（仅开发/测试环境）

**请求头**:
```
x-test-token: test-token
Content-Type: application/json
```

**请求参数**:
```json
{
  "video_url": "string (必填) - 原视频文件URL",
  "subtitles_url": "string (必填) - SRT字幕文件URL", 
  "template": "string (必填) - PyCaps模板名称"
}
```

**支持的模板**:
- `hype` - 动感炫酷风格，适合娱乐、游戏、体育类内容
- `minimalist` - 简约现代风格，适合商务、教育、纪录片
- `explosive` - 爆炸震撼风格，适合动作、惊悚、宣传片
- `vibrant` - 活泼多彩风格，适合儿童、音乐、创意内容

**响应示例**:
```json
{
  "success": true,
  "video_url": "https://storage.example.com/pycaps_subtitle_task_20240115_103000.mp4",
  "original_video_url": "https://example.com/original_video.mp4",
  "template": "hype",
  "processed": true,
  "message": "PyCaps字幕处理成功",
  "processing_info": {
    "segments_processed": 50,
    "words_generated": 245,
    "processing_time_seconds": 125.8,
    "output_file_size_mb": 19.14
  }
}
```

**错误响应示例**:
```json
{
  "success": false,
  "error": "PyCaps处理失败: 视频文件下载失败",
  "task_id": null,
  "processed": false
}
```

### 检查PyCaps状态（开发调试）

**GET** `/dynamic-subtitles/test/pycaps-status`

获取PyCaps系统的详细状态信息，用于开发调试。

**认证要求**: 需要测试Token

**请求头**:
```
x-test-token: test-token
```

**响应示例**:
```json
{
  "success": true,
  "pycaps_available": true,
  "dependencies": {
    "playwright": "installed",
    "chromium": "available",
    "python_version": "3.9.7"
  },
  "config": {
    "workspace_dir": "/tmp/textloom_workspace",
    "temp_dir": "/tmp",
    "enabled": true
  },
  "templates": {
    "builtin_count": 4,
    "local_count": 0,
    "available_templates": ["hype", "minimalist", "explosive", "vibrant"]
  },
  "system_info": {
    "chromium_version": "119.0.6045.105",
    "playwright_version": "1.40.0",
    "memory_usage_mb": 245.8,
    "cpu_usage_percent": 15.2
  }
}
```

### 使用流程

#### 1. 基本使用流程

```bash
# 1. 检查模板列表
curl -X GET "http://localhost:48095/dynamic-subtitles/templates"

# 2. 处理动态字幕
curl -X POST "http://localhost:48095/dynamic-subtitles/process" \
  -H "Content-Type: application/json" \
  -H "x-test-token: test-token" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "subtitles_url": "https://example.com/subtitles.srt",
    "template": "hype"
  }'
```

#### 2. Python客户端示例

```python
import requests

class PyCapsClient:
    def __init__(self, base_url="http://localhost:48095", test_token="test-token"):
        self.base_url = base_url
        self.test_token = test_token
    
    def get_templates(self):
        """获取可用模板列表"""
        response = requests.get(f"{self.base_url}/dynamic-subtitles/templates")
        response.raise_for_status()
        return response.json()
    
    def process_subtitles(self, video_url, subtitles_url, template):
        """处理动态字幕"""
        data = {
            "video_url": video_url,
            "subtitles_url": subtitles_url,
            "template": template
        }
        
        headers = {
            "x-test-token": self.test_token,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/dynamic-subtitles/process",
            json=data,
            headers=headers,
            timeout=300  # 5分钟超时
        )
        response.raise_for_status()
        return response.json()
    
    def check_status(self):
        """检查PyCaps状态"""
        headers = {"x-test-token": self.test_token}
        response = requests.get(
            f"{self.base_url}/dynamic-subtitles/test/pycaps-status",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

# 使用示例
client = PyCapsClient()

# 获取模板
templates = client.get_templates()
print(f"可用模板: {templates['templates']}")

# 处理字幕
result = client.process_subtitles(
    video_url="https://example.com/video.mp4",
    subtitles_url="https://example.com/subtitles.srt", 
    template="hype"
)
print(f"处理完成: {result['video_url']}")
```

#### 3. JavaScript客户端示例

```javascript
class PyCapsClient {
    constructor(baseURL = 'http://localhost:48095', testToken = 'test-token') {
        this.baseURL = baseURL;
        this.testToken = testToken;
    }
    
    async getTemplates() {
        const response = await fetch(`${this.baseURL}/dynamic-subtitles/templates`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }
    
    async processSubtitles(videoUrl, subtitlesUrl, template) {
        const response = await fetch(`${this.baseURL}/dynamic-subtitles/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-test-token': this.testToken
            },
            body: JSON.stringify({
                video_url: videoUrl,
                subtitles_url: subtitlesUrl,
                template: template
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }
    
    async checkStatus() {
        const response = await fetch(`${this.baseURL}/dynamic-subtitles/test/pycaps-status`, {
            headers: {
                'x-test-token': this.testToken
            }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }
}

// 使用示例
const client = new PyCapsClient();

try {
    // 获取模板
    const templates = await client.getTemplates();
    console.log(`可用模板: ${templates.templates}`);
    
    // 处理字幕
    const result = await client.processSubtitles(
        'https://example.com/video.mp4',
        'https://example.com/subtitles.srt',
        'hype'
    );
    console.log(`处理完成: ${result.video_url}`);
} catch (error) {
    console.error('错误:', error.message);
}
```

### 技术实现说明

#### SRT到PyCaps转换

系统自动将SRT字幕格式转换为PyCaps需要的词级JSON格式：

1. **时间戳分配**: 将句级时间戳按词长度比例分配到单词级别
2. **文档结构**: 转换为PyCaps的Document → Segment → Line → Word层级结构
3. **布局信息**: 自动生成空的布局信息供PyCaps模板系统使用

#### 异步处理架构

1. **线程隔离**: 使用独立线程运行PyCaps避免与FastAPI的asyncio事件循环冲突
2. **超时处理**: 支持处理超时和错误恢复机制
3. **临时文件管理**: 自动清理下载的临时文件和工作目录

#### 浏览器渲染

基于Playwright + Chromium的高质量渲染：
- CSS动画支持
- 字体和样式精确渲染  
- 跨平台一致性
- 高分辨率输出

---

## 文件上传接口

### 批量文件上传

**POST** `/tasks/attachments/upload`

批量上传文件到对象存储，返回可用于视频任务的URL列表。

**认证要求**: 需要API Key认证

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
      "filename": "video.mp4",
      "url": "https://storage.example.com/uploads/2024/01/15/uuid_video.mp4",
      "object_key": "uploads/2024/01/15/uuid_video.mp4",
      "media_type": "video",
      "size": 5242880,
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
    "video_count": 1,
    "total_size": 5347328
  },
  "warnings": [
    "不支持的文件类型: failed_file.xyz"
  ]
}
```

**使用方法**:
1. 上传文件获取URL列表
2. 将返回的URL用作视频任务的 `media_urls` 参数
3. 系统自动根据文件类型进行分类处理

---

## 监控和健康检查接口

### 基础健康检查

**GET** `/health`

获取系统基础健康状态。

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "celery": {
    "status": "connected",
    "workers": 3,
    "broker": "redis"
  },
  "database": {
    "async_pool": {
      "status": "healthy",
      "pool_size": 20,
      "connections_in_use": 5,
      "available_connections": 15,
      "overflow_connections": 0,
      "utilization_rate": 25.0
    },
    "sync_pool": {
      "status": "healthy",
      "connection_test": "ok",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  },
  "connection_pool_config": {
    "async_pool_size": 20,
    "async_max_overflow": 10,
    "celery_pool_size": 10,
    "celery_max_overflow": 5,
    "pool_recycle_seconds": 3600
  },
  "system_config": {
    "max_file_size_mb": 50,
    "celery_worker_concurrency": 4,
    "max_concurrent_tasks": 10
  }
}
```

### 系统根信息

**GET** `/`

获取系统基础信息和Celery状态。

**响应示例**:
```json
{
  "message": "TextLoom API - Celery架构",
  "version": "1.0.0",
  "docs": "/docs",
  "celery_status": {
    "available": true,
    "workers": 3,
    "broker": "redis"
  },
  "architecture": "Celery + Redis"
}
```

### Prometheus指标

**GET** `/monitoring/metrics`

获取Prometheus格式的系统指标数据。

**响应格式**: text/plain (Prometheus格式)

**响应示例**:
```
# HELP textloom_tasks_total Total number of tasks
# TYPE textloom_tasks_total counter
textloom_tasks_total{status="completed"} 140
textloom_tasks_total{status="failed"} 2
textloom_tasks_total{status="processing"} 3

# HELP textloom_task_duration_seconds Task processing duration
# TYPE textloom_task_duration_seconds histogram
textloom_task_duration_seconds_bucket{le="60"} 10
textloom_task_duration_seconds_bucket{le="300"} 85
textloom_task_duration_seconds_bucket{le="600"} 130
textloom_task_duration_seconds_bucket{le="+Inf"} 140

# HELP textloom_active_connections Active database connections
# TYPE textloom_active_connections gauge
textloom_active_connections 5
```

### 监控状态

**GET** `/monitoring/status`

获取详细的监控服务状态。

**响应示例**:
```json
{
  "running": true,
  "uptime_seconds": 86400,
  "config": {
    "prometheus_enabled": true,
    "log_monitoring_enabled": true,
    "alert_manager_enabled": true
  },
  "collectors": {
    "task_metrics": "active",
    "database_metrics": "active",
    "system_metrics": "active"
  },
  "system_info": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "disk_usage": {
      "/": 65.3
    },
    "load_average": [1.5, 1.2, 1.0]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 活跃告警

**GET** `/monitoring/alerts`

获取当前活跃的告警信息。

**响应示例**:
```json
{
  "alerts": [
    {
      "rule_name": "high_cpu_usage",
      "severity": "warning",
      "message": "CPU使用率超过80%",
      "value": 85.2,
      "threshold": 80.0,
      "timestamp": "2024-01-15T10:25:00Z",
      "duration": 300
    }
  ],
  "count": 1,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 告警历史

**GET** `/monitoring/alerts/history`

获取历史告警记录。

**查询参数**:
- `hours`: 查询最近N小时的历史（1-168，默认24）

**响应示例**:
```json
{
  "alerts": [
    {
      "rule_name": "database_connection_failed",
      "severity": "critical",
      "message": "数据库连接失败",
      "timestamp": "2024-01-15T08:15:00Z",
      "resolved_at": "2024-01-15T08:20:00Z",
      "duration": 300
    }
  ],
  "count": 1,
  "time_range_hours": 24,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 错误日志

**GET** `/monitoring/logs/errors`

获取最近的错误日志。

**查询参数**:
- `hours`: 查询最近N小时的错误（1-24，默认1）

**响应示例**:
```json
{
  "errors": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "level": "ERROR",
      "logger": "textloom.tasks",
      "message": "视频生成失败: 素材下载超时",
      "task_id": "uuid",
      "traceback": "Traceback (most recent call last)..."
    }
  ],
  "count": 1,
  "time_range_hours": 1,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 综合健康检查

**GET** `/monitoring/health/comprehensive`

获取全面的系统健康评估。

**响应示例**:
```json
{
  "overall_health": {
    "score": 85,
    "level": "good",
    "level_text": "良好",
    "issues": [
      "最近1小时内 2 个错误"
    ],
    "total_issues": 1
  },
  "basic_health": {
    "status": "healthy",
    "version": "1.0.0",
    "celery": {
      "status": "connected",
      "workers": 3
    },
    "database": {
      "async_pool": {
        "status": "healthy",
        "utilization_rate": 25.0
      }
    }
  },
  "monitoring_status": {
    "running": true,
    "uptime_seconds": 86400
  },
  "active_alerts": {
    "count": 1,
    "critical_count": 0,
    "alerts": [...]
  },
  "recent_errors": {
    "count": 2,
    "errors": [...]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Celery集群状态

**GET** `/tasks/celery/status`

获取Celery集群的详细状态。

**响应示例**:
```json
{
  "celery_status": "running",
  "workers": [
    {
      "worker_name": "worker1@hostname",
      "active_tasks": 2,
      "processed_tasks": 150,
      "status": "online"
    },
    {
      "worker_name": "worker2@hostname",
      "active_tasks": 1,
      "processed_tasks": 98,
      "status": "online"
    }
  ],
  "total_workers": 2,
  "queue_status": {
    "pending_tasks": 5,
    "processing_tasks": 3
  }
}
```

### 任务队列状态

**GET** `/tasks/queue/status`

获取任务队列的详细状态信息。

**响应示例**:
```json
{
  "queue_status": {
    "pending": 5,
    "processing": 3,
    "completed": 140,
    "failed": 2
  },
  "average_processing_time": 420.5,
  "celery_info": {
    "available": true,
    "active_workers": 3,
    "total_active_tasks": 3
  }
}
```

---

## 错误代码说明

### HTTP状态码

TextLoom API 使用标准HTTP状态码：

- `200` - 请求成功
- `201` - 创建成功
- `400` - 请求参数错误
- `401` - 未授权（需要登录）
- `403` - 禁止访问（权限不足）
- `404` - 资源不存在
- `422` - 数据验证失败
- `500` - 服务器内部错误
- `503` - 服务不可用

### 错误响应格式

```json
{
  "detail": "错误描述信息",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "uuid"
}
```

### 业务错误代码

#### 认证相关 (AUTH_*)
- `AUTH_API_KEY_MISSING` - 缺少API Key
- `AUTH_API_KEY_INVALID` - API Key无效或已过期
- `AUTH_API_KEY_DISABLED` - API Key已被禁用
- `AUTH_QUOTA_EXCEEDED` - 配额已用完
- `AUTH_TOKEN_EXPIRED` - JWT访问令牌已过期（管理员功能）
- `AUTH_TOKEN_INVALID` - JWT令牌格式无效（管理员功能）
- `AUTH_INSUFFICIENT_PERMISSIONS` - 权限不足
- `AUTH_USER_DISABLED` - 用户账户已被禁用

#### 任务相关 (TASK_*)
- `TASK_NOT_FOUND` - 任务不存在
- `TASK_INVALID_STATUS` - 任务状态无效
- `TASK_CREATION_FAILED` - 任务创建失败
- `TASK_PROCESSING_ERROR` - 任务处理异常
- `TASK_TIMEOUT` - 任务处理超时
- `TASK_RETRY_LIMIT_EXCEEDED` - 超过最大重试次数

#### 文件相关 (FILE_*)
- `FILE_TOO_LARGE` - 文件超过大小限制
- `FILE_TYPE_NOT_SUPPORTED` - 不支持的文件类型
- `FILE_UPLOAD_FAILED` - 文件上传失败
- `FILE_DOWNLOAD_FAILED` - 文件下载失败
- `FILE_NOT_FOUND` - 文件不存在

#### 素材相关 (MEDIA_*)
- `MEDIA_URL_INVALID` - 素材URL无效
- `MEDIA_DOWNLOAD_TIMEOUT` - 素材下载超时
- `MEDIA_ANALYSIS_FAILED` - 素材分析失败
- `MEDIA_FORMAT_ERROR` - 素材格式错误

#### 视频相关 (VIDEO_*)
- `VIDEO_GENERATION_FAILED` - 视频生成失败
- `VIDEO_SERVICE_UNAVAILABLE` - 视频服务不可用
- `VIDEO_PROCESSING_TIMEOUT` - 视频处理超时
- `VIDEO_QUALITY_ERROR` - 视频质量问题

#### 动态字幕相关 (SUBTITLE_*)
- `SUBTITLE_PYCAPS_ENGINE_ERROR` - PyCaps引擎处理失败
- `SUBTITLE_TEMPLATE_NOT_FOUND` - PyCaps模板不存在
- `SUBTITLE_SRT_FORMAT_ERROR` - SRT字幕格式错误
- `SUBTITLE_CONVERSION_FAILED` - SRT到JSON格式转换失败
- `SUBTITLE_PLAYWRIGHT_ERROR` - Playwright浏览器渲染失败
- `SUBTITLE_CHROMIUM_NOT_AVAILABLE` - Chromium浏览器不可用
- `SUBTITLE_PROCESSING_TIMEOUT` - 字幕处理超时
- `SUBTITLE_VIDEO_MERGE_FAILED` - 字幕视频合成失败

#### 系统相关 (SYSTEM_*)
- `SYSTEM_OVERLOAD` - 系统过载
- `SYSTEM_MAINTENANCE` - 系统维护中
- `SYSTEM_DATABASE_ERROR` - 数据库错误
- `SYSTEM_STORAGE_ERROR` - 存储服务错误

### 错误处理最佳实践

1. **客户端重试机制**：对于临时性错误（5xx），建议实现指数退避重试
2. **错误日志记录**：记录详细的错误信息用于调试
3. **用户友好提示**：将技术错误转换为用户可理解的提示
4. **监控告警**：对关键错误设置监控告警

---

## 示例代码和最佳实践

### Python客户端示例

```python
import requests
import time
from typing import Optional, List, Dict, Any

class TextLoomClient:
    def __init__(self, base_url: str = "http://localhost:48095", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.access_token: Optional[str] = None  # 仅用于管理员功能
        self.refresh_token: Optional[str] = None
    
    def set_api_key(self, api_key: str) -> None:
        """设置API Key"""
        self.api_key = api_key
    
    def admin_login(self, username: str, password: str) -> Dict[str, Any]:
        """管理员登录（仅管理功能需要）"""
        response = requests.post(
            f"{self.base_url}/auth/admin/login",
            json={
                "username": username,
                "password": password,
                "device_info": "Python Client v1.0"
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        
        return data
    
    def _get_headers(self, require_admin_token: bool = False) -> Dict[str, str]:
        """获取认证头"""
        headers = {"Content-Type": "application/json"}
        
        if require_admin_token:
            if not self.access_token:
                raise ValueError("管理功能需要先进行管理员登录")
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        else:
            raise ValueError("需要设置API Key或进行管理员登录")
        
        return headers
    
    def create_video_task(
        self,
        media_urls: List[str],
        title: str,
        description: str = "",
        mode: str = "multi_scene",
        script_style: str = "default",
        persona_id: Optional[int] = None,
        multi_video_count: int = 3,
        media_meta: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """创建视频任务"""
        data = {
            "media_urls": media_urls,
            "title": title,
            "description": description,
            "mode": mode,
            "script_style": script_style,
            "multi_video_count": multi_video_count
        }
        
        if persona_id:
            data["persona_id"] = persona_id
        
        if media_meta:
            data["media_meta"] = json.dumps(media_meta, ensure_ascii=False)
        
        response = requests.post(
            f"{self.base_url}/tasks/create-video-task",
            data=data,
            headers={"X-API-Key": self.api_key}
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        response = requests.get(
            f"{self.base_url}/tasks/{task_id}/status",
            headers=headers
        )
        response.raise_for_status()
        
        return response.json()
    
    def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 1800,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise Exception(f"任务失败: {status.get('error_message', '未知错误')}")
            
            print(f"任务进度: {status['progress']}% - {status.get('stage_message', '处理中...')}")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"任务在{timeout}秒内未完成")
    
    def upload_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """批量上传文件"""
        files = []
        for path in file_paths:
            files.append(
                ("files", (os.path.basename(path), open(path, "rb")))
            )
        
        try:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            
            response = requests.post(
                f"{self.base_url}/tasks/attachments/upload",
                files=files,
                headers=headers
            )
            response.raise_for_status()
            
            return response.json()
        finally:
            # 关闭文件句柄
            for _, (_, file_obj) in files:
                file_obj.close()
    
    def create_api_user(self, username: str, display_name: str = "", 
                       description: str = "", quota_limit: Optional[int] = None,
                       is_active: bool = True) -> Dict[str, Any]:
        """创建API用户（需要管理员权限）"""
        data = {
            "username": username,
            "is_active": is_active
        }
        if display_name:
            data["display_name"] = display_name
        if description:
            data["description"] = description
        if quota_limit is not None:
            data["quota_limit"] = quota_limit
        
        response = requests.post(
            f"{self.base_url}/auth/api-users",
            json=data,
            headers=self._get_headers(require_admin_token=True)
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_api_users(self, is_active: Optional[bool] = None, 
                     limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """获取API用户列表（需要管理员权限）"""
        params = {"limit": limit, "offset": offset}
        if is_active is not None:
            params["is_active"] = is_active
        
        response = requests.get(
            f"{self.base_url}/auth/api-users",
            params=params,
            headers=self._get_headers(require_admin_token=True)
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_pycaps_templates(self) -> Dict[str, Any]:
        """获取PyCaps模板列表"""
        response = requests.get(f"{self.base_url}/dynamic-subtitles/templates")
        response.raise_for_status()
        return response.json()
    
    def process_dynamic_subtitles(
        self,
        video_url: str,
        subtitles_url: str, 
        template: str,
        test_token: str = "test-token"
    ) -> Dict[str, Any]:
        """处理动态字幕"""
        data = {
            "video_url": video_url,
            "subtitles_url": subtitles_url,
            "template": template
        }
        
        headers = {
            "x-test-token": test_token,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/dynamic-subtitles/process",
            json=data,
            headers=headers,
            timeout=300  # PyCaps处理可能需要较长时间
        )
        response.raise_for_status()
        
        return response.json()
    
    def check_pycaps_status(self, test_token: str = "test-token") -> Dict[str, Any]:
        """检查PyCaps状态"""
        headers = {"x-test-token": test_token}
        response = requests.get(
            f"{self.base_url}/dynamic-subtitles/test/pycaps-status",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

# 使用示例
def main():
    # 方式1：使用API Key（推荐）
    client = TextLoomClient(api_key="sk-proj-your-api-key-here")
    
    # 或者后续设置
    # client = TextLoomClient()
    # client.set_api_key("sk-proj-your-api-key-here")
    
    # 上传文件
    file_paths = ["document.md", "image.jpg", "video.mp4"]
    upload_result = client.upload_files(file_paths)
    
    # 提取成功上传的URL
    media_urls = [
        item["url"] for item in upload_result["items"] 
        if item["success"]
    ]
    
    print(f"成功上传 {len(media_urls)} 个文件")
    
    # 创建视频任务
    task = client.create_video_task(
        media_urls=media_urls,
        title="AI产品演示视频",
        description="基于上传素材生成的产品演示视频",
        mode="multi_scene",
        script_style="product_geek",
        multi_video_count=3,
        media_meta={
            media_urls[0]: "产品介绍文档",
            media_urls[1]: "产品展示图片",
            media_urls[2]: "功能演示视频"
        }
    )
    
    print(f"任务创建成功: {task['id']}")
    
    # 等待任务完成
    try:
        final_status = client.wait_for_completion(task["id"])
        
        print("任务完成！生成的视频:")
        for video in final_status["multi_video_info"]["completed_videos"]:
            print(f"- 风格: {video['script_style']}")
            print(f"  视频: {video['video_url']}")
            print(f"  缩略图: {video['thumbnail_url']}")
            print(f"  时长: {video['duration']}秒")
            
    except Exception as e:
        print(f"任务失败: {e}")

# 管理员功能示例
def admin_example():
    client = TextLoomClient()
    
    # 管理员登录
    admin_result = client.admin_login("admin_user", "admin_password")
    print(f"管理员登录成功: {admin_result['user']['username']}")
    
    # 创建API用户
    api_user = client.create_api_user(
        username="partner_001",
        display_name="合作伙伴A",
        description="第三方集成客户",
        quota_limit=1000
    )
    print(f"创建API用户成功: {api_user['username']}")
    print(f"API Key: {api_user['api_key']}")
    
    # 获取API用户列表
    users = client.get_api_users()
    print(f"当前API用户数: {users['total']}")

# PyCaps动态字幕示例
def pycaps_example():
    client = TextLoomClient()
    
    try:
        # 获取可用模板
        templates_result = client.get_pycaps_templates()
        templates = templates_result['templates']
        print(f"可用PyCaps模板: {templates}")
        
        # 检查PyCaps状态
        status = client.check_pycaps_status()
        print(f"PyCaps状态: {'可用' if status['pycaps_available'] else '不可用'}")
        
        # 处理动态字幕
        result = client.process_dynamic_subtitles(
            video_url="https://res.bifrostv.com/easegen-core/video/example.mp4",
            subtitles_url="https://res.bifrostv.com/easegen-core/subtitle/example.srt",
            template="hype"
        )
        
        if result['success']:
            print(f"动态字幕处理成功!")
            print(f"原视频: {result['original_video_url']}")
            print(f"处理后视频: {result['video_url']}")
            print(f"使用模板: {result['template']}")
            if 'processing_info' in result:
                info = result['processing_info']
                print(f"处理信息:")
                print(f"  - 字幕段数: {info.get('segments_processed', 'N/A')}")
                print(f"  - 生成词数: {info.get('words_generated', 'N/A')}")
                print(f"  - 处理时间: {info.get('processing_time_seconds', 'N/A')}秒")
                print(f"  - 文件大小: {info.get('output_file_size_mb', 'N/A')}MB")
        else:
            print(f"动态字幕处理失败: {result.get('error', '未知错误')}")
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("需要有效的测试token才能使用PyCaps功能")
        else:
            print(f"请求失败: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"PyCaps处理异常: {e}")

if __name__ == "__main__":
    main()
    # pycaps_example()  # 取消注释以运行PyCaps示例
```

### JavaScript/Node.js客户端示例

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class TextLoomClient {
    constructor(baseURL = 'http://localhost:48095', apiKey = null) {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
        this.accessToken = null;  // 仅用于管理员功能
        this.refreshToken = null;
        
        this.client = axios.create({
            baseURL: this.baseURL,
            timeout: 30000
        });
        
        // 请求拦截器：自动添加认证头
        this.client.interceptors.request.use(
            config => {
                if (this.accessToken) {
                    config.headers.Authorization = `Bearer ${this.accessToken}`;
                } else if (this.apiKey) {
                    config.headers['X-API-Key'] = this.apiKey;
                }
                return config;
            },
            error => Promise.reject(error)
        );
        
        // 响应拦截器：自动处理token刷新
        this.client.interceptors.response.use(
            response => response,
            async error => {
                if (error.response?.status === 401 && this.refreshToken) {
                    try {
                        await this.refreshAccessToken();
                        // 重试原请求
                        return this.client.request(error.config);
                    } catch (refreshError) {
                        // 刷新失败，清除token
                        this.accessToken = null;
                        this.refreshToken = null;
                        throw refreshError;
                    }
                }
                throw error;
            }
        );
    }
    
    setApiKey(apiKey) {
        this.apiKey = apiKey;
    }
    
    async adminLogin(username, password, deviceInfo = 'Node.js Client v1.0') {
        const response = await this.client.post('/auth/admin/login', {
            username,
            password,
            device_info: deviceInfo
        });
        
        this.accessToken = response.data.access_token;
        this.refreshToken = response.data.refresh_token;
        
        return response.data;
    }
    
    async refreshAccessToken() {
        const response = await this.client.post('/auth/refresh', {
            refresh_token: this.refreshToken
        });
        
        this.accessToken = response.data.access_token;
        return response.data;
    }
    
    async createVideoTask({
        mediaUrls,
        title,
        description = '',
        mode = 'multi_scene',
        scriptStyle = 'default',
        personaId = null,
        multiVideoCount = 3,
        mediaMeta = null
    }) {
        const formData = new FormData();
        
        // 添加媒体URL数组
        mediaUrls.forEach(url => {
            formData.append('media_urls', url);
        });
        
        formData.append('title', title);
        formData.append('description', description);
        formData.append('mode', mode);
        formData.append('script_style', scriptStyle);
        formData.append('multi_video_count', multiVideoCount.toString());
        
        if (personaId !== null) {
            formData.append('persona_id', personaId.toString());
        }
        
        if (mediaMeta) {
            formData.append('media_meta', JSON.stringify(mediaMeta));
        }
        
        const headers = formData.getHeaders();
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        const response = await this.client.post('/tasks/create-video-task', formData, {
            headers
        });
        
        return response.data;
    }
    
    async getTaskStatus(taskId) {
        const response = await this.client.get(`/tasks/${taskId}/status`);
        return response.data;
    }
    
    async waitForCompletion(taskId, timeout = 1800000, pollInterval = 10000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            const status = await this.getTaskStatus(taskId);
            
            if (status.status === 'completed') {
                return status;
            } else if (status.status === 'failed') {
                throw new Error(`任务失败: ${status.error_message || '未知错误'}`);
            }
            
            console.log(`任务进度: ${status.progress}% - ${status.stage_message || '处理中...'}`);
            
            await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
        
        throw new Error(`任务在${timeout/1000}秒内未完成`);
    }
    
    async uploadFiles(filePaths) {
        const formData = new FormData();
        
        for (const filePath of filePaths) {
            const fileStream = fs.createReadStream(filePath);
            const fileName = require('path').basename(filePath);
            formData.append('files', fileStream, fileName);
        }
        
        const headers = formData.getHeaders();
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        
        const response = await this.client.post('/tasks/attachments/upload', formData, {
            headers,
            maxContentLength: Infinity,
            maxBodyLength: Infinity
        });
        
        return response.data;
    }
    
    async getPersonas() {
        const response = await this.client.get('/personas/');
        return response.data;
    }
    
    async getSystemHealth() {
        const response = await this.client.get('/health');
        return response.data;
    }
    
    async createApiUser(username, displayName = '', description = '', quotaLimit = null, isActive = true) {
        const data = {
            username,
            is_active: isActive
        };
        if (displayName) data.display_name = displayName;
        if (description) data.description = description;
        if (quotaLimit !== null) data.quota_limit = quotaLimit;
        
        const response = await this.client.post('/auth/api-users', data, {
            headers: {
                'Authorization': `Bearer ${this.accessToken}`
            }
        });
        
        return response.data;
    }
    
    async getApiUsers(isActive = null, limit = 50, offset = 0) {
        const params = { limit, offset };
        if (isActive !== null) params.is_active = isActive;
        
        const response = await this.client.get('/auth/api-users', {
            params,
            headers: {
                'Authorization': `Bearer ${this.accessToken}`
            }
        });
        
        return response.data;
    }
    
    async getPyCapsTemplates() {
        const response = await this.client.get('/dynamic-subtitles/templates');
        return response.data;
    }
    
    async processDynamicSubtitles(videoUrl, subtitlesUrl, template, testToken = 'test-token') {
        const response = await this.client.post('/dynamic-subtitles/process', {
            video_url: videoUrl,
            subtitles_url: subtitlesUrl,
            template: template
        }, {
            headers: {
                'x-test-token': testToken
            },
            timeout: 300000  // 5分钟超时
        });
        
        return response.data;
    }
    
    async checkPyCapsStatus(testToken = 'test-token') {
        const response = await this.client.get('/dynamic-subtitles/test/pycaps-status', {
            headers: {
                'x-test-token': testToken
            }
        });
        return response.data;
    }
}

// 使用示例
async function main() {
    // 方式1：使用API Key（推荐）
    const client = new TextLoomClient('http://localhost:48095', 'sk-proj-your-api-key-here');
    
    // 或者后续设置
    // const client = new TextLoomClient();
    // client.setApiKey('sk-proj-your-api-key-here');
    
    try {
        
        // 上传文件
        const filePaths = ['./document.md', './image.jpg', './video.mp4'];
        const uploadResult = await client.uploadFiles(filePaths);
        
        // 提取成功上传的URL
        const mediaUrls = uploadResult.items
            .filter(item => item.success)
            .map(item => item.url);
            
        console.log(`成功上传 ${mediaUrls.length} 个文件`);
        
        // 获取可用人设
        const personas = await client.getPersonas();
        console.log(`可用人设: ${personas.length} 个`);
        
        // 创建视频任务
        const task = await client.createVideoTask({
            mediaUrls,
            title: 'AI产品演示视频',
            description: '基于上传素材生成的产品演示视频',
            mode: 'multi_scene',
            scriptStyle: 'product_geek',
            multiVideoCount: 3,
            personaId: personas.find(p => p.name === '产品极客')?.id,
            mediaMeta: {
                [mediaUrls[0]]: '产品介绍文档',
                [mediaUrls[1]]: '产品展示图片',
                [mediaUrls[2]]: '功能演示视频'
            }
        });
        
        console.log(`任务创建成功: ${task.id}`);
        
        // 等待任务完成
        const finalStatus = await client.waitForCompletion(task.id);
        
        console.log('任务完成！生成的视频:');
        finalStatus.multi_video_info.completed_videos.forEach(video => {
            console.log(`- 风格: ${video.script_style}`);
            console.log(`  视频: ${video.video_url}`);
            console.log(`  缩略图: ${video.thumbnail_url}`);
            console.log(`  时长: ${video.duration}秒`);
        });
        
    } catch (error) {
        console.error('错误:', error.response?.data || error.message);
    }
}

// 管理员功能示例
async function adminExample() {
    const client = new TextLoomClient();
    
    try {
        // 管理员登录
        const adminResult = await client.adminLogin('admin_user', 'admin_password');
        console.log(`管理员登录成功: ${adminResult.user.username}`);
        
        // 创建API用户
        const apiUser = await client.createApiUser(
            'partner_001',
            '合作伙伴A',
            '第三方集成客户',
            1000
        );
        console.log(`创建API用户成功: ${apiUser.username}`);
        console.log(`API Key: ${apiUser.api_key}`);
        
        // 获取API用户列表
        const users = await client.getApiUsers();
        console.log(`当前API用户数: ${users.total}`);
        
    } catch (error) {
        console.error('管理员操作错误:', error.response?.data || error.message);
    }
}

// PyCaps动态字幕示例
async function pycapsExample() {
    const client = new TextLoomClient();
    
    try {
        // 获取可用模板
        const templatesResult = await client.getPyCapsTemplates();
        console.log(`可用PyCaps模板: ${templatesResult.templates}`);
        
        // 检查PyCaps状态
        const status = await client.checkPyCapsStatus();
        console.log(`PyCaps状态: ${status.pycaps_available ? '可用' : '不可用'}`);
        
        if (!status.pycaps_available) {
            console.log('PyCaps不可用，跳过字幕处理示例');
            return;
        }
        
        // 处理动态字幕
        const result = await client.processDynamicSubtitles(
            'https://res.bifrostv.com/easegen-core/video/example.mp4',
            'https://res.bifrostv.com/easegen-core/subtitle/example.srt',
            'hype'
        );
        
        if (result.success) {
            console.log('动态字幕处理成功!');
            console.log(`原视频: ${result.original_video_url}`);
            console.log(`处理后视频: ${result.video_url}`);
            console.log(`使用模板: ${result.template}`);
            
            if (result.processing_info) {
                const info = result.processing_info;
                console.log('处理信息:');
                console.log(`  - 字幕段数: ${info.segments_processed || 'N/A'}`);
                console.log(`  - 生成词数: ${info.words_generated || 'N/A'}`);
                console.log(`  - 处理时间: ${info.processing_time_seconds || 'N/A'}秒`);
                console.log(`  - 文件大小: ${info.output_file_size_mb || 'N/A'}MB`);
            }
        } else {
            console.log(`动态字幕处理失败: ${result.error || '未知错误'}`);
        }
        
    } catch (error) {
        if (error.response?.status === 403) {
            console.log('需要有效的测试token才能使用PyCaps功能');
        } else {
            console.error('PyCaps处理异常:', error.response?.data || error.message);
        }
    }
}

if (require.main === module) {
    main();
    // pycapsExample();  // 取消注释以运行PyCaps示例
}

module.exports = TextLoomClient;
```

### 最佳实践

#### 1. 错误处理和重试

```python
import time
import random
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code < 500 or attempt == max_retries:
                        raise
                    
                    # 指数退避 + 随机抖动
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0.1, 0.3) * delay
                    time.sleep(delay + jitter)
                    
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 使用装饰器
@retry_with_backoff(max_retries=3, base_delay=1, max_delay=30)
def create_task_with_retry(client, **kwargs):
    return client.create_video_task(**kwargs)
```

#### 2. 异步任务监控

```python
import asyncio
import aiohttp

async def monitor_multiple_tasks(client, task_ids):
    """并发监控多个任务"""
    async def monitor_single_task(task_id):
        while True:
            status = await client.get_task_status_async(task_id)
            
            if status['status'] in ['completed', 'failed']:
                return task_id, status
            
            await asyncio.sleep(10)
    
    # 并发监控所有任务
    results = await asyncio.gather(*[
        monitor_single_task(task_id) for task_id in task_ids
    ])
    
    return dict(results)
```

#### 3. 文件上传优化

```python
def chunked_file_upload(client, file_paths, chunk_size=10):
    """分块上传大量文件"""
    results = []
    
    for i in range(0, len(file_paths), chunk_size):
        chunk = file_paths[i:i + chunk_size]
        print(f"上传第 {i//chunk_size + 1} 批文件 ({len(chunk)} 个)")
        
        chunk_result = client.upload_files(chunk)
        results.extend(chunk_result['items'])
        
        # 避免过于频繁的请求
        time.sleep(1)
    
    return results
```

#### 4. 配置管理

```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class TextLoomConfig:
    base_url: str = "http://localhost:48095"
    username: Optional[str] = None
    password: Optional[str] = None
    max_retries: int = 3
    timeout: int = 30
    poll_interval: int = 10
    
    @classmethod
    def from_env(cls):
        """从环境变量创建配置"""
        return cls(
            base_url=os.getenv('TEXTLOOM_BASE_URL', 'http://localhost:48095'),
            username=os.getenv('TEXTLOOM_USERNAME'),
            password=os.getenv('TEXTLOOM_PASSWORD'),
            max_retries=int(os.getenv('TEXTLOOM_MAX_RETRIES', '3')),
            timeout=int(os.getenv('TEXTLOOM_TIMEOUT', '30')),
            poll_interval=int(os.getenv('TEXTLOOM_POLL_INTERVAL', '10'))
        )

# 使用配置
config = TextLoomConfig.from_env()
client = TextLoomClient(config.base_url)
```

#### 5. 日志和监控

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('textloom_client.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('textloom_client')

class LoggingTextLoomClient(TextLoomClient):
    def create_video_task(self, **kwargs):
        logger.info(f"创建视频任务: {kwargs.get('title')}")
        start_time = datetime.now()
        
        try:
            result = super().create_video_task(**kwargs)
            logger.info(f"任务创建成功: {result['id']}")
            return result
        except Exception as e:
            logger.error(f"任务创建失败: {e}")
            raise
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"任务创建耗时: {duration:.2f}秒")
    
    def wait_for_completion(self, task_id, **kwargs):
        logger.info(f"开始等待任务完成: {task_id}")
        
        try:
            result = super().wait_for_completion(task_id, **kwargs)
            logger.info(f"任务成功完成: {task_id}")
            return result
        except Exception as e:
            logger.error(f"任务失败: {task_id}, 错误: {e}")
            raise
```

#### 6. 批量处理工具

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable

class BatchProcessor:
    def __init__(self, client: TextLoomClient, max_workers: int = 5):
        self.client = client
        self.max_workers = max_workers
    
    def process_batch(
        self,
        items: List[Dict],
        processor: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """批量处理任务"""
        results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_item = {
                executor.submit(processor, item): item 
                for item in items
            }
            
            # 收集结果
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append({
                        'item': item,
                        'result': result,
                        'success': True,
                        'error': None
                    })
                except Exception as e:
                    results.append({
                        'item': item,
                        'result': None,
                        'success': False,
                        'error': str(e)
                    })
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(items))
        
        return results

# 使用示例
def batch_create_tasks():
    client = TextLoomClient()
    client.login("username", "password")
    
    processor = BatchProcessor(client, max_workers=3)
    
    task_configs = [
        {
            'media_urls': ['url1', 'url2'],
            'title': 'Task 1',
            'script_style': 'default'
        },
        {
            'media_urls': ['url3', 'url4'],
            'title': 'Task 2',
            'script_style': 'product_geek'
        }
    ]
    
    def create_single_task(config):
        return client.create_video_task(**config)
    
    def progress_callback(completed, total):
        print(f"进度: {completed}/{total} ({completed/total*100:.1f}%)")
    
    results = processor.process_batch(
        task_configs,
        create_single_task,
        progress_callback
    )
    
    successful_tasks = [r for r in results if r['success']]
    print(f"成功创建 {len(successful_tasks)} 个任务")
```

这个API文档涵盖了TextLoom系统的完整接口规范，包括详细的参数说明、响应格式、错误处理和实用的示例代码。开发者可以根据这个文档快速集成和使用TextLoom的视频生成功能。