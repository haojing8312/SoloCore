# TextLoom Editly 引擎测试指南

本指南提供 TextLoom + Editly 架构的完整测试流程。

## 📋 目录

1. [环境检查](#环境检查)
2. [独立 Editly 测试](#独立-editly-测试)
3. [完整 API 测试](#完整-api-测试)
4. [查看生成视频](#查看生成视频)
5. [故障排查](#故障排查)

---

## 🔍 环境检查

### 运行环境检查脚本

```bash
cd textloom
python test_environment.py
```

**应该看到：**
```
✅ Python 版本: 3.9.x
✅ 数据库配置: 已配置
✅ Redis 配置: localhost:6379
✅ Editly 引擎: node /path/to/editly/dist/cli.js
✅ AI 模型配置: Gemini (gemini-2.5-pro)
✅ 工作空间: 3/3 子目录

检查结果: 6/6 通过 (100%)
```

### 手动检查清单

- [ ] Python 3.9+
- [ ] PostgreSQL 数据库运行中
- [ ] Redis 服务运行中
- [ ] Editly 已安装（Node.js + FFmpeg）
- [ ] AI API Key 已配置（Gemini 或 OpenAI）
- [ ] 工作空间目录已创建

---

## 🎬 独立 Editly 测试

测试 Editly 引擎的核心功能，**无需启动完整服务**。

### 运行独立测试

```bash
cd textloom
python test_editly_video_generation.py
```

### 测试内容

1. **数据准备**: 创建测试图片和脚本数据
2. **数据转换**: TextLoom Scene → Editly Clip 映射
3. **视频生成**: 调用 Editly 生成 8 秒测试视频
4. **文件验证**: 检查输出文件是否存在

### 预期输出

```
✅ 环境检查: 通过
✅ 数据转换: 通过
✅ Editly 视频生成: 通过
✅ 配置验证: 通过

📁 输出文件位置:
   - 视频: ./workspace/processed/test_editly_output.mp4
   - 配置: ./workspace/processed/test_editly_config.json5
```

### 查看生成的视频

**Windows:**
```bash
start workspace/processed/test_editly_output.mp4
```

**Linux/Mac:**
```bash
open workspace/processed/test_editly_output.mp4  # Mac
xdg-open workspace/processed/test_editly_output.mp4  # Linux
```

---

## 🚀 完整 API 测试

测试完整的 TextLoom API 服务（需要数据库和 Celery）。

### 第一步：启动服务

```bash
# 启动 Docker 服务（PostgreSQL + Redis）
cd docker/compose
docker-compose up -d

# 返回项目根目录
cd ../..

# 启动所有服务（FastAPI + Celery）
./start_all_services.sh
```

**验证服务状态：**
```bash
curl http://localhost:48095/health
```

应该返回：
```json
{
  "status": "healthy",
  "database": "connected",
  "celery": "connected"
}
```

### 第二步：运行业务端到端测试

```bash
python business_e2e_test.py
```

### 第三步：API 手动测试

#### 1. 创建视频生成任务

```bash
curl -X POST http://localhost:48095/tasks/video \
  -H "Content-Type: application/json" \
  -d '{
    "script_data": {
      "title": "API 测试视频",
      "scenes": [
        {
          "scene_id": 1,
          "narration": "这是通过 API 生成的测试视频",
          "duration": 5,
          "textDriver": {"textJson": "API 测试场景"}
        }
      ]
    },
    "media_files": [],
    "mode": "multi_scene"
  }'
```

**响应示例：**
```json
{
  "task_id": "abc123",
  "status": "pending",
  "message": "任务已创建"
}
```

#### 2. 查询任务状态

```bash
curl http://localhost:48095/tasks/abc123/status
```

**响应示例：**
```json
{
  "task_id": "abc123",
  "status": "processing",
  "progress": 75,
  "current_stage": "视频生成中",
  "video_url": null
}
```

#### 3. 等待完成并获取视频

任务完成后：
```json
{
  "task_id": "abc123",
  "status": "completed",
  "progress": 100,
  "video_url": "http://localhost:48095/workspace/processed/abc123_video_1_output.mp4"
}
```

### 第四步：停止服务

```bash
./stop_all.sh
```

---

## 🎥 查看生成视频

### 方法 1: 直接打开文件

```bash
# Windows
start workspace/processed/test_editly_output.mp4

# Mac
open workspace/processed/test_editly_output.mp4

# Linux
xdg-open workspace/processed/test_editly_output.mp4
```

### 方法 2: 通过 HTTP 访问

如果服务正在运行：
```
http://localhost:48095/workspace/processed/test_editly_output.mp4
```

### 方法 3: 使用 ffprobe 查看视频信息

```bash
ffprobe -v error -show_format -show_streams workspace/processed/test_editly_output.mp4
```

### 方法 4: 生成缩略图

```bash
ffmpeg -i workspace/processed/test_editly_output.mp4 -vf "select=eq(n\,0)" -vframes 1 thumbnail.jpg
```

---

## 🛠️ 故障排查

### 问题 1: Editly 未找到

**错误信息：**
```
❌ Editly 引擎: 未找到
```

**解决方案：**
```bash
cd ../editly
npm install
npm run build

# 或设置环境变量
export EDITLY_EXECUTABLE_PATH=/path/to/editly/dist/cli.js
```

### 问题 2: 数据库连接失败

**错误信息：**
```
❌ 数据库配置: 连接失败
```

**解决方案：**
```bash
# 检查 Docker 服务
docker ps | grep postgres

# 启动数据库
cd docker/compose
docker-compose up -d postgres

# 检查 .env 配置
cat .env | grep DATABASE_URL
```

### 问题 3: Redis 连接失败

**错误信息：**
```
❌ Redis 配置: 连接超时
```

**解决方案：**
```bash
# 启动 Redis
cd docker/compose
docker-compose up -d redis

# 测试连接
redis-cli -h localhost -p 6379 ping
```

### 问题 4: AI 模型配置错误

**错误信息：**
```
❌ AI 模型配置: 未配置
```

**解决方案：**
```bash
# 编辑 .env 文件
vim .env

# 添加或修改：
USE_GEMINI=true
GEMINI_API_KEY=your-api-key
GEMINI_MODEL_NAME=gemini-2.5-pro
```

### 问题 5: 视频文件大小异常小

**症状：** 生成的视频只有几 KB

**可能原因：**
- 场景时长过短
- 缺少素材文件
- 转场效果配置错误

**解决方案：**
```python
# 增加场景时长
"duration": 5  # 至少 3-5 秒

# 添加更多素材
media_files = [
    {"id": "mat1", "file_url": "./path/to/image.jpg"}
]
```

### 问题 6: Celery Worker 未启动

**错误信息：**
```
Task stuck in 'pending' status
```

**解决方案：**
```bash
# 检查 Celery Worker 状态
celery -A celery_config inspect active

# 重启 Worker
./stop_all.sh
./start_all_services.sh
```

---

## 📊 性能基准

### 典型视频生成时间

| 场景数 | 总时长 | 素材数 | 生成时间 |
|--------|--------|--------|----------|
| 1      | 3s     | 0      | ~5s      |
| 3      | 8s     | 1      | ~15s     |
| 5      | 15s    | 3      | ~30s     |
| 10     | 30s    | 5      | ~60s     |

**影响因素：**
- CPU 性能
- 素材文件大小
- 转场效果复杂度
- 字幕渲染数量

---

## 🔗 相关文档

- [Editly 官方文档](https://github.com/mifi/editly)
- [TextLoom 架构设计](./docs/architecture/)
- [API 文档](./docs/API_DOCUMENTATION.md)
- [配置管理](./docs/deployment/CONFIG_FILE_MANAGEMENT.md)

---

## ✅ 测试检查清单

完成以下检查以确保系统正常运行：

- [ ] 环境检查 100% 通过
- [ ] 独立 Editly 测试成功生成视频
- [ ] 视频文件可正常播放
- [ ] API 服务可正常启动
- [ ] 健康检查端点返回正常
- [ ] Celery Worker 正常处理任务
- [ ] 数据库连接稳定
- [ ] Redis 缓存工作正常

---

**最后更新**: 2025-11-17
**维护者**: Claude
**版本**: 1.0.0 - Editly 纯架构
