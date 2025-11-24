# 动态字幕系统架构文档

## 概览

TextLoom的动态字幕系统提供两个主要入口：API直接处理和Celery异步任务处理。系统支持TikTok/抖音风格的高级字幕效果，包括重点词高亮、打字机效果等。

## 系统架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   API 入口      │    │   Celery 入口    │    │   核心服务层       │
│ /process-       │    │ process_dynamic_ │    │ DynamicSubtitle    │
│ advanced        │──→ │ subtitles_task   │──→ │ Service            │
└─────────────────┘    └──────────────────┘    └────────────────────┘
         │                        │                         │
         ▼                        ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  文件下载        │    │  数据库更新      │    │  字幕渲染器        │
│  requests       │    │ sync_update_     │    │ SimpleDynamic      │
│                 │    │ sub_video_task   │    │ SubtitleService    │
└─────────────────┘    └──────────────────┘    └────────────────────┘
         │                        │                         │
         ▼                        ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  本地存储        │    │  PostgreSQL      │    │  FFmpeg 渲染       │
│  workspace/     │    │ sub_video_tasks  │    │  SimpleSubtitle    │
│                 │    │                  │    │  Renderer          │
└─────────────────┘    └──────────────────┘    └────────────────────┘
         │                        │                         │
         ▼                        ▼                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  云存储上传      │    │  状态跟踪        │    │  输出文件          │
│  MinIO/OBS/     │    │  progress: 85-100│    │  .mp4 视频         │
│  Local          │    │  status: completed│   │                    │
└─────────────────┘    └──────────────────┘    └────────────────────┘
```

## 入口1: API直接处理

### 入口方法
**位置**: `routers/dynamic_subtitles.py:92`
```python
@router.post("/process-advanced")
async def process_advanced_subtitles(
    request: ProcessAdvancedSubtitleRequest, 
    x_test_token: Optional[str] = Header(None)
)
```

### 调用链详解

#### 1.1 入参验证与文件下载
```python
# 验证内部测试token
verify_internal_token(x_test_token) -> bool

# 下载视频和字幕文件
requests.get(request.video_url, timeout=60) -> Response
requests.get(request.subtitles_url, timeout=30) -> Response
```

**输入参数**:
- `video_url`: 原视频URL
- `subtitles_url`: 字幕文件URL (.srt格式)
- `video_width`: 视频宽度 (默认1080)
- `video_height`: 视频高度 (默认1920)
- `style_config`: 高级样式配置
  - `enable_typewriter`: 打字机效果开关
  - `enable_highlight`: 重点词高亮开关
  - `enable_auto_wrap`: 自动换行开关
  - `position`: 字幕位置 ("top", "center", "bottom")
  - `style_type`: 样式类型 ("social", "modern", "neon")
  - `custom_highlight_words`: 自定义高亮词列表

#### 1.2 本地文件处理
```python
# 临时文件存储
tempfile.TemporaryDirectory() -> TemporaryDirectory
# 视频文件: temp_dir/input_video.mp4
# 字幕文件: temp_dir/subtitles.srt

