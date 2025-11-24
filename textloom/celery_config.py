"""
Celery配置模块
使用Redis作为消息代理和结果后端，实现任务队列与API服务的完全解耦
"""

from celery import Celery
from kombu import Queue

from config import settings

# 创建Celery应用实例
celery_app = Celery(
    "textloom",
    broker=f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
    backend=f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
    include=[
        "tasks.video_processing_tasks",
        # "tasks.video_merge_polling",  # 已禁用 - SubVideoTask 功能已移除
        # "tasks.dynamic_subtitle_tasks"  # 已禁用 - 需要重构以支持单视频架构
    ],
)

# Celery配置
celery_app.conf.update(
    # 序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 时区配置
    timezone="UTC",
    enable_utc=True,
    # 任务跟踪配置
    task_track_started=True,
    task_send_sent_event=True,
    # 任务超时配置
    task_time_limit=settings.task_timeout,
    task_soft_time_limit=settings.task_timeout - 300,
    # Worker配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    worker_disable_rate_limits=True,
    # 任务确认配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 结果配置
    result_expires=3600,  # 结果保存1小时
    result_compression="gzip",
    # 临时禁用结果存储以避免序列化错误
    task_ignore_result=True,
    result_backend_transport_options={
        "visibility_timeout": 3600,
        "retry_on_timeout": True,
        "socket_keepalive": True,
        "socket_keepalive_options": {
            "TCP_KEEPIDLE": 1,
            "TCP_KEEPINTVL": 3,
            "TCP_KEEPCNT": 5,
        },
    },
    # 异常处理配置 - 避免序列化问题
    result_backend_always_retry=True,
    result_backend_max_retries=3,
    # 任务路由配置（使用实际任务名：模块路径 + 函数名）
    task_routes={
        "tasks.video_processing_tasks.process_text_to_video": {
            "queue": "video_processing"
        },
        "tasks.video_processing_tasks.process_video_generation": {
            "queue": "video_generation"
        },
        "tasks.video_processing_tasks.cleanup_expired_tasks": {"queue": "maintenance"},
        "tasks.video_processing_tasks.health_check": {"queue": "monitoring"},
        "tasks.dynamic_subtitle_tasks.process_pycaps_subtitles_task": {
            "queue": "video_generation"
        },
        "tasks.dynamic_subtitle_tasks.batch_process_pycaps_subtitles_task": {
            "queue": "video_generation"
        },
    },
    # 队列配置 - 明确定义队列避免Kombu自动添加后缀
    task_queues=[
        Queue("video_processing", routing_key="video_processing"),
        Queue("video_generation", routing_key="video_generation"),
        Queue("maintenance", routing_key="maintenance"),
        Queue("monitoring", routing_key="monitoring"),
        Queue("default", routing_key="default"),
    ],
    task_default_queue="default",
    task_default_exchange="default",
    task_default_exchange_type="direct",
    task_default_routing_key="default",
    # 重试配置
    task_autoretry_for=(Exception,),
    task_retry_backoff=True,
    task_retry_backoff_max=700,
    task_retry_jitter=False,
    task_max_retries=3,
    # 监控配置
    worker_send_task_events=True,
    # Redis连接池配置
    broker_connection_retry_on_startup=True,
    broker_pool_limit=20,
    # 任务优先级支持
    task_inherit_parent_priority=True,
    task_default_priority=5,
)

# Celery Beat 静态调度配置 - 已禁用（SubVideoTask 功能已移除）
# celery_app.conf.beat_schedule = {
#     "poll_video_merge_results": {
#         "task": "tasks.video_merge_polling.poll_video_merge_results",
#         "schedule": 60.0,
#         # 指定投递到 maintenance 队列，和任务装饰器保持一致
#         "options": {"queue": "maintenance"},
#     },
# }
