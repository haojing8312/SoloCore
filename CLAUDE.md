# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

**SoloCore** 是一个开源平台，旨在帮助个人成为"AI 时代的超级个体"，打造成功的"一人公司"。该项目提供了一整套 AI 驱动的内容创作工具，包括文本转视频生成、文章写作和社交媒体内容创作。

### 核心使命
提供一套开源的、可本地部署的 AI 工具栈，并结合透明的实战教程，赋能每一个有志向的个体，使其能独立完成产品、营销和商业化的闭环。

## 仓库结构

SoloCore 是一个 **monorepo（单仓多项目）**，包含多个相互关联的项目:

### 主要项目

1. **textloom/** - 智能文本转视频系统 (Python/FastAPI)
   - 将 Markdown 文档转换为专业视频内容
   - AI 驱动的内容分析、脚本生成和视频合成
   - 基于 PyCaps 的动态字幕生成
   - Celery + Redis 分布式任务处理

2. **easegen-admin/** - 数字人课程平台后端 (Java/Spring Boot)
   - Git 子模块: https://github.com/taoofagi/easegen-admin
   - 基于 ruoyi-vue-pro 框架的模块化单体架构
   - 处理课程创建、数字人管理、AI 集成

3. **easegen-front/** - 数字人平台前端 (Vue 3/TypeScript)
   - Git 子模块: https://github.com/taoofagi/easegen-front
   - 基于 Element Plus 的表单驱动 UI
   - BPMN 工作流设计器集成

4. **editly/** - 视频编辑库 (Node.js)
   - Git 子模块（兼容 Windows 的 fork 版本）
   - 声明式视频编辑引擎
   - 被 textloom 用于视频合成

5. **frontend/** - SoloCore 统一 Web 界面（规划中）
   - 未来所有 SoloCore 功能的统一入口
   - 目前处于规划阶段

## 常用开发命令

### TextLoom (Python/FastAPI)

```bash
# 工作目录
cd textloom

# 安装依赖
uv sync

# 安装 Playwright（用于动态字幕）
playwright install chromium

# 启动所有服务 (API + Celery Worker/Flower/Beat)
./start_all_services.sh

# 停止所有服务
./stop_all.sh

# 启动单个服务
uv run uvicorn main:app --reload --host 0.0.0.0 --port 48095  # API 服务器
./start_celery_worker.sh worker &   # Worker 工作进程
./start_celery_worker.sh flower &   # 监控面板
./start_celery_worker.sh beat &     # 调度器

# 数据库迁移 (Alembic)
uv run alembic revision --autogenerate -m "sync models to db"
uv run alembic upgrade head

# 运行测试
uv run pytest tests/
uv run python business_e2e_test.py

# 运行真实 AI 集成测试（受控）
export RUN_LIVE_AI_TESTS=1
export INTERNAL_TEST_TOKEN=test-token
uv run pytest tests/integration/test_dynamic_subtitles_live.py -v

# 代码质量检查
uv run black .
uv run isort .
uv run mypy .
uv run flake8 .
```

### Easegen-Admin (Java/Spring Boot)

```bash
# 工作目录
cd easegen-admin

# 构建（跳过测试）
mvn clean install -DskipTests

# 运行应用（默认端口: 48080）
cd yudao-server
mvn spring-boot:run

# 运行测试
mvn test

# Docker 构建
docker compose --env-file docker.env up -d
```

### Easegen-Front (Vue 3/Vite)

```bash
# 工作目录
cd easegen-front

# 安装依赖（需要 pnpm >= 8.6.0）
pnpm install

# 开发
pnpm dev         # 本地开发
pnpm dev-server  # 开发服务器

# 构建
pnpm build:local  # 本地构建
pnpm build:dev    # 开发环境构建
pnpm build:prod   # 生产环境构建

# 代码质量检查
pnpm lint:eslint  # 修复 ESLint 问题
pnpm lint:format  # Prettier 格式化
pnpm lint:style   # Stylelint 修复
```

### Editly (Node.js)

```bash
# 工作目录
cd editly

# 安装依赖（需要 Node.js v18+）
npm install

# 构建
npm run build

# 测试视频生成
node dist/cli.js test_simple.json5
```

### Docker 服务

```bash
# 启动 PostgreSQL 和 Redis
docker-compose -f docker/postgres/docker-compose.yml up -d
docker-compose -f docker/redis/docker-compose.yml up -d

# 停止服务
docker-compose -f docker/postgres/docker-compose.yml down
docker-compose -f docker/redis/docker-compose.yml down
```

### Git 子模块

```bash
# 克隆包含子模块
git clone --recursive https://github.com/haojing8312/SoloCore.git

# 在已克隆的仓库中初始化子模块
git submodule update --init --recursive

# 更新所有子模块到最新版本
git submodule update --remote --merge
```

## 架构概览

### TextLoom 架构

**技术栈:**
- FastAPI（全程使用 async/await）
- Celery + Redis（分布式任务队列）
- PostgreSQL with asyncpg（异步 SQLAlchemy）
- PyCaps + Playwright（动态字幕渲染）
- AI 模型: 支持 OpenAI/Gemini

**处理流水线:**
1. 素材处理 (0-25%): 从文档中提取并下载媒体
2. 素材分析 (25-50%): AI 驱动的内容分析
3. 脚本生成 (50-75%): 生成多种风格的视频脚本
4. 视频生成 (75-100%): 两阶段视频合成与轮询

**关键模式:**
- 所有表使用 `textloom_core` schema 命名空间
- 任务状态流: `pending` → `processing` → `completed`/`failed`/`cancelled`
- 多视频支持: 单个任务可生成多个视频变体
- 后台任务使用 Celery，具有进度跟踪和重试机制
- 数据库会话使用 `get_db_session()` 上下文管理器
- 基于环境的配置，使用 Pydantic Settings

**重要组件:**
- `main.py`: FastAPI 应用入口，带 CORS 中间件
- `celery_config.py`: Celery 配置，使用 Redis broker
- `tasks/`: 每个处理阶段的 Celery 任务定义
- `models/db_models.py`: SQLAlchemy ORM 模型（单一事实来源）
- `services/`: 核心业务逻辑（处理器、生成器）
- `routers/`: API 路由定义
- `alembic/`: 数据库迁移文件

### Easegen 架构

**Easegen-Admin (后端):**
- Maven 多模块结构的模块化单体架构
- `yudao-server`: 可运行的 Spring Boot 应用（外壳容器）
- `yudao-framework`: 14 个自定义 Spring Boot starters，用于横切关注点
- `yudao-module-digitalcourse`: 数字课程创建的主要业务逻辑
- `yudao-module-ai`: AI 模型集成（OpenAI、百度、DeepSeek 等）
- MyBatis-Plus 配合 `BaseMapperX` 实现增强查询
- Redis 缓存、MySQL 持久化、Quartz 调度

**Easegen-Front (前端):**
- Vue 3 Composition API 配合 TypeScript
- 使用 `useCrudSchemas` hook 的 Schema 驱动 CRUD
- 基于 @form-create/element-ui 的动态表单
- BPMN 工作流设计器集成
- Pinia 状态管理，带持久化
- 按后端模块组织的 API 层
- 基于队列的 token 刷新重试机制

### Editly 集成

- 声明式视频编辑引擎（Node.js v18+）
- 被 textloom 用于视频合成
- Windows 兼容性需要 Node.js v18 及预编译二进制文件
- 需要 FFmpeg 进行编码
- 使用 JSON5 配置格式定义视频规格

## 关键开发规则

### 配置管理

⚠️ **严禁未经用户明确确认修改 `.env` 文件**

- `.env` 包含敏感的生产环境配置
- 只有 `.env.example` 应该被用作模板（单一事实来源）
- 严禁创建多个模板文件（env.example、.env.template 等）
- 配置更改可能导致服务中断
- 任何 `.env` 修改前必须征得用户确认

### 数据库操作 (TextLoom)

- **始终使用 `get_db_session()` 上下文管理器**进行数据库操作
- `models/db_models.py` 中的 SQLAlchemy ORM 模型是单一事实来源
- 模型修改后运行 `alembic revision --autogenerate`
- 所有表必须使用 `textloom_core` schema
- 严禁跳过迁移 - 必须将迁移文件提交到 Git
- 处理连接池边缘情况（pgbouncer 兼容性）

### 模块通信 (Easegen-Admin)

- 严禁直接引用其他模块的 Service 实现
- 使用 `-api` 模块的接口/DTO 进行模块间调用
- 示例: 使用 `yudao-module-infra-api` 接口，而非实现

### 代码风格

- TextLoom: 遵循 PEP 8，使用 Black + isort + mypy
- Easegen-Admin: 遵循现有的 Java/Spring Boot 约定
- Easegen-Front: 遵循 ESLint + Prettier 规则
- 优先编辑现有文件而非创建新文件
- 仅在明确要求时创建文档文件

## 关键功能与模式

### TextLoom 动态字幕

- 集成 PyCaps 引擎，实现基于 CSS 的动态字幕
- 从 SRT 自动分配词级时间戳
- 内置模板: hype、minimalist、explosive、vibrant
- 异步处理，线程隔离（Playwright/FastAPI 兼容性）
- API 端点位于 `/dynamic-subtitles/`

### TextLoom 内部评估端点

受 `INTERNAL_TEST_TOKEN` 保护，仅用于开发/测试环境:
- `/internal/analyzer/analyze-image` - 带上下文的 AI 图像分析
- `/internal/materials/extract-media` - 媒体提取
- `/internal/script/generate` - 多风格脚本生成
- `/internal/video/generate-single` - 单视频生成
- `/internal/video/generate-multiple` - 多视频生成

### Easegen 数字人功能

`yudao-module-digitalcourse` 中的核心实体:
- Courses、CoursePpts、CourseScenes、CourseSceneAudios
- 带审批流程的数字人管理
- SSML 语音合成（确保单个 `<speak>` 根标签）
- 视频合成验证（脚本不能为空，时长单位为毫秒）

### 安全模式

**TextLoom:**
- 基于 JWT 的认证
- 可配置允许源的 CORS
- 数据库连接凭证存储在环境变量中
- 内部测试端点受测试 token 保护

**Easegen:**
- Spring Security 配合 JWT
- 权限注解: `@PreAuthorize("@ss.hasPermission(...)")`
- 多租户支持（当前已禁用: `yudao.tenant.enable=false`）
- 使用 `deleted` 字段的逻辑删除

## 环境配置

### TextLoom 所需服务

- PostgreSQL 8.0+ 位于 `localhost:5432`（数据库: `solocore`，用户: `solocore_user`）
- Redis 位于 `localhost:6379`
- AI API 访问权限（OpenAI 或 Gemini）
- 视频合成服务 API
- Playwright + Chromium（用于动态字幕）

### Easegen-Admin 所需服务

- MySQL 8.0+ 位于 `localhost:3306`（数据库: `easegen`，用户: `easegen`）
- Redis 位于 `localhost:6379`

### Docker 快速启动

```bash
# 为 TextLoom 启动 PostgreSQL 和 Redis
docker-compose -f docker/postgres/docker-compose.yml up -d
docker-compose -f docker/redis/docker-compose.yml up -d

# 默认凭证（⚠️ 仅用于开发环境 - 生产环境必须修改）
# PostgreSQL: solocore_user / solocore_pass_2024
# Redis: solocore_redis_pass_2024
```

## 重要工作流

### 添加新的处理步骤 (TextLoom)

1. 在 `services/` 中扩展服务（如 `TaskProcessor`）
2. 在 `tasks/` 中创建 Celery 任务
3. 更新进度百分比范围
4. 在数据库模型中添加状态跟踪
5. 生成 Alembic 迁移: `alembic revision --autogenerate`
6. 实现错误处理和回滚逻辑
7. 在 `tests/integration/` 中添加测试

### 添加新实体 (Easegen-Admin)

1. 在 `dal/dataobject` 中创建 DO 类
2. 在 `dal/mysql` 中创建 Mapper 接口，继承 `BaseMapperX`
3. 在 `service` 中创建 Service 接口和实现
4. 在 `controller/*/vo` 中创建 ReqVO/RespVO
5. 创建包含 CRUD 操作的 Controller
6. 在 `ErrorCodeConstants` 中添加错误码
7. 在 system 模块中添加菜单和权限

### 创建新的 API 路由 (TextLoom)

1. 在 `routers/` 中使用 FastAPI 装饰器定义路由
2. 实现异步处理函数
3. 使用 Pydantic 模型进行请求/响应验证
4. 使用 `get_db_session()` 处理数据库会话
5. 返回结构化响应
6. 添加集成测试
7. 更新 API 文档字符串

## 测试

### TextLoom 测试

```bash
# 单元/集成测试
uv run pytest tests/ -v