# 输出文件路径
output_path = workspace/advanced_subtitle_output_{timestamp}.mp4
```

#### 1.3 字幕渲染服务调用
```python
# services/subtitle_renderer.py:1067
service = AdvancedDynamicSubtitleService()
result = service.process_video_subtitles_advanced(
    video_path=video_path,
    subtitle_path=subtitle_path,
    output_path=output_path,
    video_width=request.video_width,
    video_height=request.video_height,
    style_config=style_dict
)
```

**`AdvancedDynamicSubtitleService.process_video_subtitles_advanced()` 方法调用链**:
1. **字体信息获取**: `get_font_info()` -> Dict[str, Any]
2. **文件存在性检查**: `os.path.exists()` 验证输入文件
3. **TikTok渲染器创建**: `TikTokStyleSubtitleRenderer()`
4. **高级字幕创建**: `tiktok_renderer.create_advanced_subtitles()`
5. **多级渲染尝试**:
   - `_try_complex_filter()` - 复杂滤镜渲染
   - `_try_emergency_fallback()` - 紧急回退渲染

#### 1.4 输出结果
**成功响应**:
```json
{
  "success": true,
  "message": "高级动态字幕处理成功",
  "output_path": "/path/to/output.mp4",
  "effects_applied": {
    "typewriter": true,
    "highlight": true
  },
  "font_info": {
    "primary_font": "Noto Sans CJK SC",
    "fallback_fonts": ["Arial"]
  },
  "video_info": {
    "width": 1080,
    "height": 1920,
    "output_file": "advanced_subtitle_output_1693123456.mp4"
  }
}
```

## 入口2: Celery异步任务

### 入口方法
**位置**: `tasks/dynamic_subtitle_tasks.py:21`
```python
@celery_app.task(bind=True)
def process_dynamic_subtitles_task(
    self,
    sub_task_id: str,
    video_url: str,
    subtitles_url: Optional[str] = None,
    style_config: Optional[Dict[str, Any]] = None,
)
```

### 调用链详解

#### 2.1 数据库状态更新
```python
# models/celery_db.py:sync_update_sub_video_task
sync_update_sub_video_task(
    sub_task_id,
    {
        "status": "processing_subtitles",
        "progress": 85,  # 字幕处理阶段
    },
)
```

**数据库操作详情**:
- **表**: `textloom_core.sub_video_tasks`
- **字段更新**:
  - `status`: "processing_subtitles"
  - `progress`: 85 (表示视频生成完成，开始字幕处理)
  - `updated_at`: 当前时间戳
- **并发控制**: 使用 `with_for_update()` 行级锁
- **终态保护**: 已完成状态不允许回退

#### 2.2 动态字幕服务调用
```python
# services/dynamic_subtitle_service.py:27
subtitle_service = DynamicSubtitleService()
result = subtitle_service.process_video_subtitles(
    video_url=video_url,
    subtitles_url=subtitles_url,
    task_id=sub_task_id,
    style_config=style_config or {},
)
```

**`DynamicSubtitleService.process_video_subtitles()` 方法调用链**:

1. **配置检查**: `self.enabled` 检查动态字幕功能是否启用
2. **依赖检查**: `_check_pycaps_available()` 检查渲染器可用性
3. **文件下载**: 
   - `_download_file(video_url)` -> temp_dir/input_video.mp4
   - `_download_file(subtitles_url)` -> temp_dir/subtitles.srt
4. **字幕生成**: `_generate_dynamic_subtitles()`
5. **文件上传**: `_upload_processed_video()`

#### 2.3 简化字幕渲染服务
```python
# services/subtitle_renderer.py:1339
from .subtitle_renderer import SimpleDynamicSubtitleService
renderer_service = SimpleDynamicSubtitleService()
result = renderer_service.process_video_subtitles(
    video_path=str(video_path),
    subtitle_path=str(subtitle_path),
    output_path=str(output_path),
    style_config=style_config,
)
```

**`SimpleDynamicSubtitleService.process_video_subtitles()` 调用链**:
1. **字体信息记录**: `get_font_info()`
2. **文件存在性检查**: `os.path.exists()`
3. **样式配置处理**: 默认样式配置应用
4. **字幕渲染**: `self.renderer.render_subtitles()`

#### 2.4 SimpleSubtitleRenderer 渲染流程
```python
# services/subtitle_renderer.py:497
class SimpleSubtitleRenderer:
    def render_subtitles(
        self,
        video_path: str,
        subtitle_path: str, 
        output_path: str,
        style_config: Dict[str, Any]
    ) -> bool:
```

**渲染调用链**:
1. **视频信息获取**: `_get_video_info(video_path)` 
   - 获取分辨率、帧率等信息
   - 使用 `ffprobe` 命令解析
2. **SRT解析**: `self.srt_parser.parse_srt_file(subtitle_path)`
   - 解析时间轴和文本内容
   - 生成 `SubtitleSegment` 对象列表
3. **字幕滤镜创建**: `_create_subtitle_filter(segments, style_config)`
4. **FFmpeg渲染**: `_render_with_ffmpeg(video_path, output_path, subtitle_filter)`
   - **标准渲染**: `_try_standard_render()`
   - **紧急回退**: `_try_emergency_simple_render()`

#### 2.5 文件上传到云存储
```python
# utils/storage_utils.py:16
video_url = upload_file_to_storage(
    file_path=str(video_path), 
    filename=filename, 
    content_type="video/mp4"
)
```

**存储服务选择**:
- **MinIO**: `_upload_to_minio()` - 私有云存储
- **华为OBS**: `_upload_to_obs()` - 华为云对象存储  
- **本地存储**: `_upload_to_local()` - 本地文件系统

**上传成功后**:
- 返回公网访问URL
- 文件名格式: `dynamic_subtitle_{task_id}_{timestamp}.mp4`

#### 2.6 最终状态更新
```python
# 处理成功时
sync_update_sub_video_task(
    sub_task_id,
    {
        "status": "completed",
        "progress": 100,
        "video_url": result["video_url"],  # 新的视频URL
    },
)

