# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
<!-- 此文件为 Claude Code (claude.ai/code) 提供在此代码库中工作的指导 -->

## 📚 Documentation Structure
<!-- 文档结构 -->

The project uses a well-organized documentation structure under the `docs/` directory:
<!-- 项目使用良好组织的文档结构，位于 docs/ 目录下 -->

- **Architecture** (`docs/architecture/`): System design, architecture reviews, and logging enhancements
- **Security** (`docs/security/`): Security audits, JWT authentication, CORS configuration, and security implementation guides
- **Performance** (`docs/performance/`): Database optimization, connection pool tuning, and performance improvements
- **Deployment** (`docs/deployment/`): CI/CD pipelines and deployment guides
- **Backup** (`docs/backup/`): Backup strategies and disaster recovery procedures

For complete navigation, refer to `docs/README.md`.
<!-- 完整导航请参考 docs/README.md -->

## Quick Commands
<!-- 快速命令 -->

### Development Commands
<!-- 开发命令 -->
```bash

# Start all services in background (recommended for production)
# 启动所有服务到后台
./start_all_services.sh

# Stop all services
# 停止所有服务
./stop_all.sh

# Install dependencies
# 安装依赖
uv sync

# Install Playwright browsers (required for dynamic subtitles)
# 安装 Playwright 浏览器（动态字幕功能必需）
playwright install chromium

# Run tests
# 运行测试
pytest tests/

# Start Celery services
# 启动 Celery 服务（Worker/Flower/Beat）
./start_celery_worker.sh worker &
./start_celery_worker.sh flower &
./start_celery_worker.sh beat &

# Individual Celery service management
# 单独的 Celery 服务管理
./start_celery_worker.sh worker   # Start Worker only
./start_celery_worker.sh flower   # Start Flower monitoring only
./start_celery_worker.sh beat     # Start Beat scheduler only

# Start Docker services (see docker/README.md for details)
# 启动Docker服务（详见docker/README.md）
docker-compose -f docker/compose/docker-compose.yml up -d
```

### Database Management
<!-- 数据库管理 -->
```bash
# Alembic migrations（SQLAlchemy ORM as single source of truth）
# Alembic 迁移（SQLAlchemy ORM 为单一事实来源）
uv run alembic revision --autogenerate -m "sync models to db"
uv run alembic upgrade head
```

### Code Quality
<!-- 代码质量 -->
```bash
# Format code
# 格式化代码
uv run black .

# Sort imports
# 排序导入
uv run isort .

# Type checking
# 类型检查
uv run mypy .

# Linting
# 代码检查
uv run flake8 .
```

### Testing
<!-- 测试 -->
```bash

# Run business e2e tests
# 运行业务端到端测试
uv run python business_e2e_test.py

# Run PyCaps dynamic subtitles integration tests
# 运行PyCaps动态字幕集成测试
export RUN_LIVE_AI_TESTS=1
export INTERNAL_TEST_TOKEN=test-token
uv run pytest tests/integration/test_dynamic_subtitles_live.py -v

```

## Internal Evaluation Endpoints (dev/staging only)
<!-- 内部评估接口（仅 dev/staging） -->

The following endpoints are exposed for rapid iteration of prompts/models. Protect with `INTERNAL_TEST_TOKEN` and send `x-test-token` header. Do not enable in production.
<!-- 以下端点用于提示词/模型的快速迭代验证。通过 INTERNAL_TEST_TOKEN 保护，并在请求头携带 x-test-token。生产环境请勿开启。 -->

- Image analysis with context: `POST /internal/analyzer/analyze-image`
- Material extract/download: `POST /internal/materials/extract-media`, `POST /internal/materials/download-and-organize`
- Script generation: `POST /internal/script/generate`
- Video generation: `POST /internal/video/generate-single`, `POST /internal/video/generate-multiple`

Example (script generation):
```bash
curl -X POST http://localhost:48095/internal/script/generate \
  -H "Content-Type: application/json" \
  -H "x-test-token: ${INTERNAL_TEST_TOKEN}" \
  -d '{
    "topic": "AI 工具趋势",
    "source_content": "近年生成式 AI 工具爆发...",
    "styles": ["professional", "viral"],
    "material_context": {"summary": {"total_count": 2, "image_count": 1, "video_count": 1}}
  }'
```

