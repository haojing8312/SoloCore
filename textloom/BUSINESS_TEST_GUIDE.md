# TextLoom 完整业务测试指南

本指南介绍如何运行 TextLoom 的完整业务端到端测试（使用 `business_e2e_test.py`）。

## 📋 前置准备检查清单

### 1. 依赖安装

```bash
cd E:/code/yzpd/SoloCore/textloom

# 使用 uv 安装依赖（推荐）
uv sync

# 安装 Playwright 浏览器（如需动态字幕功能）
playwright install chromium
```

**等待安装完成**（约 3-5 分钟，取决于网络速度）。

### 2. 环境配置检查

确保 `.env` 文件已正确配置：

```bash
# 必需配置项
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# AI 模型配置（必需）
USE_GEMINI=true
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL_NAME=gemini-2.5-pro

# Editly 配置
EDITLY_EXECUTABLE_PATH=  # 留空自动查找
EDITLY_FAST_MODE=true
```

### 3. 准备测试素材

创建一个测试目录并放入测试素材：

```bash
# 创建测试目录
mkdir test_materials

# 放入测试文件（图片或视频）
# 例如：test_materials/image1.jpg, test_materials/video1.mp4
```

**测试素材要求：**
- 最多 50 个文件
- 支持格式：JPG, PNG, MP4, MOV等
- 建议准备 3-5 个素材文件即可

---

## 🚀 启动服务

### 方法 1：一键启动（Linux/Mac）

```bash
# 启动所有服务（FastAPI + Celery Worker + Flower + Beat）
./start_all_services.sh

# 查看服务状态
curl http://localhost:48095/health
```

### 方法 2：Windows 手动启动

#### 步骤 1: 启动 FastAPI

```bash
# 新开一个终端窗口
cd E:/code/yzpd/SoloCore/textloom
uv run uvicorn main:app --host 0.0.0.0 --port 48095
```

**等待看到：**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:48095
```

#### 步骤 2: 启动 Celery Worker

```bash
# 新开另一个终端窗口
cd E:/code/yzpd/SoloCore/textloom
uv run celery -A celery_config worker --loglevel=info --pool=solo
```

**等待看到：**
```
[tasks]
  . tasks.video_merge_polling.poll_video_merge_results
  . tasks.video_processor.process_text_to_video_task

celery@HOSTNAME ready.
```

#### 步骤 3: 启动 Celery Beat（可选，用于定时任务）

```bash
# 新开第三个终端窗口
cd E:/code/yzpd/SoloCore/textloom
uv run celery -A celery_config beat --loglevel=info
```

#### 步骤 4: 启动 Flower 监控（可选）

```bash
# 新开第四个终端窗口
cd E:/code/yzpd/SoloCore/textloom
uv run celery -A celery_config flower
```

访问：http://localhost:5555

---

## 🧪 运行业务端到端测试

### 基本测试（默认风格）

```bash
cd E:/code/yzpd/SoloCore/textloom

# 使用测试素材目录运行测试
uv run python business_e2e_test.py --local-dir ./test_materials
```

### 测试参数说明

```bash
uv run python business_e2e_test.py \
  --local-dir ./test_materials \              # 必需：素材目录
  --script-style default \                    # 可选：脚本风格（default/product_geek）
  --base-url http://localhost:48095 \        # 可选：API 地址
  --test-styles-comparison \                  # 可选：启用风格对比测试
  --desc-json ./descriptions.json             # 可选：素材描述文件
```

### 素材描述文件示例（descriptions.json）

```json
{
  "image1.jpg": "产品宣传图，展示新款智能手表",
  "video1.mp4": "产品演示视频，展示手表功能"
}
```

或数组格式：
```json
[
  {
    "filename": "image1.jpg",
    "description": "产品宣传图，展示新款智能手表"
  },
  {
    "filename": "video1.mp4",
    "description": "产品演示视频，展示手表功能"
  }
]
```

---

## 📊 测试流程说明

业务端到端测试会自动执行以下步骤：

### 步骤 0: API 健康检查
- 检查 API 服务是否正常运行
- 验证数据库和 Celery 连接

### 步骤 1: 用户注册/登录（如果需要）
- 使用 API Key 认证（demo_client）
- 验证身份认证功能

### 步骤 2: 人设管理
- 创建测试人设（"科技博主小A"）
- 验证人设 CRUD 操作

### 步骤 3: 素材上传
- 批量上传测试目录中的文件
- 最多 50 个文件
- 验证文件上传功能

### 步骤 4: 任务创建
- 使用上传的素材创建视频生成任务
- 指定脚本风格
- 提交任务到 Celery 队列

### 步骤 5: 任务监控
- 轮询任务状态（pending → processing → completed）
- 监控各个阶段进度：
  - 0-25%: 素材处理
  - 25-50%: 素材分析
  - 50-75%: 脚本生成
  - 75-100%: 视频生成

### 步骤 6: 结果验证
- 检查视频生成结果
- 下载生成的视频文件
- 验证视频质量

---

## 📈 预期测试输出

### 成功运行示例

```
============================================================
步骤 0: API健康检查
============================================================
✅ API根端点: API服务正常运行
✅ 健康检查: API健康状态良好

============================================================
步骤 4: 人设管理测试
============================================================
✅ 创建人设: 人设创建成功，ID: 123
✅ 获取人设列表: 成功获取 1 个人设
✅ 更新人设: 人设更新成功

