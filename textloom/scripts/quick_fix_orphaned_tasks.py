#!/usr/bin/env python3
"""
快速修复孤儿任务脚本
立即清理当前Redis中存在但数据库中不存在的任务
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.redis_cleanup import cleanup_redis_tasks


def main():
    print("🧹 开始快速清理孤儿任务...")
    
    try:
        # 执行强制清理
        result = cleanup_redis_tasks(force=True, max_age_hours=1)
        
        print("✅ 清理完成:")
        print(f"  - 孤儿任务: {result.get('orphaned_tasks_found', 0)} 个")
        print(f"  - 已撤销: {result.get('tasks_revoked', 0)} 个")
        print(f"  - 撤销失败: {result.get('revoke_failed', 0)} 个")
        print(f"  - 清理结果: {result.get('results_cleaned', 0)} 个")
        print(f"  - 耗时: {result.get('cleanup_duration', 'unknown')}")
        
        if result.get('tasks_revoked', 0) > 0:
            print("\n🔄 建议重启Celery Worker以完全清理状态")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())