Example (video generation):
```bash
curl -X POST http://localhost:48095/internal/video/generate-single \
  -H "Content-Type: application/json" \
  -H "x-test-token: ${INTERNAL_TEST_TOKEN}" \
  -d '{
    "script_data": {
      "narration": "这是一个示例旁白",
      "scenes": [{"scene_id": 1, "narration": "片头介绍", "material_id": "mat1"}]
    },
    "media_files": [
      {"id": "mat1", "file_url": "https://example.com/a.jpg", "filename": "a.jpg"}
    ],
    "mode": "multi_scene"
  }'
```

Run live integration tests (optional, controlled):
<!-- 运行真连网集成测试（可选，受控） -->
```bash
export RUN_LIVE_AI_TESTS=1
uv run pytest tests/integration/test_internal_endpoints_live.py -q
```

## Architecture Overview
<!-- 架构概述 -->

TextLoom is an intelligent text-to-video generation system built with FastAPI and Celery that converts Markdown documents into professional video content using AI-powered analysis and script generation. The system now uses a distributed architecture with Celery and Redis for scalable background task processing.
<!-- TextLoom 是一个基于 FastAPI 和 Celery 构建的智能文本转视频生成系统，使用 AI 驱动的分析和脚本生成将 Markdown 文档转换为专业视频内容。系统现在使用基于 Celery 和 Redis 的分布式架构来实现可扩展的后台任务处理 -->

### Core Architecture Components
<!-- 核心架构组件 -->

**FastAPI Application** (`main.py`)
<!-- FastAPI 应用程序 -->
- Entry point with CORS middleware <!-- 带 CORS 中间件的入口点 -->
- Health checks and status endpoints <!-- 健康检查和状态端点 -->
- Task submission API endpoints <!-- 任务提交API端点 -->
- Database connection lifecycle management <!-- 数据库连接生命周期管理 -->

**Celery + Redis Architecture** (`celery_config.py`, `tasks/`)
<!-- Celery + Redis 架构 -->
- Distributed task queue with Redis as message broker <!-- 使用Redis作为消息代理的分布式任务队列 -->
- Horizontal scaling with multiple Worker processes <!-- 支持多Worker进程的水平扩展 -->
- Task retry and error handling mechanisms <!-- 任务重试和错误处理机制 -->
- Real-time progress tracking and status updates <!-- 实时进度跟踪和状态更新 -->
- Flower monitoring dashboard for task visualization <!-- 用于任务可视化的Flower监控面板 -->

**Database Layer** (`models/`)
<!-- 数据库层 -->
- PostgreSQL with async SQLAlchemy <!-- 使用异步 SQLAlchemy 的 PostgreSQL -->
- Supabase integration support <!-- Supabase 集成支持 -->
- Custom connection pooling with pgbouncer compatibility <!-- 与 pgbouncer 兼容的自定义连接池 -->
- Schema: `textloom_core` namespace <!-- 模式：textloom_core 命名空间 -->
- Enhanced task tracking with Celery integration fields <!-- 增强的任务跟踪，包含Celery集成字段 -->

**Processing Pipeline** (Celery Tasks):
<!-- 处理流水线（Celery任务）-->
1. **Material Processing** (0-25%): Extract and download media from documents
   <!-- 素材处理：从文档中提取和下载媒体 -->
2. **Material Analysis** (25-50%): AI-powered content analysis 
   <!-- 素材分析：AI 驱动的内容分析 -->
3. **Script Generation** (50-75%): Generate video scripts from content
   <!-- 脚本生成：从内容生成视频脚本 -->
4. **Video Generation** (75-100%): Compose final video output
   <!-- 视频生成：合成最终视频输出 -->

Each stage is implemented as a Celery task with progress callbacks and error handling.
<!-- 每个阶段都实现为带有进度回调和错误处理的Celery任务 -->

### Key Models and Status Flow
<!-- 关键模型和状态流 -->

**Task Status Flow**:
<!-- 任务状态流 -->
`pending` → `processing` → `completed` / `failed` / `cancelled`
<!-- 待处理 → 处理中 → 已完成 / 失败 / 已取消 -->

