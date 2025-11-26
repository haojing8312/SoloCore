# CLAUDE.md

此文件为 Claude Code 在本仓库中工作时提供指导。

## 语言使用规范

**重要：** 所有工作必须遵循以下语言规则：

- ✅ **英文**：代码、命令、路径、技术术语、Git 提交信息、API 端点
- ✅ **中文**：AI 对话回复、文档说明、代码注释、问题讨论、用户界面文本

**示例：**
```python
# ✅ 正确
async def get_task_status(task_id: str) -> TaskStatus:
    """获取任务状态"""
    return await db.query(TaskTable).filter_by(id=task_id).first()
```

## 项目概述

**SoloCore** 是一个 monorepo，包含多个 AI 驱动的内容创作工具：
- **textloom/** - 文本转视频系统 (Python/FastAPI)
- **easegen-admin/** - 数字人平台后端 (Java/Spring Boot)
- **easegen-front/** - 数字人平台前端 (Vue 3/TypeScript)
- **editly/** - 视频编辑库 (Node.js)
- **frontend/** - 统一 Web 界面（规划中）

## 常用命令

### TextLoom (Python/FastAPI)
```bash
cd textloom
uv sync                              # 安装依赖
playwright install chromium          # 安装浏览器（动态字幕）
./start_all_services.sh             # 启动所有服务
./stop_all.sh                       # 停止所有服务
uv run alembic upgrade head         # 数据库迁移
uv run pytest tests/ -v             # 运行测试
```

### Easegen-Admin (Java/Spring Boot)
```bash
cd easegen-admin
mvn clean install -DskipTests      # 构建
cd yudao-server && mvn spring-boot:run  # 运行（端口 48080）
```

### Easegen-Front (Vue 3/Vite)
```bash
cd easegen-front
pnpm install                        # 安装依赖
pnpm dev                           # 开发模式
pnpm build:prod                    # 生产构建
```

### Docker 服务
```bash
docker-compose -f docker/postgres/docker-compose.yml up -d  # PostgreSQL
docker-compose -f docker/redis/docker-compose.yml up -d     # Redis
```

## 关键开发规则

### ⚠️ 配置管理（严格执行）
- **严禁未经用户确认修改 `.env` 文件**
- 只使用 `.env.example` 作为模板（单一事实来源）
- 严禁创建多个模板文件（如 `.env.template`）

### 数据库操作 (TextLoom)
- **必须使用 `get_db_session()` 上下文管理器**
- `models/db_models.py` 是 ORM 模型的单一事实来源
- 模型修改后必须运行 `alembic revision --autogenerate`
- 所有表使用 `textloom_core` schema
- **严禁跳过迁移** - 必须提交迁移文件到 Git

### Async-First (TextLoom)
- 所有 I/O 操作必须使用 `async`/`await`
- 数据库操作使用异步会话管理器
- HTTP 客户端使用 `httpx`（不是 `requests`）
- 同步库（如 Playwright）需线程隔离

### 代码风格
- TextLoom: `black`, `isort`, `mypy`, `flake8`
- Easegen-Admin: Checkstyle, SpotBugs
- Easegen-Front: ESLint, Prettier, Stylelint
- **优先编辑现有文件，避免创建新文件**

### 模块通信 (Easegen-Admin)
- 严禁直接引用其他模块的 Service 实现
- 使用 `-api` 模块的接口/DTO 进行跨模块调用

## 架构要点

### TextLoom 架构
- **技术栈**: FastAPI (async), Celery + Redis, PostgreSQL (asyncpg), PyCaps + Playwright
- **处理流水线**: 素材处理 → 素材分析 → 脚本生成 → 视频生成（四阶段）
- **任务状态**: `pending` → `processing` → `completed`/`failed`/`cancelled`
- **关键组件**:
  - `main.py` - FastAPI 入口
  - `celery_config.py` - Celery 配置
  - `models/db_models.py` - ORM 模型（单一事实来源）
  - `services/` - 业务逻辑
  - `tasks/` - Celery 任务

### Easegen 架构
- **Admin (后端)**: Maven 多模块，Spring Boot 3.x，MyBatis-Plus，MySQL
- **Front (前端)**: Vue 3 Composition API，Element Plus，Pinia 状态管理
- **核心模块**: `yudao-module-digitalcourse`（数字课程），`yudao-module-ai`（AI 集成）

## 测试

### TextLoom
```bash
uv run pytest tests/ -v                                     # 单元/集成测试
uv run python business_e2e_test.py                         # 端到端测试
RUN_LIVE_AI_TESTS=1 uv run pytest tests/integration/ -q   # AI 集成测试（受控）
```

### Easegen
```bash
mvn test                                                    # 所有测试
mvn test -Dtest=YourTestClass                              # 单个测试类
pnpm ts:check                                              # 前端类型检查
```

## 监控与运维

### TextLoom
- 健康检查: `GET /health`
- Celery Flower: `http://localhost:5555`
- 任务状态: `GET /tasks/{task_id}/status`
- 日志: `logs/textloom.log`, `logs/textloom_error.log`

### Easegen-Admin
- Swagger UI: `http://localhost:48080/swagger-ui`
- Druid 监控: `http://localhost:48080/druid/`

## 重要提醒

### 工作原则
- 做被要求的事，不多不少
- 严禁创建文件，除非绝对必要
- 优先编辑现有文件
- 严禁主动创建文档文件（*.md）

### 配置安全
- 严禁未经确认修改 `.env`
- 使用 `.env.example` 作为唯一模板
- 配置更改需用户批准

### 语言使用
- **AI 对话必须使用中文**
- 代码、命令、路径保持英文
- 代码注释和文档字符串使用中文

---

**详细文档**:
- 完整架构文档: `textloom/docs/`
- 贡献指南: `CONTRIBUTING.md`
- 许可证信息: `LICENSE`
- 项目说明: `README.md`
