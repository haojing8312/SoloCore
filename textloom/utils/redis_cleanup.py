"""
Redis任务清理工具 - 确保Redis与数据库的一致性
处理孤儿Celery任务和过期任务清理
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from celery import current_app
from celery.result import AsyncResult
from redis import Redis

from celery_config import celery_app
from config import get_settings
from models.celery_db import sync_get_all_active_tasks, sync_get_task_by_id

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisTaskCleaner:
    """Redis任务清理器 - 维护Celery任务与数据库的一致性"""
    
    def __init__(self):
        # 构建Redis URL
        redis_url = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        self.redis_client = Redis.from_url(redis_url)
        self.celery_app = celery_app
    
    def get_active_database_task_ids(self) -> Set[str]:
        """获取数据库中所有活跃任务的ID列表"""
        try:
            active_tasks = sync_get_all_active_tasks()
            task_ids = {task['id'] for task in active_tasks if task.get('id')}
            logger.info(f"📊 数据库中活跃任务数: {len(task_ids)}")
            return task_ids
        except Exception as e:
            logger.error(f"获取数据库活跃任务失败: {e}")
            return set()
    
    def get_celery_active_tasks(self) -> Dict[str, List[Dict]]:
        """获取Celery中所有活跃任务"""
        try:
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            
            total_tasks = sum(len(tasks) for tasks in active_tasks.values())
            logger.info(f"📊 Celery中活跃任务数: {total_tasks}")
            
            return active_tasks
        except Exception as e:
            logger.error(f"获取Celery活跃任务失败: {e}")
            return {}
    
    def get_celery_reserved_tasks(self) -> Dict[str, List[Dict]]:
        """获取Celery中所有预留任务（队列中等待执行的任务）"""
        try:
            inspect = self.celery_app.control.inspect()
            reserved_tasks = inspect.reserved() or {}
            
            total_tasks = sum(len(tasks) for tasks in reserved_tasks.values())
            logger.info(f"📊 Celery中预留任务数: {total_tasks}")
            
            return reserved_tasks
        except Exception as e:
            logger.error(f"获取Celery预留任务失败: {e}")
            return {}
    
    def find_orphaned_celery_tasks(self) -> List[Dict]:
        """找到孤儿Celery任务（数据库中不存在但Celery中存在的任务）"""
        db_task_ids = self.get_active_database_task_ids()
        active_tasks = self.get_celery_active_tasks()
        reserved_tasks = self.get_celery_reserved_tasks()
        
        orphaned_tasks = []
        
        # 检查活跃任务
        for worker, tasks in active_tasks.items():
            for task in tasks:
                db_task_id = self._extract_db_task_id(task)
                if db_task_id and db_task_id not in db_task_ids:
                    orphaned_tasks.append({
                        'type': 'active',
                        'worker': worker,
                        'celery_task_id': task.get('id'),
                        'task_name': task.get('name'),
                        'db_task_id': db_task_id,
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'reason': 'database_task_missing'
                    })
        
        # 检查预留任务
        for worker, tasks in reserved_tasks.items():
            for task in tasks:
                db_task_id = self._extract_db_task_id(task)
                if db_task_id and db_task_id not in db_task_ids:
                    orphaned_tasks.append({
                        'type': 'reserved',
                        'worker': worker,
                        'celery_task_id': task.get('id'),
                        'task_name': task.get('name'),
                        'db_task_id': db_task_id,
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'reason': 'database_task_missing'
                    })
        
        logger.info(f"🔍 发现孤儿任务数: {len(orphaned_tasks)}")
        return orphaned_tasks
    
    def _extract_db_task_id(self, celery_task: Dict) -> Optional[str]:
        """从Celery任务信息中提取数据库任务ID"""
        try:
            args = celery_task.get('args', [])
            if args and len(args) > 0:
                return str(args[0])  # 第一个参数通常是数据库任务ID
            return None
        except Exception as e:
            logger.debug(f"提取任务ID失败: {e}")
            return None
    
    def revoke_orphaned_tasks(self, orphaned_tasks: List[Dict], force: bool = False) -> Dict[str, int]:
        """撤销孤儿任务"""
        results = {
            'revoked': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for task in orphaned_tasks:
            celery_task_id = task.get('celery_task_id')
            db_task_id = task.get('db_task_id')
            task_type = task.get('type')
            
            if not celery_task_id:
                results['skipped'] += 1
                continue
            
            try:
                # 撤销Celery任务
                result = AsyncResult(celery_task_id, app=self.celery_app)
                
                if force or task_type == 'reserved':
                    # 强制撤销或撤销预留任务
                    result.revoke(terminate=True, signal='SIGKILL')
                    action = 'force_revoked' if force else 'revoked'
                else:
                    # 优雅撤销活跃任务
                    result.revoke(terminate=False)
                    action = 'revoked'
                
                logger.warning(
                    f"🚫 {action.upper()}: {task_type} task\n"
                    f"  • Celery任务ID: {celery_task_id}\n"
                    f"  • 数据库任务ID: {db_task_id}\n"
                    f"  • Worker: {task.get('worker')}\n"
                    f"  • 任务名称: {task.get('task_name')}\n"
                    f"  • 原因: {task.get('reason')}"
                )
                
                results['revoked'] += 1
                
                # 短暂延迟，避免撤销操作过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"撤销任务失败 - Celery任务ID: {celery_task_id}, 错误: {e}")
                results['failed'] += 1
        
        return results
    
    def clean_completed_task_results(self, max_age_hours: int = 24) -> int:
        """清理过期的任务结果"""
        try:
            # 使用通用的Celery结果键模式
            pattern = "celery-task-meta-*"
            keys = self.redis_client.keys(pattern)
            
            cleaned = 0
            
            for key in keys:
                try:
                    # 检查键的TTL
                    ttl = self.redis_client.ttl(key)
                    if ttl == -1:  # 没有过期时间的键
                        # 提取任务ID
                        key_str = key.decode() if isinstance(key, bytes) else str(key)
                        task_id = key_str.split('-')[-1]
                        
                        try:
                            result = AsyncResult(task_id, app=self.celery_app)
                            
                            if result.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                                # 删除已完成任务的结果
                                self.redis_client.delete(key)
                                cleaned += 1
                        except Exception:
                            # 如果任务ID无效，也删除这个键
                            self.redis_client.delete(key)
                            cleaned += 1
                
                except Exception as e:
                    logger.debug(f"清理结果键失败 {key}: {e}")
            
            logger.info(f"🧹 清理过期任务结果: {cleaned} 个")
            return cleaned
            
        except Exception as e:
            logger.error(f"清理任务结果失败: {e}")
            return 0
    
    def perform_full_cleanup(self, force_revoke: bool = False, max_result_age_hours: int = 24) -> Dict:
        """执行完整的Redis清理操作"""
        cleanup_start = datetime.utcnow()
        
        logger.info("🧹 开始Redis任务清理...")
        
        # 1. 找到孤儿任务
        orphaned_tasks = self.find_orphaned_celery_tasks()
        
        # 2. 撤销孤儿任务
        revoke_results = {'revoked': 0, 'failed': 0, 'skipped': 0}
        if orphaned_tasks:
            revoke_results = self.revoke_orphaned_tasks(orphaned_tasks, force=force_revoke)
        
        # 3. 清理过期结果
        cleaned_results = self.clean_completed_task_results(max_result_age_hours)
        
        cleanup_duration = (datetime.utcnow() - cleanup_start).total_seconds()
        
        summary = {
            'cleanup_duration': f"{cleanup_duration:.2f}s",
            'orphaned_tasks_found': len(orphaned_tasks),
            'tasks_revoked': revoke_results['revoked'],
            'revoke_failed': revoke_results['failed'],
            'revoke_skipped': revoke_results['skipped'],
            'results_cleaned': cleaned_results,
            'force_revoke_used': force_revoke,
            'timestamp': cleanup_start.isoformat()
        }
        
        logger.info(
            f"✅ Redis清理完成:\n"
            f"  • 耗时: {cleanup_duration:.2f}s\n"
            f"  • 孤儿任务: {len(orphaned_tasks)} 个\n"
            f"  • 已撤销: {revoke_results['revoked']} 个\n"
            f"  • 撤销失败: {revoke_results['failed']} 个\n"
            f"  • 已跳过: {revoke_results['skipped']} 个\n"
            f"  • 清理结果: {cleaned_results} 个\n"
            f"  • 强制模式: {force_revoke}"
        )
        
        return summary
    
    def check_task_consistency(self, task_id: str) -> Dict:
        """检查特定任务的一致性状态"""
        try:
            # 检查数据库中的任务
            db_task = sync_get_task_by_id(task_id)
            
            # 检查Celery中的任务
            celery_task_id = db_task.get('celery_task_id') if db_task else None
            celery_status = None
            
            if celery_task_id:
                result = AsyncResult(celery_task_id, app=self.celery_app)
                celery_status = result.state
            
            consistency = {
                'task_id': task_id,
                'database_exists': bool(db_task),
                'database_status': db_task.get('status') if db_task else None,
                'celery_task_id': celery_task_id,
                'celery_status': celery_status,
                'consistent': bool(db_task) == bool(celery_task_id and celery_status not in ['PENDING']),
                'check_timestamp': datetime.utcnow().isoformat()
            }
            
            return consistency
            
        except Exception as e:
            logger.error(f"检查任务一致性失败 - 任务ID: {task_id}, 错误: {e}")
            return {
                'task_id': task_id,
                'error': str(e),
                'check_timestamp': datetime.utcnow().isoformat()
            }


# 便捷函数
def cleanup_redis_tasks(force: bool = False, max_age_hours: int = 24) -> Dict:
    """便捷函数：执行Redis任务清理"""
    cleaner = RedisTaskCleaner()
    return cleaner.perform_full_cleanup(force_revoke=force, max_result_age_hours=max_age_hours)


def check_task_consistency(task_id: str) -> Dict:
    """便捷函数：检查单个任务的一致性"""
    cleaner = RedisTaskCleaner()
    return cleaner.check_task_consistency(task_id)


def find_orphaned_tasks() -> List[Dict]:
    """便捷函数：找到所有孤儿任务"""
    cleaner = RedisTaskCleaner()
    return cleaner.find_orphaned_celery_tasks()