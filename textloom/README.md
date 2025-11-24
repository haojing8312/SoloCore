# TextLoom - 智能文本转视频系统

## 项目简介

TextLoom 是一个基于 FastAPI 的智能文本转视频系统，支持将 Markdown 文档自动转换为精美的视频内容。系统采用现代化的微服务架构，集成了 AI 技术，提供从文本分析到视频生成的完整解决方案。

## 🚀 核心功能

### 完整的处理流程
1. **素材处理** - 自动提取并下载文档中的媒体文件
2. **素材分析** - 使用 AI 技术分析媒体内容特征
3. **脚本生成** - 基于内容生成适合视频表达的脚本
4. **视频生成** - 智能合成最终的视频作品

### 系统特性
- ✅ **异步处理** - 后台任务处理，实时进度跟踪
- ✅ **智能分析** - AI 驱动的内容理解和脚本生成
- ✅ **多媒体支持** - 支持图片、视频、音频素材
- ✅ **个性化设置** - 支持人设配置和智能脚本生成
- ✅ **实时监控** - 完整的任务状态管理和进度追踪
- ✅ **动态字幕** - 基于PyCaps引擎的专业动态字幕生成

## 📋 系统要求

- Python 3.8+
- FastAPI
- SQLite/PostgreSQL
- 大模型 API 访问权限
- 视频生成服务 API
- Playwright (用于动态字幕渲染)
- Chromium 浏览器 (由Playwright自动管理)

## 🛠️ 快速开始

### 🐳 Docker 部署 (推荐)

使用 Docker 进行一键部署，详细配置请参考 [`docker/README.md`](docker/README.md)。

```bash
# 快速启动主要服务
docker-compose -f docker/compose/docker-compose.yml up -d

```

### 1. 环境配置

```bash
# 复制环境配置模板（首次使用）
cp .env.example .env

# 编辑 .env 文件，填入真实的配置值（重点项）：
# - secret_key：JWT密钥（生产环境请使用强密码）
# - database_url：数据库连接串（postgresql+asyncpg://user:pass@host:port/db）
# - use_gemini=true 且 gemini_api_key（使用 Gemini 时必填）
# - openai_api_key / openai_api_base（若走 OpenAI 兼容接口）
# - image_analysis_*：图片分析专用配置
# - video_merge_api_url / video_merge_api_key / video_merge_account_id
# - redis_host / redis_port / redis_db / redis_password
# - allowed_origins：CORS可信域清单（JSON数组，如 ["http://localhost:3000"]）
```

### 2. 安装依赖

```bash
# 推荐使用 uv 包管理器
uv sync

# 或者使用 pip
pip install -r requirements.txt

# 安装 Playwright 浏览器 (动态字幕功能必需)
playwright install chromium
```

### 3. 启动服务

```bash
# 开发模式
uv run uvicorn main:app --reload --host 0.0.0.0 --port 48095

# 启动 Celery（Worker/Flower/Beat）
./start_celery_worker.sh worker &
./start_celery_worker.sh flower &
./start_celery_worker.sh beat &

# 一键后台启动所有服务（API、Worker、Flower、Beat）
./start_all_services.sh

# 停止所有服务
./stop_all.sh
```

### 3.1 两段式视频合成与轮询

- 阶段4“视频生成”为两段式：提交后任务可能处于 processing，随后由定时轮询推进到终态。
- 轮询任务：`tasks.video_merge_polling.poll_video_merge_results`（Celery Beat 每60秒执行一次）。
- 行为：
  - 查询 `textloom_core.sub_video_tasks` 中 `status=processing` 的子任务
  - 调用视频合成接口的查询端点获取状态
  - 更新 `sub_video_tasks`：成功写入 `video_url/thumbnail_url/duration/status=completed`；失败写入 `error_message/status=failed`
  - 当同一 `parent_task_id` 的子任务全部终态，汇总到 `tasks.multi_video_results`，并将主任务置为 completed（若至少一个成功）或 failed（全部失败）
- 超时：超过 `settings.multi_video_generation_timeout`（默认30分钟）仍未完成将标记为超时失败，并参与父任务收敛。

### 4. 运行端到端业务测试

