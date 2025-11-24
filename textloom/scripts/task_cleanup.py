#!/usr/bin/env python3
"""
任务清理管理脚本
处理数据库与Redis任务一致性问题的命令行工具
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.redis_cleanup import RedisTaskCleaner, cleanup_redis_tasks, check_task_consistency, find_orphaned_tasks
from utils.task_validation import log_task_consistency_info


def setup_logging(verbose: bool = False):
    """设置日志配置"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/home/easegen/textloom/logs/task_cleanup.log')
        ]
    )


def cmd_check_consistency(args):
    """检查任务一致性"""
    if args.task_id:
        # 检查特定任务
        result = check_task_consistency(args.task_id)
        print(f"任务一致性检查结果 - {args.task_id}:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        # 检查所有孤儿任务
        orphaned = find_orphaned_tasks()
        if orphaned:
            print(f"发现 {len(orphaned)} 个孤儿任务:")
            for task in orphaned:
                print(f"  类型: {task.get('type')}")
                print(f"  Celery任务ID: {task.get('celery_task_id')}")
                print(f"  数据库任务ID: {task.get('db_task_id')}")
                print(f"  Worker: {task.get('worker')}")
                print(f"  原因: {task.get('reason')}")
                print("  ---")
        else:
            print("✅ 没有发现孤儿任务")


def cmd_cleanup(args):
    """执行清理操作"""
    print(f"开始执行任务清理...")
    print(f"参数: 强制模式={args.force}, 结果保留时间={args.max_age}小时")
    
    if not args.force:
        response = input("确认执行清理操作? (y/N): ")
        if response.lower() != 'y':
            print("操作已取消")
            return
    
    result = cleanup_redis_tasks(force=args.force, max_age_hours=args.max_age)
    
    print("清理完成:")
    for key, value in result.items():
        print(f"  {key}: {value}")


def cmd_monitor(args):
    """监控任务状态"""
    cleaner = RedisTaskCleaner()
    
    print("=== 任务监控报告 ===")
    print(f"时间: {datetime.now().isoformat()}")
    
    # 数据库活跃任务
    db_tasks = cleaner.get_active_database_task_ids()
    print(f"数据库活跃任务: {len(db_tasks)} 个")
    
    # Celery活跃任务
    celery_active = cleaner.get_celery_active_tasks()
    celery_reserved = cleaner.get_celery_reserved_tasks()
    
    total_active = sum(len(tasks) for tasks in celery_active.values())
    total_reserved = sum(len(tasks) for tasks in celery_reserved.values())
    
    print(f"Celery活跃任务: {total_active} 个")
    print(f"Celery预留任务: {total_reserved} 个")
    
    # 孤儿任务
    orphaned = cleaner.find_orphaned_celery_tasks()
    if orphaned:
        print(f"⚠️  孤儿任务: {len(orphaned)} 个")
        if args.verbose:
            for task in orphaned[:5]:  # 显示前5个
                print(f"  - {task.get('celery_task_id')} (DB: {task.get('db_task_id')})")
            if len(orphaned) > 5:
                print(f"  ... 还有 {len(orphaned) - 5} 个")
    else:
        print("✅ 没有孤儿任务")


def cmd_revoke(args):
    """撤销指定任务"""
    from celery.result import AsyncResult
    from celery_config import celery_app
    
    if args.celery_task_id:
        # 撤销Celery任务
        result = AsyncResult(args.celery_task_id, app=celery_app)
        result.revoke(terminate=args.force)
        print(f"已撤销Celery任务: {args.celery_task_id} (强制: {args.force})")
    
    if args.task_id:
        # 检查并记录数据库任务状态
        info = log_task_consistency_info(args.task_id)
        if info:
            celery_task_id = info.get('celery_task_id')
            if celery_task_id:
                result = AsyncResult(celery_task_id, app=celery_app)
                result.revoke(terminate=args.force)
                print(f"已撤销相关Celery任务: {celery_task_id}")
            else:
                print(f"任务 {args.task_id} 没有关联的Celery任务")
        else:
            print(f"任务 {args.task_id} 在数据库中不存在")


def main():
    parser = argparse.ArgumentParser(
        description="TextLoom 任务清理管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s check                    # 检查所有孤儿任务
  %(prog)s check --task-id <id>     # 检查特定任务
  %(prog)s cleanup                  # 执行清理（交互确认）
  %(prog)s cleanup --force          # 强制清理（无确认）
  %(prog)s monitor                  # 监控任务状态
  %(prog)s revoke --task-id <id>    # 撤销数据库任务对应的Celery任务
  %(prog)s revoke --celery-task-id <id> --force  # 强制终止Celery任务
        """
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='输出详细日志'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # check命令
    check_parser = subparsers.add_parser('check', help='检查任务一致性')
    check_parser.add_argument(
        '--task-id',
        help='检查特定任务ID的一致性'
    )
    
    # cleanup命令
    cleanup_parser = subparsers.add_parser('cleanup', help='执行Redis任务清理')
    cleanup_parser.add_argument(
        '--force',
        action='store_true',
        help='强制清理，无需确认'
    )
    cleanup_parser.add_argument(
        '--max-age',
        type=int,
        default=24,
        help='清理多少小时前的任务结果 (默认: 24)'
    )
    
    # monitor命令
    monitor_parser = subparsers.add_parser('monitor', help='监控任务状态')
    
    # revoke命令
    revoke_parser = subparsers.add_parser('revoke', help='撤销任务')
    revoke_parser.add_argument(
        '--task-id',
        help='要撤销的数据库任务ID'
    )
    revoke_parser.add_argument(
        '--celery-task-id',
        help='要撤销的Celery任务ID'
    )
    revoke_parser.add_argument(
        '--force',
        action='store_true',
        help='强制终止任务'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    setup_logging(args.verbose)
    
    try:
        if args.command == 'check':
            cmd_check_consistency(args)
        elif args.command == 'cleanup':
            cmd_cleanup(args)
        elif args.command == 'monitor':
            cmd_monitor(args)
        elif args.command == 'revoke':
            cmd_revoke(args)
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n操作已中断")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"执行命令失败: {e}", exc_info=True)
        print(f"❌ 执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()