# 处理失败时  
sync_update_sub_video_task(
    sub_task_id,
    {
        "status": "completed",  # 仍标记为完成，使用原视频
        "progress": 100,
        "error_message": f"动态字幕处理失败: {error_msg}",
    },
)
```

## 数据库交互详情

### 主要表结构

#### `textloom_core.sub_video_tasks` 表
```sql
CREATE TABLE textloom_core.sub_video_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sub_task_id VARCHAR(255) UNIQUE NOT NULL,  -- 业务唯一键
    parent_task_id UUID REFERENCES textloom_core.tasks(id),
    progress INTEGER DEFAULT 0,                -- 进度 (0-100)
    status VARCHAR(50) DEFAULT 'pending',      -- 状态
    video_url TEXT,                           -- 视频URL
    script_data JSON DEFAULT '{}',            -- 脚本数据
    error_message TEXT,                       -- 错误信息
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 关键数据库操作

#### 1. 状态更新操作
```python
# models/celery_db.py 中的 sync_update_sub_video_task
def sync_update_sub_video_task(sub_task_id: str, update_data: Dict[str, Any]) -> bool:
    # 1. 获取行级锁
    row = session.execute(
        select(SubVideoTaskTable.status, SubVideoTaskTable.progress)
        .where(SubVideoTaskTable.sub_task_id == sub_task_id)
        .with_for_update()  # 行级锁防止并发修改
    ).first()
    
    # 2. 终态保护逻辑
    if current_status == "completed" and target_status != "completed":
        return True  # 已完成状态不允许回退
        
    # 3. 进度单调性检查
    target_progress = update_data.get("progress", current_progress)
    if target_progress < current_progress:
        update_data.pop("progress", None)  # 移除退步的进度
        
    # 4. 执行更新
    session.execute(
        update(SubVideoTaskTable)
        .where(SubVideoTaskTable.sub_task_id == sub_task_id)
        .values(**update_data)
    )
    session.commit()
```

## 云存储交互详情

### 存储策略选择
根据 `settings.storage_type` 配置选择存储后端:

#### 1. MinIO 存储 (`storage_type="minio"`)
```python
# utils/storage_utils.py:53
def _upload_to_minio(file_path: str, filename: str, content_type: str) -> Optional[str]:
    client = Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key, 
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure
    )
    
    # 上传文件到指定bucket
    client.fput_object(
        bucket_name=settings.minio_bucket,
        object_name=filename,
        file_path=file_path,
        content_type=content_type
    )
    
    # 返回公网访问URL
    return f"https://{settings.minio_endpoint}/{settings.minio_bucket}/{filename}"
```

#### 2. 华为OBS存储 (`storage_type="obs"`)
```python 
# utils/storage_utils.py:134
def _upload_to_obs(file_path: str, filename: str, content_type: str) -> Optional[str]:
    client = ObsClient(
        access_key_id=settings.obs_access_key,
        secret_access_key=settings.obs_secret_key,
        server=settings.obs_endpoint
    )
    
    # 上传到指定bucket
    resp = client.putFile(
        bucketName=settings.obs_bucket,
        objectKey=filename,
        file_path=file_path
    )
    
    # 返回公网访问URL  
    return f"https://{settings.obs_bucket}.{settings.obs_endpoint}/{filename}"
```

#### 3. 本地存储 (`storage_type="local"`)
```python
# utils/storage_utils.py:187  
def _upload_to_local(file_path: str, filename: str) -> Optional[str]:
    # 目标目录: workspace/uploads/
    local_storage_dir = Path(settings.workspace_dir) / "uploads"
    local_storage_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制文件
    target_path = local_storage_dir / filename
    shutil.copy2(file_path, target_path)
    
    # 返回相对路径URL
    return f"/uploads/{filename}"
```

