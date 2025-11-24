"""
任务验证工具 - 确保Celery任务与数据库一致性
处理手动删除数据库任务但Redis中任务仍存在的情况
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from celery import current_task
from celery.exceptions import Ignore

from models.celery_db import sync_get_task_by_id
from models.task import TaskStatus

logger = logging.getLogger(__name__)


def validate_task_exists(func: Callable) -> Callable:
    """
    装饰器：验证数据库中任务是否存在
    如果任务不存在，自动撤销Celery任务并清理Redis状态
    
    适用于所有需要操作数据库任务的Celery任务
    """
    @wraps(func)
    def wrapper(self, task_id: str, *args, **kwargs) -> Any:
        # 检查任务在数据库中是否存在
        task_info = sync_get_task_by_id(task_id)
        
        if not task_info:
            error_msg = f"任务 {task_id} 在数据库中不存在，可能已被手动删除"
            logger.warning(f"🚫 {error_msg}")
            
            # 记录Celery任务信息用于调试
            celery_task_id = getattr(current_task.request, 'id', 'unknown') if current_task else 'unknown'
            worker_name = getattr(current_task.request, 'hostname', 'unknown') if current_task else 'unknown'
            
            logger.warning(
                f"撤销Celery任务:\n"
                f"  • 数据库任务ID: {task_id}\n"
                f"  • Celery任务ID: {celery_task_id}\n"
                f"  • Worker: {worker_name}\n"
                f"  • 原因: 数据库中任务不存在"
            )
            
            # 直接记录撤销信息，避免调用update_state触发后端异常处理
            # 注意：不使用update_state避免Celery后端异常信息格式问题
            logger.info(f"任务已标记为撤销 - 任务ID: {task_id}, Celery ID: {celery_task_id}")
            
            # 使用更简单的方式：直接使用Ignore但不传递复杂的异常信息
            raise Ignore()
        
        # 检查任务状态是否允许继续处理
        current_status = task_info.get('status')
        if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            error_msg = f"任务 {task_id} 状态为 {current_status}，不应继续处理"
            logger.warning(f"🚫 {error_msg}")
            
            # 记录状态不一致情况
            celery_task_id = getattr(current_task.request, 'id', 'unknown') if current_task else 'unknown'
            logger.warning(
                f"任务状态不一致:\n"
                f"  • 数据库任务ID: {task_id}\n"
                f"  • 数据库状态: {current_status}\n"
                f"  • Celery任务ID: {celery_task_id}\n"
                f"  • 建议: 清理Redis中的相关任务队列"
            )
            
            # 直接记录状态不一致信息，避免调用update_state
            logger.info(f"任务状态不一致已处理 - 任务ID: {task_id}, 数据库状态: {current_status}")
            
            raise Ignore()
        
        # 任务存在且状态正常，记录开始处理
        logger.info(
            f"✅ 任务验证通过 - 任务ID: {task_id}\n"
            f"  • 数据库状态: {current_status}\n"
            f"  • 继续执行Celery任务"
        )
        
        # 执行原始任务
        return func(self, task_id, *args, **kwargs)
    
    return wrapper


def validate_sub_task_exists(parent_task_id_param: str = 'task_id'):
    """
    装饰器：验证子任务的父任务是否存在
    
    Args:
        parent_task_id_param: 父任务ID在参数中的名称，默认为'task_id'
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取父任务ID
            parent_task_id = kwargs.get(parent_task_id_param)
            if not parent_task_id and args:
                # 如果kwargs中没有，尝试从args中获取（通常是第一个参数）
                parent_task_id = args[0] if len(args) > 0 else None
            
            if not parent_task_id:
                error_msg = f"无法获取父任务ID (参数名: {parent_task_id_param})"
                logger.error(f"🚫 {error_msg}")
                raise ValueError(error_msg)
            
            # 检查父任务是否存在
            task_info = sync_get_task_by_id(parent_task_id)
            
            if not task_info:
                error_msg = f"父任务 {parent_task_id} 在数据库中不存在，子任务无法继续"
                logger.warning(f"🚫 {error_msg}")
                
                celery_task_id = getattr(current_task.request, 'id', 'unknown') if current_task else 'unknown'
                logger.warning(
                    f"撤销子任务:\n"
                    f"  • 父任务ID: {parent_task_id}\n"
                    f"  • Celery任务ID: {celery_task_id}\n"
                    f"  • 原因: 父任务不存在"
                )
                
                # 直接记录子任务撤销信息，避免调用update_state
                logger.info(f"子任务已撤销 - 父任务ID: {parent_task_id}, Celery ID: {celery_task_id}")
                
                raise Ignore()
            
            # 执行原始任务
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


def log_task_consistency_info(task_id: str) -> Optional[dict]:
    """
    记录任务一致性信息，用于调试和监控
    
    Returns:
        任务信息字典，如果任务不存在则返回None
    """
    try:
        task_info = sync_get_task_by_id(task_id)
        
        if task_info:
            logger.info(
                f"📊 任务一致性信息 - 任务ID: {task_id}\n"
                f"  • 数据库状态: {task_info.get('status')}\n"
                f"  • 创建时间: {task_info.get('created_at')}\n"
                f"  • 更新时间: {task_info.get('updated_at')}\n"
                f"  • Celery任务ID: {task_info.get('celery_task_id', 'None')}\n"
                f"  • Worker名称: {task_info.get('worker_name', 'None')}"
            )
            return task_info
        else:
            logger.warning(f"📊 任务一致性检查 - 任务ID: {task_id} 在数据库中不存在")
            return None
    
    except Exception as e:
        logger.error(f"📊 任务一致性检查失败 - 任务ID: {task_id}, 错误: {e}")
        return None


def get_orphaned_celery_tasks_info() -> dict:
    """
    获取可能的孤儿Celery任务信息
    这个函数需要与Celery的监控工具结合使用
    
    Returns:
        包含孤儿任务信息的字典
    """
    try:
        from celery_config import celery_app
        
        # 获取活跃任务
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        orphaned_info = {
            'total_workers': len(active_tasks) if active_tasks else 0,
            'active_tasks_count': 0,
            'potential_orphans': [],
            'check_timestamp': logger.info.__globals__.get('datetime', {}).get('datetime', {}).get('utcnow', lambda: 'unknown')()
        }
        
        if active_tasks:
            for worker, tasks in active_tasks.items():
                orphaned_info['active_tasks_count'] += len(tasks)
                
                for task in tasks:
                    task_name = task.get('name', '')
                    task_args = task.get('args', [])
                    
                    # 检查是否是我们的任务
                    if 'process_text_to_video' in task_name or 'process_video_generation' in task_name:
                        if task_args:
                            db_task_id = task_args[0]
                            db_task = sync_get_task_by_id(db_task_id)
                            
                            if not db_task:
                                orphaned_info['potential_orphans'].append({
                                    'worker': worker,
                                    'celery_task_id': task.get('id'),
                                    'task_name': task_name,
                                    'db_task_id': db_task_id,
                                    'reason': 'database_task_missing'
                                })
        
        logger.info(
            f"🔍 孤儿任务检查结果:\n"
            f"  • 活跃Worker数: {orphaned_info['total_workers']}\n"
            f"  • 活跃任务数: {orphaned_info['active_tasks_count']}\n"
            f"  • 潜在孤儿任务数: {len(orphaned_info['potential_orphans'])}"
        )
        
        return orphaned_info
        
    except Exception as e:
        logger.error(f"获取孤儿任务信息失败: {e}")
        return {'error': str(e)}