============================================================
步骤 5: 素材上传测试
============================================================
✅ 上传素材 1/3: image1.jpg (成功)
✅ 上传素材 2/3: image2.jpg (成功)
✅ 上传素材 3/3: video1.mp4 (成功)
✅ 素材上传完成: 成功 3 个，失败 0 个

============================================================
步骤 6: 任务创建与监控
============================================================
✅ 创建任务: 任务创建成功，ID: task_abc123
   任务状态: pending
   预计处理时间: 1-3 分钟

⏳ 轮询任务状态...
  [00:15] 状态: processing | 进度: 10% | 阶段: 素材处理中
  [00:30] 状态: processing | 进度: 35% | 阶段: 素材分析中
  [00:45] 状态: processing | 进度: 60% | 阶段: 脚本生成中
  [01:15] 状态: processing | 进度: 85% | 阶段: 视频生成中
  [01:45] 状态: completed | 进度: 100% | 完成！

✅ 任务完成:
   视频 URL: http://localhost:48095/workspace/processed/task_abc123_video_1.mp4
   时长: 15.3 秒
   缩略图: http://localhost:48095/workspace/processed/task_abc123_thumb.jpg

============================================================
测试报告
============================================================
测试用例: 6
成功: 6
失败: 0
成功率: 100%

总耗时: 2分15秒

🎉 所有测试通过！
```

---

## 🛠️ 故障排查

### 问题 1: 服务启动失败

**症状：**
```
ModuleNotFoundError: No module named 'celery'
```

**解决方案：**
```bash
# 重新安装依赖
uv sync

# 确保使用 uv run 运行命令
uv run python business_e2e_test.py --local-dir ./test_materials
```

### 问题 2: API 健康检查失败

**症状：**
```
❌ API健康检查: 连接拒绝
```

**解决方案：**
```bash
# 检查 FastAPI 服务是否运行
curl http://localhost:48095/health

# 查看 FastAPI 日志
cat logs/api.log

# 重启服务
./stop_all.sh
./start_all_services.sh
```

### 问题 3: Celery Worker 未运行

**症状：**
```
任务一直停留在 pending 状态
```

**解决方案：**
```bash
# 检查 Celery Worker 状态
uv run celery -A celery_config inspect active

# 查看 Worker 日志
cat logs/celery_worker.log

# 手动启动 Worker
uv run celery -A celery_config worker --loglevel=info --pool=solo
```

### 问题 4: 数据库连接失败

**症状：**
```
❌ 健康检查: database connection failed
```

**解决方案：**
```bash
# 检查 .env 配置
cat .env | grep DATABASE_URL

# 测试数据库连接
uv run python -c "from config import settings; print(settings.database_url)"

# 检查远程数据库是否可访问
ping your-db-host
```

### 问题 5: Redis 连接失败

**症状：**
```
celery.exceptions.CeleryError: Cannot connect to redis://...
```

**解决方案：**
```bash
# 检查 Redis 配置
cat .env | grep REDIS

# 测试 Redis 连接（如果有 redis-cli）
redis-cli -h your-redis-host -p 6379 ping
```

### 问题 6: AI 模型配置错误

**症状：**
```
❌ 脚本生成失败: API key invalid
```

**解决方案：**
```bash
# 检查 AI 配置
cat .env | grep GEMINI_API_KEY
cat .env | grep USE_GEMINI

# 测试 API Key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models
```

### 问题 7: 视频生成失败

**症状：**
```
❌ 视频生成: Editly 执行失败
```

**解决方案：**
```bash
# 检查 Editly 是否可用
cd ../editly
npm run build

# 检查 FFmpeg
ffmpeg -version

# 查看详细日志
cat logs/sync_video_generator.log
```

---

## 📁 重要文件和日志位置

### 日志文件
```
logs/api.log                    # FastAPI 服务日志
logs/celery_worker.log          # Celery Worker 日志
logs/celery_flower.log          # Flower 监控日志
logs/celery_beat.log            # Beat 调度器日志
logs/sync_video_generator.log   # 视频生成日志
```

### 输出文件
```
workspace/materials/            # 上传的素材文件
workspace/processed/            # 生成的视频文件
workspace/keyframes/            # 视频关键帧
workspace/logs/                 # 处理日志
```

### 配置文件
```
.env                           # 环境配置
.env.example                   # 配置模板
config.py                      # 配置管理
```

---

## 🔗 相关资源

- **API 文档**: http://localhost:48095/docs
- **Flower 监控**: http://localhost:5555
- **健康检查**: http://localhost:48095/health
- **Editly 文档**: https://github.com/mifi/editly
- **项目文档**: ./docs/

---

## ✅ 快速测试检查清单

完成以下步骤确保测试顺利进行：

- [ ] ✅ 依赖已安装（`uv sync` 完成）
- [ ] ✅ `.env` 文件已配置
- [ ] ✅ 测试素材目录已准备（`test_materials/`）
- [ ] ✅ PostgreSQL 远程服务可访问
- [ ] ✅ Redis 远程服务可访问
- [ ] ✅ AI API Key 已配置且有效
- [ ] ✅ Editly 引擎可用（`node editly/dist/cli.js`）
- [ ] ✅ FastAPI 服务已启动（端口 48095）
- [ ] ✅ Celery Worker 已启动
- [ ] ✅ API 健康检查通过（`/health` 返回 200）

完成上述检查后，运行：

```bash
uv run python business_e2e_test.py --local-dir ./test_materials
```

---

**最后更新**: 2025-11-17
**维护者**: Claude
**版本**: 1.0.0 - Editly 纯架构