## 核心组件说明

### 1. SRT字幕解析器 (`SrtParser`)
**位置**: `services/subtitle_renderer.py:45`

**功能**: 解析SRT格式字幕文件
```python
def parse_srt_file(self, srt_path: str) -> List[SubtitleSegment]:
    # 解析SRT时间格式: 00:00:01,000 --> 00:00:03,500
    time_match = re.match(
        r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
        time_line,
    )
    # 转换为秒数时间戳
    start_time = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
```

### 2. 字幕片段模型 (`SubtitleSegment`)
**位置**: `services/subtitle_renderer.py:18`

**属性**:
- `start_time: float` - 开始时间戳（秒）
- `end_time: float` - 结束时间戳（秒）  
- `text: str` - 字幕文本内容
- `words: List[str]` - 分词结果

### 3. 简化字幕渲染器 (`SimpleSubtitleRenderer`)
**位置**: `services/subtitle_renderer.py:497`

**核心功能**:
- **视频信息解析**: 使用 `ffprobe` 获取视频参数
- **字幕滤镜生成**: 生成FFmpeg字幕滤镜链
- **多级渲染回退**: 标准渲染失败时的紧急回退方案
- **SRT/ASS格式支持**: 支持多种字幕格式输出

### 4. 高级动态字幕服务 (`AdvancedDynamicSubtitleService`)
**位置**: `services/subtitle_renderer.py:1067`

**高级特性**:
- **字体检测**: 自动检测可用的CJK字体
- **复杂滤镜**: 支持复杂的FFmpeg滤镜效果
- **容错机制**: 多级回退确保渲染成功率

## 错误处理机制

### 1. 渐进式降级策略
```python
# 渲染优先级: 复杂滤镜 -> 简单滤镜 -> SRT回退
if not _try_complex_filter():
    if not _try_emergency_fallback():
        return {"success": False, "error": "所有渲染方案均失败"}
```

### 2. 任务状态容错
- **终态保护**: 已完成状态不允许回退
- **进度单调**: 进度值只能递增不能递减  
- **错误记录**: 失败信息记录到 `error_message` 字段
- **优雅降级**: 字幕处理失败时返回原视频URL

### 3. 存储服务容错
- **多后端支持**: MinIO/OBS/本地存储自动切换
- **上传重试**: 网络异常时的重试机制
- **路径规范**: 统一的文件命名和路径规范

## 性能优化要点

### 1. 临时文件管理
- 使用 `tempfile.TemporaryDirectory()` 自动清理
- 及时释放下载的大文件

### 2. 数据库优化
- 行级锁避免并发冲突
- 索引优化查询性能
- 连接池管理数据库连接

### 3. FFmpeg优化
- 合理的超时设置
- 内存使用限制
- 多级回退保证成功率

## 配置参数

### 动态字幕相关配置
```python
# config/settings.py
dynamic_subtitle_enabled: bool = True              # 功能开关
dynamic_subtitle_style: str = "default"           # 默认样式
dynamic_subtitle_animation: str = "fade_in"       # 默认动画
dynamic_subtitle_font_size: int = 24              # 默认字体大小
dynamic_subtitle_font_color: str = "#FFFFFF"      # 默认字体颜色

# 存储配置
storage_type: str = "local"                       # 存储类型
workspace_dir: str = "./workspace"               # 工作目录
```

### 超时配置
```python
# 文件下载超时
video_download_timeout: int = 60    # 视频文件下载超时（秒）
subtitle_download_timeout: int = 30  # 字幕文件下载超时（秒）

# FFmpeg渲染超时
ffmpeg_render_timeout: int = 300    # FFmpeg渲染超时（秒）
```

## 监控与日志

### 关键日志记录点
1. **任务开始**: 记录输入参数和配置
2. **文件下载**: 记录下载进度和耗时
3. **字幕解析**: 记录解析的片段数量
4. **渲染过程**: 记录FFmpeg命令和输出
5. **上传结果**: 记录最终URL和文件大小
6. **状态更新**: 记录数据库操作结果

### 性能指标监控
- 处理时长统计
- 成功率统计  
- 错误类型分析
- 资源使用情况

---

**文档版本**: v1.0
**最后更新**: 2025-08-27
**作者**: TextLoom开发团队