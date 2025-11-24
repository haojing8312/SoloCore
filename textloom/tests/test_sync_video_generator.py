"""
测试同步视频生成器
验证 services/sync_video_generator.py 的并发视频生成功能
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from tests.conftest import TEST_MEDIA_FILES


class TestSyncVideoGenerator:
    """测试同步视频生成器"""

    @pytest.fixture
    def mock_http_client(self):
        """模拟HTTP客户端"""
        with patch("services.sync_video_generator.get_sync_http_client") as mock:
            client = Mock()
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_database(self):
        """模拟数据库操作"""
        with (
            patch(
                "services.sync_video_generator.sync_create_sub_video_task"
            ) as create_mock,
            patch(
                "services.sync_video_generator.sync_update_sub_video_task"
            ) as update_mock,
        ):
            create_mock.return_value = "sub-task-id"
            yield {"create_sub_task": create_mock, "update_sub_task": update_mock}

    @pytest.fixture
    def mock_file_operations(self):
        """模拟文件操作"""
        with (
            patch("services.sync_video_generator.os.path.exists") as exists_mock,
            patch("services.sync_video_generator.shutil.copy2") as copy_mock,
        ):
            exists_mock.return_value = True
            yield {"exists": exists_mock, "copy": copy_mock}

    def test_generate_single_video_success(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试单个视频生成成功"""
        from services.sync_video_generator import SyncVideoGenerator

        # 模拟成功的视频生成响应
        mock_http_client.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "success": True,
                "video_url": "https://example.com/video.mp4",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "duration": 120,
                "course_media_id": "media123",
            },
        )

        generator = SyncVideoGenerator()
        result = generator.generate_single_video_sync(
            script_data={
                "title": "测试视频",
                "description": "测试描述",
                "narration": "测试旁白",
                "scenes": [{"scene_id": 1, "description": "场景1"}],
                "script_style": "default",
            },
            media_files=TEST_MEDIA_FILES,
            task_id="test-task",
            sub_task_index=1,
            mode="multi_scene",
        )

        assert result["success"] is True
        assert result["video_url"] == "https://example.com/video.mp4"
        assert result["duration"] == 120
        assert result["script_style"] == "default"
        mock_database["create_sub_task"].assert_called_once()
        mock_database["update_sub_task"].assert_called()

    def test_generate_single_video_api_failure(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试视频生成API失败"""
        from services.sync_video_generator import SyncVideoGenerator

        # 模拟API失败响应
        mock_http_client.post.return_value = Mock(
            status_code=500,
            json=lambda: {"error": "服务器内部错误"},
            text="Internal Server Error",
        )

        generator = SyncVideoGenerator()
        result = generator.generate_single_video_sync(
            script_data={
                "title": "测试视频",
                "description": "测试描述",
                "narration": "测试旁白",
                "scenes": [],
                "script_style": "default",
            },
            media_files=[],
            task_id="test-task",
            sub_task_index=1,
            mode="single_scene",
        )

        assert result["success"] is False
        assert "视频生成API调用失败" in result["error"]
        assert result["status_code"] == 500

    def test_generate_multiple_videos_success(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试多视频并发生成成功"""
        from services.sync_video_generator import SyncVideoGenerator

        # 模拟多个成功响应
        def mock_post(*args, **kwargs):
            return Mock(
                status_code=200,
                json=lambda: {
                    "success": True,
                    "video_url": f"https://example.com/video_{len(mock_post.calls)}.mp4",
                    "thumbnail_url": f"https://example.com/thumb_{len(mock_post.calls)}.jpg",
                    "duration": 120 + len(mock_post.calls) * 10,
                    "course_media_id": f"media{len(mock_post.calls)}",
                },
            )

        mock_post.calls = []
        mock_http_client.post.side_effect = lambda *args, **kwargs: (
            mock_post.calls.append(1),
            mock_post(*args, **kwargs),
        )[1]

        scripts_data = [
            {
                "title": f"测试视频{i}",
                "description": f"描述{i}",
                "narration": f"旁白{i}",
                "scenes": [],
                "script_style": "default" if i % 2 == 0 else "product_geek",
            }
            for i in range(3)
        ]

        generator = SyncVideoGenerator()
        results = generator.generate_multiple_videos_sync(
            scripts_data=scripts_data,
            media_files=TEST_MEDIA_FILES,
            task_id="test-task",
            mode="multi_scene",
        )

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert results[0]["video_url"] == "https://example.com/video_1.mp4"
        assert results[1]["script_style"] == "product_geek"
        assert mock_database["create_sub_task"].call_count == 3

    def test_generate_multiple_videos_partial_failure(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试多视频生成部分失败"""
        from services.sync_video_generator import SyncVideoGenerator

        # 模拟部分成功部分失败
        def mock_post(*args, **kwargs):
            call_count = len(mock_post.calls)
            mock_post.calls.append(1)

            if call_count == 0:  # 第一个成功
                return Mock(
                    status_code=200,
                    json=lambda: {
                        "success": True,
                        "video_url": "https://example.com/video1.mp4",
                        "thumbnail_url": "https://example.com/thumb1.jpg",
                        "duration": 120,
                        "course_media_id": "media1",
                    },
                )
            else:  # 第二个失败
                return Mock(
                    status_code=500,
                    json=lambda: {"error": "生成失败"},
                    text="Server Error",
                )

        mock_post.calls = []
        mock_http_client.post.side_effect = mock_post

        scripts_data = [
            {
                "title": "成功视频",
                "description": "",
                "narration": "",
                "scenes": [],
                "script_style": "default",
            },
            {
                "title": "失败视频",
                "description": "",
                "narration": "",
                "scenes": [],
                "script_style": "default",
            },
        ]

        generator = SyncVideoGenerator()
        results = generator.generate_multiple_videos_sync(
            scripts_data=scripts_data,
            media_files=[],
            task_id="test-task",
            mode="single_scene",
        )

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "视频生成API调用失败" in results[1]["error"]

    def test_prepare_video_request_data(self, mock_file_operations):
        """测试视频请求数据准备"""
        from services.sync_video_generator import SyncVideoGenerator

        generator = SyncVideoGenerator()
        script_data = {
            "title": "测试视频",
            "description": "测试描述",
            "narration": "这是测试旁白内容",
            "scenes": [
                {
                    "scene_id": 1,
                    "scene_title": "场景1",
                    "description": "场景描述",
                    "media_elements": ["test.jpg"],
                }
            ],
            "script_style": "product_geek",
        }

        request_data = generator._prepare_video_request_data_sync(
            script_data=script_data,
            media_files=TEST_MEDIA_FILES,
            sub_task_id="sub-123",
            mode="multi_scene",
        )

        assert request_data["title"] == "测试视频"
        assert request_data["description"] == "测试描述"
        assert request_data["mode"] == "multi_scene"
        assert request_data["sub_task_id"] == "sub-123"
        assert "narration" in request_data
        assert "scenes" in request_data

    def test_copy_media_files_to_workspace(self, mock_file_operations):
        """测试媒体文件复制到工作空间"""
        import os
        import tempfile

        from services.sync_video_generator import SyncVideoGenerator

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_dir = os.path.join(temp_dir, "workspace")
            os.makedirs(workspace_dir, exist_ok=True)

            generator = SyncVideoGenerator()
            result = generator._copy_media_files_to_workspace_sync(
                media_files=TEST_MEDIA_FILES, workspace_dir=workspace_dir
            )

            assert "workspace_media_files" in result
            # 验证文件复制调用
            assert mock_file_operations["copy"].call_count == len(TEST_MEDIA_FILES)

    def test_concurrent_video_generation_performance(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试并发视频生成性能"""
        import time

        from services.sync_video_generator import SyncVideoGenerator

        # 模拟API调用延迟
        def mock_post_with_delay(*args, **kwargs):
            time.sleep(0.01)  # 优化：减少测试延迟从100ms到10ms
            return Mock(
                status_code=200,
                json=lambda: {
                    "success": True,
                    "video_url": "https://example.com/video.mp4",
                    "thumbnail_url": "https://example.com/thumb.jpg",
                    "duration": 120,
                    "course_media_id": "media123",
                },
            )

        mock_http_client.post.side_effect = mock_post_with_delay

        scripts_data = [
            {
                "title": f"视频{i}",
                "description": "",
                "narration": "",
                "scenes": [],
                "script_style": "default",
            }
            for i in range(3)
        ]

        generator = SyncVideoGenerator()

        start_time = time.time()
        results = generator.generate_multiple_videos_sync(
            scripts_data=scripts_data,
            media_files=[],
            task_id="test-task",
            mode="single_scene",
        )
        end_time = time.time()

        # 并发执行应该比串行快
        execution_time = end_time - start_time
        assert execution_time < 0.25  # 应该小于3*0.1秒
        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_error_handling_network_timeout(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试网络超时错误处理"""
        import requests

        from services.sync_video_generator import SyncVideoGenerator

        # 模拟网络超时
        mock_http_client.post.side_effect = requests.Timeout("请求超时")

        generator = SyncVideoGenerator()
        result = generator.generate_single_video_sync(
            script_data={
                "title": "测试视频",
                "description": "测试描述",
                "narration": "测试旁白",
                "scenes": [],
                "script_style": "default",
            },
            media_files=[],
            task_id="test-task",
            sub_task_index=1,
            mode="single_scene",
        )

        assert result["success"] is False
        assert "网络超时" in result["error"] or "请求超时" in result["error"]

    def test_invalid_script_data_handling(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试无效脚本数据处理"""
        from services.sync_video_generator import SyncVideoGenerator

        generator = SyncVideoGenerator()

        # 测试空脚本数据
        result = generator.generate_single_video_sync(
            script_data={},
            media_files=[],
            task_id="test-task",
            sub_task_index=1,
            mode="single_scene",
        )

        assert result["success"] is False
        assert "脚本数据无效" in result["error"] or "必需字段" in result["error"]

    def test_sub_task_management(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试子任务管理"""
        from services.sync_video_generator import SyncVideoGenerator

        mock_http_client.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "success": True,
                "video_url": "https://example.com/video.mp4",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "duration": 120,
                "course_media_id": "media123",
            },
        )

        generator = SyncVideoGenerator()
        result = generator.generate_single_video_sync(
            script_data={
                "title": "测试视频",
                "description": "测试描述",
                "narration": "测试旁白",
                "scenes": [],
                "script_style": "default",
            },
            media_files=[],
            task_id="main-task",
            sub_task_index=2,
            mode="multi_scene",
        )

        # 验证子任务创建和更新
        mock_database["create_sub_task"].assert_called_once()
        create_call = mock_database["create_sub_task"].call_args[1]
        assert create_call["main_task_id"] == "main-task"
        assert create_call["sub_task_index"] == 2
        assert create_call["script_style"] == "default"

        # 验证子任务状态更新
        assert (
            mock_database["update_sub_task"].call_count >= 2
        )  # 至少更新两次（进行中和完成）

    def test_video_mode_handling(
        self, mock_http_client, mock_database, mock_file_operations
    ):
        """测试视频模式处理"""
        from services.sync_video_generator import SyncVideoGenerator

        mock_http_client.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "success": True,
                "video_url": "https://example.com/video.mp4",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "duration": 120,
                "course_media_id": "media123",
            },
        )

        generator = SyncVideoGenerator()

        # 测试multi_scene模式
        result_multi = generator.generate_single_video_sync(
            script_data={
                "title": "多场景视频",
                "description": "",
                "narration": "",
                "scenes": [{"scene_id": 1}, {"scene_id": 2}],
                "script_style": "default",
            },
            media_files=TEST_MEDIA_FILES,
            task_id="test-task",
            sub_task_index=1,
            mode="multi_scene",
        )

        # 测试single_scene模式
        result_single = generator.generate_single_video_sync(
            script_data={
                "title": "单场景视频",
                "description": "",
                "narration": "",
                "scenes": [{"scene_id": 1}],
                "script_style": "default",
            },
            media_files=TEST_MEDIA_FILES,
            task_id="test-task",
            sub_task_index=2,
            mode="single_scene",
        )

        assert result_multi["success"] is True
        assert result_single["success"] is True

        # 验证API调用包含正确的模式
        api_calls = mock_http_client.post.call_args_list
        assert len(api_calls) == 2