```bash
# 运行完整的端到端业务测试
uv run python business_e2e_test.py --script-style default --local-dir test/081901DeepSeep更新版本v31有效果提升吗附实测对比 --desc-json test/081701macaron-终于有关注大家生活的AI产品了/终于有关注大家生活的AI产品了.json
```

### 5. 内部评估接口与集成测试（脚本/视频/素材）

仅用于 dev/staging，默认通过 `INTERNAL_TEST_TOKEN` 进行保护，不建议在生产开启。

1) 启用方式（两种任选其一）：
- 设置环境变量（全局一次）：
```bash
export INTERNAL_TEST_TOKEN=test-token
```
- 或在集成测试脚本内自动设置（`tests/integration/test_internal_endpoints_live.py` 已内置）。

2) 接口说明：
- 图片上下文分析（AI）
  - `POST /internal/analyzer/analyze-image`
  - Header: `x-test-token: <INTERNAL_TEST_TOKEN>`
  - Body 示例：
    ```json
    {"image_url":"https://example.com/a.jpg","context_before":"前文","context_after":"后文","surrounding_paragraph":"所在段落","resolution":"800x600"}
    ```
- 素材提取/下载
  - `POST /internal/materials/extract-media`
  - `POST /internal/materials/download-and-organize`
  - Header: `x-test-token: <INTERNAL_TEST_TOKEN>`
- 脚本生成（多风格）
  - `POST /internal/script/generate`
  - Header: `x-test-token`
  - Body 关键字段：`topic`, `source_content`, `material_context`, `styles`（如 ["professional","viral","balanced"]）
- 视频生成
  - `POST /internal/video/generate-single`
  - `POST /internal/video/generate-multiple`
  - Header: `x-test-token`
  - 需提供 `script_data.scenes/narration` 与 `media_files[].file_url` 等字段

3) 真连网集成测试（可选）
- 受控开关运行：
```bash
export RUN_LIVE_AI_TESTS=1
uv run pytest tests/integration/test_internal_endpoints_live.py -q
```
- 需准备：OpenAI/Gemini/视频合成服务等相关环境变量；未设置则测试会失败或被跳过。

## 🎨 动态字幕功能 (PyCaps)