# 业务端到端测试
uv run python business_e2e_test.py

# 真实 AI 集成测试（通过环境变量控制）
export RUN_LIVE_AI_TESTS=1
uv run pytest tests/integration/test_internal_endpoints_live.py -q
```

### Easegen-Admin 测试

```bash
# 运行所有测试
mvn test

# 运行特定模块的测试
cd yudao-module-digitalcourse/yudao-module-digitalcourse-biz
mvn test

# 运行单个测试类
mvn test -Dtest=YourTestClass
```

### Easegen-Front 测试

测试目前较少。运行类型检查:
```bash
pnpm ts:check
```

## 监控与运维

### TextLoom 监控

- API 健康检查: `GET /health`（包含数据库状态和 Celery 状态）
- Celery Flower 仪表板: `http://localhost:5555`
- 任务状态轮询: `GET /tasks/{task_id}/status`
- 日志: `logs/app.log`、`logs/textloom.log`、`logs/textloom_error.log`

### Celery 队列管理

```bash
# 清空队列（先停止 worker）
celery -A celery_config purge -Q video_processing,video_generation,maintenance,default -f

# 清理过期结果
celery -A celery_config call celery.backend_cleanup
```

### Easegen-Admin 监控

- Swagger UI: `http://localhost:48080/swagger-ui`
- Druid SQL 监控: `http://localhost:48080/druid/`
- API 端点: `/admin-api/**` 和 `/app-api/**`