**Task Types**:
<!-- 任务类型 -->
- `TEXT_TO_VIDEO`: Full pipeline processing <!-- 完整流水线处理 -->
- `VIDEO_GENERATION`: Video composition only <!-- 仅视频合成 -->
- `DYNAMIC_SUBTITLE`: PyCaps dynamic subtitle generation <!-- PyCaps动态字幕生成 -->

**Multi-Video Support**:
<!-- 多视频支持 -->
- Single task can generate multiple video variants <!-- 单个任务可生成多个视频变体 -->
- Sub-video tasks track individual video generation <!-- 子视频任务跟踪单个视频生成 -->
- Configurable video count via `multi_video_count` <!-- 通过 multi_video_count 配置视频数量 -->

## Database Architecture
<!-- 数据库架构 -->

### Connection Management
<!-- 连接管理 -->
- Uses `asyncpg` with SQLAlchemy async <!-- 使用 asyncpg 和 SQLAlchemy 异步 -->
- Connection pooling optimized for pgbouncer <!-- 为 pgbouncer 优化的连接池 -->
- Prepared statements disabled for compatibility <!-- 为兼容性禁用预处理语句 -->
- Custom session management with automatic rollback <!-- 带自动回滚的自定义会话管理 -->

### Key Tables Structure
<!-- 关键表结构 -->
- `tasks`: Main task tracking with comprehensive metadata <!-- 主任务跟踪及综合元数据 -->
- `media_items`: Media file references and metadata <!-- 媒体文件引用和元数据 -->
- `material_analyses`: AI analysis results <!-- AI 分析结果 -->
- `personas`: Content generation personas/styles <!-- 内容生成人设/风格 -->
- `script_content`: Generated scripts and prompts <!-- 生成的脚本和提示词 -->
- `sub_video_tasks`: Individual video generation tracking <!-- 单个视频生成跟踪 -->

### Schema Organization
<!-- 模式组织 -->
All tables use the `textloom_core` schema namespace.
<!-- 所有表都使用 textloom_core 模式命名空间 -->

## PyCaps Dynamic Subtitle Integration
<!-- PyCaps动态字幕集成 -->