TextLoom 集成了 [PyCaps](https://github.com/francozanardi/pycaps) 开源动态字幕引擎，提供专业级的CSS动态字幕渲染能力。

### 功能特性
- ✅ **词级精准定位** - 自动将SRT字幕转换为词级时间戳
- ✅ **丰富模板支持** - 内置 hype、minimalist、explosive、vibrant 等多种风格模板
- ✅ **CSS样式定制** - 基于CSS的专业字幕样式系统
- ✅ **高质量渲染** - 使用Playwright + Chromium进行精确渲染
- ✅ **完全异步处理** - 无阻塞的后台字幕生成

### API 端点

#### 1. 获取可用模板
```bash
curl -X GET "http://localhost:48095/dynamic-subtitles/templates"
```

#### 2. 获取PyCaps配置状态
```bash  
curl -X GET "http://localhost:48095/dynamic-subtitles/config"
```

#### 3. 处理动态字幕
```bash
curl -X POST "http://localhost:48095/dynamic-subtitles/process" \
  -H "Content-Type: application/json" \
  -H "x-test-token: test-token" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "subtitles_url": "https://example.com/subtitles.srt", 
    "template": "hype"
  }'
```

#### 4. 检查PyCaps状态 (开发调试)
```bash
curl -X GET "http://localhost:48095/dynamic-subtitles/test/pycaps-status" \
  -H "x-test-token: test-token"
```

### 内置模板

| 模板名称 | 风格描述 | 适用场景 |
|---------|---------|---------|
| `hype` | 动感炫酷风格 | 娱乐、游戏、体育类内容 |
| `minimalist` | 简约现代风格 | 商务、教育、纪录片 |
| `explosive` | 爆炸震撼风格 | 动作、惊悚、宣传片 |
| `vibrant` | 活泼多彩风格 | 儿童、音乐、创意内容 |

### 集成测试

运行动态字幕功能的完整测试：

```bash
# 启用真连网测试
export RUN_LIVE_AI_TESTS=1
export INTERNAL_TEST_TOKEN=test-token

# 运行PyCaps集成测试
uv run pytest tests/integration/test_dynamic_subtitles_live.py -v

# 测试特定模板
uv run pytest tests/integration/test_dynamic_subtitles_live.py::TestDynamicSubtitlesIntegration::test_process_pycaps_subtitles_hype_style -v
```

### 配置说明

动态字幕功能通过以下环境变量控制：

```env
# 动态字幕开关
dynamic_subtitle_enabled=true

# 工作目录
workspace_dir=/tmp/textloom_workspace

# 测试Token (仅开发/测试环境)
INTERNAL_TEST_TOKEN=test-token
```

## 🛠️ 运维

### 清理 Celery 队列（使用 celery -A）

前提：先停止所有 Celery worker，再执行清理命令。以下命令仅清空 Broker 中的待处理消息，不会清空结果后端记录。

```bash
# 清空指定队列（不显式指定 Broker，使用应用内配置）
celery -A celery_config \
  purge -Q video_processing,video_generation,maintenance,default -f

# 如需显式指定 Broker（推荐在运维环境用环境变量传入）
celery -A celery_config -b "$CELERY_BROKER_URL" \
  purge -Q video_processing,video_generation,maintenance,default -f

# 如果你的环境使用 uv 管理虚拟环境，也可以：
uv run celery -A celery_config -b "$CELERY_BROKER_URL" \
  purge -Q video_processing,video_generation,maintenance,default -f

# 可选：清理结果后端中过期结果（需要有 worker 运行才能执行）
celery -A celery_config -b "$CELERY_BROKER_URL" call celery.backend_cleanup
```

说明：
- `purge` 只会清空队列中的待处理任务；对正在执行或已完成任务无影响。
- `celery.backend_cleanup` 仅清理过期结果记录；如需“彻底”清理结果键，可使用 redis-cli 精确删除（谨慎操作）。

## 🔧 配置说明

### 大模型配置
系统支持 OpenAI/Gemini 与图片分析独立配置（从环境读取）。若使用 Gemini，请务必设置 `gemini_api_key`。

```env
# OpenAI（可选）
openai_api_key=
openai_api_base=
openai_model_name=Qwen/Qwen2.5-VL-72B-Instruct
script_model_name=deepseek-chat

# Google AI Studio - Gemini（推荐）
use_gemini=true
gemini_api_key=
# 可选：当通过 OpenAI SDK 访问 Gemini 的 OpenAI 兼容网关时设置
gemini_api_base=
gemini_model_name=gemini-2.5-pro
gemini_script_model_name=gemini-2.5-pro

# 图片分析（可独立配置）
image_analysis_use_gemini=false
image_analysis_model_name=Qwen/Qwen2.5-VL-72B-Instruct
image_analysis_api_base=
image_analysis_api_key=
```

### 视频生成配置
```env
video_merge_api_url=
video_merge_api_key=
video_merge_account_id=
video_merge_timeout=1800
multi_video_generation_timeout=1800  # 两段式轮询超时阈值（秒），默认30分钟
```

## 🗄️ 数据库迁移（Alembic）

本项目使用 SQLAlchemy ORM + Alembic 作为“单一事实来源”的数据库管理方案。

要点：
- 模型定义：`models/db_models.py`（所有表均在 `textloom_core` schema 下）
- 迁移入口：`alembic/`（请将 `alembic/versions/*.py` 提交到 Git；`alembic.ini` 不提交）
- 迁移环境：`alembic/env.py` 已自动从环境/配置解析 `DATABASE_URL`，并在迁移时将 `postgresql+asyncpg://` 转换为 `postgresql+psycopg2://`
- 仅迁移 `textloom_core`：通过 `include_object` 过滤，避免修改其他 schema 的对象

常用命令：
```bash
# 生成迁移（自动对比 models/db_models.py 与数据库）
uv run alembic revision --autogenerate -m "sync models to db"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移（示例）
uv run alembic downgrade -1
```

注意：
- 修改模型后务必生成并提交迁移文件，以保持“模型=数据库”的一致性。
- 本次重构新增了 `sub_video_tasks` 的字段以支持两段式：`sub_task_id`(唯一)、`progress`、`script_style`、`script_id`、`script_data`。


## 📚 文档导航

### 📖 完整文档结构
本项目采用分类文档管理，详见 [`docs/README.md`](docs/README.md) 完整导航。

主要文档目录：
- **[架构文档](docs/architecture/)** - 系统设计和技术架构
- **[安全文档](docs/security/)** - 安全审计报告和配置指南  
- **[性能文档](docs/performance/)** - 性能优化和数据库调优
- **[部署文档](docs/deployment/)** - CI/CD流水线和部署指南
- **[备份文档](docs/backup/)** - 数据备份和灾难恢复

### 🔗 API 文档

启动服务后，可以通过以下地址访问 API 文档：

- **Swagger UI**: http://localhost:48095/docs
- **ReDoc**: http://localhost:48095/redoc
- **Flower（本机）**: http://127.0.0.1:5555

### 核心 API 端点

#### 任务管理
- `POST /tasks/create-video-task` - 创建文本转视频任务
- `GET /tasks/` - 获取任务列表
- `GET /tasks/{task_id}` - 获取任务详情
- `GET /tasks/{task_id}/status` - 获取任务状态（用于轮询）
- `GET /tasks/{task_id}/media` - 获取任务媒体素材
- `POST /tasks/{task_id}/cancel` - 取消任务
- `POST /tasks/{task_id}/retry` - 重试任务
- `DELETE /tasks/{task_id}` - 删除任务

#### 动态字幕
- `GET /dynamic-subtitles/templates` - 获取PyCaps模板列表
- `GET /dynamic-subtitles/config` - 获取PyCaps配置状态
- `POST /dynamic-subtitles/process` - 处理动态字幕生成
- `GET /dynamic-subtitles/test/pycaps-status` - PyCaps状态检查 (需要test-token)

## 🎯 使用流程

### 1. 创建视频任务
```bash
curl -X POST "http://localhost:48095/tasks/create-video-task" \
  -F "file=@your_article.md" \
  -F "title=我的视频标题" \
  -F "description=视频描述"
```

### 2. 监控任务进度
```bash
# 获取任务状态
curl -X GET "http://localhost:48095/tasks/{task_id}/status"

# 获取任务详情
curl -X GET "http://localhost:48095/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🏗️ 系统架构

```
TextLoom/
├── main.py                 # FastAPI 应用入口
├── config.py              # 配置管理
├── models/                # 数据模型
│   ├── task.py           # 任务模型
│   ├── personas.py       # 人设模型
│   └── database.py       # 数据库操作
├── routers/              # API路由
│   ├── personas.py       # 人设路由
│   └── tasks.py         # 任务路由
├── services/            # 核心服务
│   ├── task_processor.py # 任务处理器
│   ├── script_generator.py # 脚本生成
│   └── video_generator.py # 视频生成
├── processors/          # 处理器模块
│   ├── material_processor.py # 素材处理
│   └── material_analyzer.py # 素材分析
└── integration_test.py  # 集成测试
```

## 📝 开发说明

### 后台任务处理
系统采用异步任务处理架构，任务按以下步骤自动执行：

1. **素材处理**（0-25%）：提取并下载文档中的媒体文件
2. **素材分析**（25-50%）：分析媒体内容特征
3. **脚本生成**（50-75%）：基于内容生成视频脚本
4. **视频生成**（75-100%）：合成最终视频

### 任务状态
- `pending` - 待处理
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败
- `cancelled` - 已取消

### 扩展开发
要扩展系统功能，可以：

1. 在 `services/` 目录添加新的服务模块
2. 在 `processors/` 目录添加新的处理器
3. 在 `routers/` 目录添加新的 API 路由
4. 更新 `models/` 中的数据模型

## 🔧 故障排除

### 常见问题

1. **API 密钥错误**
   - 检查 `.env` 文件中的 API 密钥配置
   - 确认密钥有效期

2. **数据库连接失败**
   - 检查数据库 URL 配置
   - 确认数据库服务正在运行

3. **任务处理失败**
   - 查看日志文件 `logs/app.log`
   - 检查网络连接
   - 验证第三方服务可用性

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/new-feature`)
3. 提交更改 (`git commit -am 'Add new feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系我们

如有问题或建议，请通过以下方式联系：

- 创建 GitHub Issue
- 发送邮件至：support@textloom.com
- 查看文档：https://docs.textloom.com

---

**TextLoom** - 让文本变成精彩视频！ 🎬✨ 