## 文档

### TextLoom 文档

完整文档位于 `textloom/docs/`:
- **架构**: 系统设计和技术架构
- **安全**: 安全审计、JWT 认证、CORS 配置
- **性能**: 数据库优化、连接池调优
- **部署**: CI/CD 流水线和部署指南
- **备份**: 备份策略和灾难恢复

导航索引: `textloom/docs/README.md`

### Easegen 文档

- 部署指南: https://ozij45g3ts.feishu.cn/docx/EgS3dm1HtoKOPkxReEQcxaWanQb
- 各子模块中的独立 CLAUDE.md 文件

### Editly 文档

- Windows 配置: `docs/EDITLY_WINDOWS_SETUP.md`
- 快速开始: `textloom/EDITLY_QUICKSTART.md`
- 官方文档: `editly/README.md`

## 许可证与贡献

### 双重许可模式

- **社区许可证（免费）**: 个人用户用于个人使用、学习、研究
- **商业许可证（付费）**: 团队部署、代码修改、再分发、嵌入产品时必须购买

### 贡献指南

1. 阅读 `CONTRIBUTING.md` 了解详细的贡献指南
2. 提交贡献即表示授予社区许可证和商业许可证下的永久许可
3. 使用功能分支: `git checkout -b feature/your-feature-name`
4. 提交格式: `feat: add your feature description` 或 `fix: description`
5. 提交包含详细描述的 Pull Request

## 重要提醒

- 做被要求的事，不多不少
- 严禁创建文件，除非对实现目标绝对必要
- 始终优先编辑现有文件而非创建新文件
- 严禁主动创建文档文件（*.md）或 README 文件
- 严禁未经用户明确确认修改 .env 文件
- 严禁创建多个配置模板文件
- 始终使用 .env.example 作为配置模板的单一事实来源
- 任何配置更改必须先获得用户批准