TextLoom integrates the open-source [PyCaps](https://github.com/francozanardi/pycaps) library for professional dynamic subtitle generation.
<!-- TextLoom集成开源PyCaps库用于专业动态字幕生成 -->

**Key Components**:
<!-- 关键组件 -->
- **PyCaps Service** (`services/pycaps_subtitle_service.py`): Main integration service <!-- 主要集成服务 -->
- **SRT Converter** (`services/pycaps_converter.py`): Converts SRT to PyCaps JSON format <!-- SRT转PyCaps JSON格式转换器 -->  
- **Template System**: Built-in templates (hype, minimalist, explosive, vibrant) <!-- 内置模板系统 -->
- **Async Processing**: Thread isolation to avoid FastAPI/Playwright conflicts <!-- 异步处理：线程隔离避免冲突 -->

**Processing Flow**:
<!-- 处理流程 -->
1. Download video and SRT files <!-- 下载视频和SRT文件 -->
2. Convert SRT to word-level JSON format <!-- 转换SRT为词级JSON格式 -->
3. Apply PyCaps template rendering with Playwright/Chromium <!-- 应用PyCaps模板渲染 -->
4. Upload processed video to storage <!-- 上传处理后的视频到存储 -->

**Template Management**:
<!-- 模板管理 -->
- Templates are managed by `TemplateService` and `TemplateFactory` <!-- 通过TemplateService和TemplateFactory管理模板 -->
- No custom template code - uses PyCaps built-in templates only <!-- 不使用自定义模板代码，仅使用PyCaps内置模板 -->
- Word-level timing automatically distributed from sentence-level SRT data <!-- 词级时间戳从句级SRT数据自动分配 -->

## Configuration System
<!-- 配置系统 -->

**Environment-based**: Uses Pydantic Settings with `.env` file support
<!-- 基于环境：使用 Pydantic Settings 和 .env 文件支持 -->

**Key Configuration Areas**:
<!-- 关键配置区域 -->
- **AI Models**: Supports OpenAI, Gemini, custom endpoints <!-- AI 模型：支持 OpenAI、Gemini、自定义端点 -->
- **Video Generation**: Custom video service integration <!-- 视频生成：自定义视频服务集成 -->
- **Storage**: MinIO, Huawei OBS support <!-- 存储：MinIO、华为 OBS 支持 -->
- **Database**: PostgreSQL/Supabase with connection tuning <!-- 数据库：PostgreSQL/Supabase 连接调优 -->
- **Task Processing**: Concurrency, timeouts, polling intervals <!-- 任务处理：并发、超时、轮询间隔 -->
- **Dynamic Subtitles**: PyCaps engine configuration and template management <!-- 动态字幕：PyCaps引擎配置和模板管理 -->

**Model Switching**: 
<!-- 模型切换 -->
- `use_gemini=True` switches to Google Gemini models <!-- use_gemini=True 切换到 Google Gemini 模型 -->
- Separate image analysis model configuration <!-- 独立的图像分析模型配置 -->
- Per-task model selection support <!-- 每任务模型选择支持 -->

## API Architecture
<!-- API 架构 -->

### Router Organization
<!-- 路由组织 -->
- `/tasks`: Task management and video generation <!-- 任务管理和视频生成 -->
- `/personas`: Content generation personas <!-- 内容生成人设 -->
- `/auth`: JWT authentication and user management <!-- JWT 认证和用户管理 -->
- `/secure-tasks`: Secure task operations with authentication <!-- 带认证的安全任务操作 -->
- `/dynamic-subtitles`: Dynamic subtitle generation <!-- 动态字幕生成 -->
- `/internal/*`: Internal evaluation endpoints (dev/staging only) <!-- 内部评估端点（仅 dev/staging） -->

### Key API Patterns
<!-- 关键 API 模式 -->
- Async/await throughout <!-- 全程使用 Async/await -->
- Background task submission via scheduler <!-- 通过调度器提交后台任务 -->
- File upload handling with size limits <!-- 带大小限制的文件上传处理 -->
- Progress tracking via polling endpoints <!-- 通过轮询端点跟踪进度 -->

### Error Handling
<!-- 错误处理 -->
- Structured error responses <!-- 结构化错误响应 -->
- Background task error capture <!-- 后台任务错误捕获 -->
- Timeout and recovery mechanisms <!-- 超时和恢复机制 -->

## Development Patterns
<!-- 开发模式 -->

### Adding New Processing Steps
<!-- 添加新的处理步骤 -->
1. Extend `TaskProcessor` in `services/` <!-- 在 services/ 中扩展 TaskProcessor -->
2. Update progress percentage ranges <!-- 更新进度百分比范围 -->
3. Add status tracking in database models <!-- 在数据库模型中添加状态跟踪 -->
4. Implement error handling and rollback <!-- 实现错误处理和回滚 -->

### Database Operations
<!-- 数据库操作 -->
- Always use `get_db_session()` context manager <!-- 始终使用 get_db_session() 上下文管理器 -->
- Implement proper transaction handling <!-- 实现正确的事务处理 -->
- Use model conversion functions for type safety <!-- 使用模型转换函数确保类型安全 -->
- Handle connection pooling edge cases <!-- 处理连接池边缘情况 -->

### Background Tasks
<!-- 后台任务 -->
- Use Celery for distributed task processing <!-- 使用 Celery 进行分布式任务处理 -->
- Implement timeout handling and retry mechanisms <!-- 实现超时处理和重试机制 -->
- Track task states in database with Celery task IDs <!-- 在数据库中跟踪任务状态及 Celery 任务 ID -->
- Use Redis as message broker for task queuing <!-- 使用 Redis 作为任务队列的消息代理 -->

### Testing
<!-- 测试 -->
- Integration tests simulate full workflows <!-- 集成测试模拟完整工作流 -->
- Business e2e tests validate core user journeys <!-- 业务端到端测试验证核心用户旅程 -->
- Use `--verbose` flag for detailed test output <!-- 使用 --verbose 标志获取详细测试输出 -->
- Database tests require running Supabase instance <!-- 数据库测试需要运行 Supabase 实例 -->

## Storage and Media Handling
<!-- 存储和媒体处理 -->

**Workspace Structure**:
<!-- 工作空间结构 -->
```
workspace/
├── materials/          # Downloaded source materials 下载的源素材
│   ├── images/         # 图片
│   ├── videos/         # 视频
│   └── audio/          # 音频
├── processed/          # Processed outputs 处理后的输出
├── keyframes/          # Video keyframe extraction 视频关键帧提取
└── logs/              # Processing logs 处理日志
```

**File Upload Limits**:
<!-- 文件上传限制 -->
- Max file size: 50MB <!-- 最大文件大小：50MB -->
- Max images per task: 20 <!-- 每个任务最多 20 张图片 -->
- Max videos per task: 5 <!-- 每个任务最多 5 个视频 -->

## Logging and Debugging
<!-- 日志和调试 -->

**Log Files**:
<!-- 日志文件 -->
- `logs/app.log`: Application logs <!-- 应用程序日志 -->
- `logs/textloom.log`: Server logs <!-- 服务器日志 -->
- `logs/textloom_error.log`: Error logs <!-- 错误日志 -->
- `workspace/logs/material_analysis.log`: Analysis logs <!-- 分析日志 -->

**Health Endpoints**:
<!-- 健康检查端点 -->
- `/health`: Service health check with database status <!-- 服务健康检查，包含数据库状态 -->
- `/`: Basic service info and Celery status <!-- 基本服务信息和Celery状态 -->

**Task Monitoring**:
<!-- 任务监控 -->
- Use `/tasks/{task_id}/status` for progress polling <!-- 使用 /tasks/{task_id}/status 进行进度轮询 -->
- Use `/health` for service health checks <!-- 使用 /health 进行服务健康检查 -->
- Celery task status and Worker monitoring via Flower dashboard <!-- 通过Flower仪表板监控Celery任务状态和Worker -->
- Database connection monitoring in health checks <!-- 健康检查中的数据库连接监控 -->

## Documentation Management
<!-- 文档管理 -->

**Adding New Documentation**:
<!-- 添加新文档 -->
- Place documents in appropriate `docs/` subdirectories based on their purpose
- Update `docs/README.md` index when adding new documents  
- Follow the established naming conventions and structure
- Include both English and Chinese documentation where applicable

**Documentation Guidelines**:
<!-- 文档指导原则 -->
- Keep technical documents in `docs/` rather than project root
- Use clear, descriptive filenames (e.g., `SECURITY_AUDIT_REPORT.md`)
- Maintain consistent markdown formatting and structure
- Update cross-references when moving or renaming documents

## Configuration File Management
<!-- 配置文件管理 -->

**⚠️ CRITICAL RULES for Configuration Files**:
<!-- 配置文件关键规则 -->

**Never modify user's `.env` file without explicit confirmation**:
<!-- 严禁未经确认修改用户的.env文件 -->
- Contains sensitive production configuration
- Changes can cause service interruption
- Always ask for confirmation before any `.env` modifications

**Single Configuration Template Policy**:
<!-- 单一配置模板政策 -->
- Only use `.env.example` as the configuration template
- Never create multiple template files (env.example, .env.template, etc.)
- Avoid user confusion about which version is correct

**Configuration File Standards**:
<!-- 配置文件标准 -->
- `.env` - Actual runtime configuration (never commit to git)
- `.env.example` - Complete configuration template (commit to git)
- Use placeholder values in template (your-api-key, your-password)
- Provide detailed comments for all configuration sections

**Before modifying any configuration**:
<!-- 修改任何配置前必须 -->
1. Ask for user confirmation
2. Create backup if needed
3. Clearly explain what will be changed
4. Verify the change won't break existing functionality

Detailed configuration management guidelines: `docs/deployment/CONFIG_FILE_MANAGEMENT.md`
<!-- 详细配置管理指导：docs/deployment/CONFIG_FILE_MANAGEMENT.md -->

# important-instruction-reminders
<!-- 重要指令提醒 -->

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

**🚨 CRITICAL: Configuration File Protection**
<!-- 关键：配置文件保护 -->
NEVER modify .env files without explicit user confirmation.
NEVER create multiple configuration template files.
ALWAYS use .env.example as the single source of truth for configuration templates.
ANY configuration changes must be approved by the user first.

IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.