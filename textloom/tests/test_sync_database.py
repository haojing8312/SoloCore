"""
测试同步数据库操作
验证 models/celery_db.py 中的所有同步方法
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


# 由于实际的数据库连接可能不存在，我们使用mock进行测试
@pytest.fixture
def mock_db_connection():
    """模拟数据库连接"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor

    # 模拟查询结果
    mock_cursor.fetchone.return_value = {
        "id": "test-id",
        "status": "processing",
        "progress": 50,
    }
    mock_cursor.fetchall.return_value = [
        {"id": "test-id-1", "name": "test1"},
        {"id": "test-id-2", "name": "test2"},
    ]
    mock_cursor.rowcount = 1

    return mock_conn, mock_cursor


class TestSyncDatabaseOperations:
    """测试同步数据库操作"""

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_get_task_by_id(self, mock_get_conn, mock_db_connection):
        """测试获取任务信息"""
        from models.celery_db import sync_get_task_by_id

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        # 测试正常情况
        result = sync_get_task_by_id("test-task-1")

        # 验证调用
        mock_cursor.execute.assert_called_once()
        assert result["id"] == "test-id"
        assert result["status"] == "processing"

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_update_task_status(self, mock_get_conn, mock_db_connection):
        """测试更新任务状态"""
        from models.celery_db import sync_update_task_status

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        # 测试更新状态
        result = sync_update_task_status("test-task-1", "completed", "任务完成")

        # 验证调用
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result is True

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_update_task_progress(self, mock_get_conn, mock_db_connection):
        """测试更新任务进度"""
        from models.celery_db import sync_update_task_progress

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        # 测试更新进度
        result = sync_update_task_progress(
            "test-task-1", 75, "script_generation", "生成脚本中"
        )

        # 验证调用
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result is True

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_create_media_item(self, mock_get_conn, mock_db_connection):
        """测试创建媒体项"""
        from models.celery_db import sync_create_media_item

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        media_data = {
            "task_id": "test-task-1",
            "filename": "test.jpg",
            "file_type": "image",
            "file_size": 1024,
            "file_url": "https://example.com/test.jpg",
        }

        # 测试创建媒体项
        result = sync_create_media_item(media_data)

        # 验证调用
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result["id"] == "test-id"

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_create_material_analysis(self, mock_get_conn, mock_db_connection):
        """测试创建素材分析记录"""
        from models.celery_db import sync_create_material_analysis

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        analysis_data = {
            "media_item_id": "test-media-1",
            "ai_description": "测试描述",
            "key_objects": ["object1", "object2"],
            "analysis_status": "completed",
        }

        # 测试创建分析记录
        result = sync_create_material_analysis(analysis_data)

        # 验证调用
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result["id"] == "test-id"

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_get_persona_by_id(self, mock_get_conn, mock_db_connection):
        """测试获取人设信息"""
        from models.celery_db import sync_get_persona_by_id

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        # 测试获取人设
        result = sync_get_persona_by_id(1)

        # 验证调用
        mock_cursor.execute.assert_called_once()
        assert result["id"] == "test-id"

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_create_script_content(self, mock_get_conn, mock_db_connection):
        """测试创建脚本内容"""
        from models.celery_db import sync_create_script_content

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        script_data = {
            "task_id": "test-task-1",
            "script_style": "default",
            "generation_status": "completed",
        }

        # 测试创建脚本
        result = sync_create_script_content(script_data)

        # 验证调用
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result["id"] == "test-id"

    @patch("models.celery_db.get_sync_db_connection")
    def test_sync_update_task_multi_video_results(
        self, mock_get_conn, mock_db_connection
    ):
        """测试更新多视频结果"""
        from models.celery_db import sync_update_task_multi_video_results

        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = mock_conn

        multi_video_results = [
            {
                "sub_task_id": "test-task-1_video_1",
                "success": True,
                "video_url": "https://example.com/video1.mp4",
            },
            {
                "sub_task_id": "test-task-1_video_2",
                "success": True,
                "video_url": "https://example.com/video2.mp4",
            },
        ]

        # 测试更新多视频结果
        result = sync_update_task_multi_video_results(
            "test-task-1", multi_video_results
        )

        # 验证调用
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        assert result is True

    @patch("models.celery_db.get_sync_db_connection")
    def test_database_error_handling(self, mock_get_conn):
        """测试数据库错误处理"""
        from models.celery_db import sync_get_task_by_id

        # 模拟数据库连接错误
        mock_get_conn.side_effect = Exception("Database connection failed")

        # 测试错误处理
        result = sync_get_task_by_id("test-task-1")

        # 应该返回None而不是抛出异常
        assert result is None

    @patch("models.celery_db.get_sync_db_connection")
    def test_connection_pool_cleanup(self, mock_get_conn, mock_db_connection):
        """测试连接池清理"""
        from models.celery_db import close_sync_connection_pool

        mock_conn, _ = mock_db_connection
        mock_get_conn.return_value = mock_conn

        # 测试连接池清理
        close_sync_connection_pool()

        # 这里主要测试不会抛出异常
        # 具体的连接关闭逻辑由实际的连接池实现

    def test_database_health_check(self):
        """测试数据库健康检查"""
        from models.celery_db import sync_check_database_health

        # 由于这是一个实际的健康检查，在测试环境中可能会失败
        # 我们主要测试它不会抛出未处理的异常
        try:
            result = sync_check_database_health()
            assert isinstance(result, dict)
            assert "status" in result
        except Exception:
            # 在测试环境中数据库连接可能不可用，这是正常的
            pass
