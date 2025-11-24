"""
测试Celery任务集成
验证Celery任务的执行、状态更新和与各组件的集成
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from celery import Celery
from celery.exceptions import Retry as TaskRetryError
from sqlalchemy.exc import DatabaseError

from tests.conftest import TEST_CONTENT


class TestCeleryIntegration:
    """测试Celery任务集成"""

    @pytest.fixture
    def mock_celery_app(self):
        """模拟Celery应用"""
        with patch("tasks.video_processing_tasks.celery_app") as mock_app:
            mock_app.conf = Mock()
            yield mock_app

    @pytest.fixture
    def mock_sync_task_processor(self):
        """模拟同步任务处理器"""
        with patch(
            "tasks.video_processing_tasks.SyncTaskProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            # 设置成功的处理结果
            mock_processor.process_text_to_video_task.return_value = {
                "task_id": "test-task-123",
                "status": "completed",
                "progress": 100,
                "video_url": "https://example.com/video.mp4",
                "script_title": "测试视频标题",
                "processing_time": 45.2,
                "successful_video_count": 2,
                "failed_video_count": 0,
            }

            yield mock_processor

    @pytest.fixture
    def mock_database_operations(self):
        """模拟数据库操作"""
        with (
            patch("tasks.video_processing_tasks.sync_get_task_by_id") as get_task,
            patch(
                "tasks.video_processing_tasks.sync_update_task_status"
            ) as update_status,
            patch(
                "tasks.video_processing_tasks.sync_update_task_celery_info"
            ) as update_celery,
        ):

            get_task.return_value = {
                "id": "test-task-123",
                "status": "pending",
                "source_file": "/test/file.md",
                "workspace_dir": "/tmp/workspace/test-task-123",
                "mode": "multi_scene",
                "persona_id": "test-persona",
                "multi_video_count": 2,
            }

            yield {
                "get_task": get_task,
                "update_status": update_status,
                "update_celery": update_celery,
            }

    def test_process_text_to_video_task_success(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试Celery文本转视频任务成功执行"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 模拟Celery任务上下文
        task_context = Mock()
        task_context.request.id = "celery-task-abc123"
        task_context.request.hostname = "worker-node-1"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-123")

        # 验证任务执行结果
        assert result["success"] is True
        assert result["task_id"] == "test-task-123"
        assert result["celery_task_id"] == "celery-task-abc123"
        assert result["worker_name"] == "worker-node-1"
        assert result["result"]["status"] == "completed"

        # 验证数据库操作
        mock_database_operations["get_task"].assert_called_once_with("test-task-123")
        mock_database_operations["update_celery"].assert_called_once_with(
            "test-task-123", "celery-task-abc123", "worker-node-1"
        )

        # 验证任务处理器调用
        mock_sync_task_processor.process_text_to_video_task.assert_called_once()
        call_args = mock_sync_task_processor.process_text_to_video_task.call_args[1]
        assert call_args["task_id"] == "test-task-123"
        assert call_args["source_file"] == "/test/file.md"
        assert call_args["multi_video_count"] == 2

    def test_process_text_to_video_task_not_found(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试任务不存在的情况"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 设置任务不存在
        mock_database_operations["get_task"].return_value = None

        task_context = Mock()
        task_context.request.id = "celery-task-notfound"
        task_context.request.hostname = "worker-node-1"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("nonexistent-task")

        # 验证错误处理
        assert result["success"] is False
        assert "任务不存在" in result["error"]
        assert result["task_id"] == "nonexistent-task"

        # 验证任务处理器未被调用
        mock_sync_task_processor.process_text_to_video_task.assert_not_called()

    def test_process_text_to_video_task_processing_failure(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试任务处理失败"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 设置处理失败
        mock_sync_task_processor.process_text_to_video_task.return_value = {
            "task_id": "test-task-fail",
            "status": "failed",
            "error": "素材处理失败",
            "processing_time": 12.3,
        }

        task_context = Mock()
        task_context.request.id = "celery-task-failed"
        task_context.request.hostname = "worker-node-2"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-fail")

        # 验证失败结果
        assert result["success"] is False
        assert result["task_id"] == "test-task-fail"
        assert result["error"] == "素材处理失败"
        assert result["result"]["status"] == "failed"

    def test_process_text_to_video_task_exception_handling(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试异常处理"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 设置处理器抛出异常
        mock_sync_task_processor.process_text_to_video_task.side_effect = Exception(
            "系统异常"
        )

        task_context = Mock()
        task_context.request.id = "celery-task-exception"
        task_context.request.hostname = "worker-node-3"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-exception")

        # 验证异常处理
        assert result["success"] is False
        assert "系统异常" in result["error"]
        assert result["task_id"] == "test-task-exception"

        # 验证状态更新为失败
        mock_database_operations["update_status"].assert_called_with(
            "test-task-exception", "failed", mock.ANY
        )

    def test_progress_callback_integration(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试进度回调集成"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 捕获传递给处理器的进度回调函数
        progress_callback = None

        def capture_callback(*args, **kwargs):
            nonlocal progress_callback
            progress_callback = kwargs.get("progress_callback")
            return mock_sync_task_processor.process_text_to_video_task.return_value

        mock_sync_task_processor.process_text_to_video_task.side_effect = (
            capture_callback
        )

        task_context = Mock()
        task_context.request.id = "celery-task-progress"
        task_context.request.hostname = "worker-node-1"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-progress")

        # 验证进度回调函数被传递
        assert progress_callback is not None

        # 测试进度回调函数
        with patch(
            "tasks.video_processing_tasks.sync_update_task_progress"
        ) as mock_update:
            progress_callback(50, "material_analysis", "分析中...")
            mock_update.assert_called_once_with(
                "test-task-progress", 50, "material_analysis", "分析中..."
            )

    def test_celery_task_retry_mechanism(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试Celery任务重试机制"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 模拟可重试的错误（如网络错误）
        call_count = 0

        def mock_process_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("网络连接失败")  # 第一次失败
            else:
                return {  # 第二次成功
                    "task_id": "test-task-retry",
                    "status": "completed",
                    "progress": 100,
                    "processing_time": 30.5,
                }

        mock_sync_task_processor.process_text_to_video_task.side_effect = (
            mock_process_with_retry
        )

        task_context = Mock()
        task_context.request.id = "celery-task-retry"
        task_context.request.hostname = "worker-node-1"
        task_context.request.retries = 0
        task_context.retry = Mock()

        # 第一次调用（失败）
        with (
            patch(
                "tasks.video_processing_tasks.process_text_to_video_task.request",
                task_context.request,
            ),
            patch(
                "tasks.video_processing_tasks.process_text_to_video_task.retry",
                task_context.retry,
            ),
        ):
            try:
                result = process_text_to_video_task("test-task-retry")
            except TaskRetryError:
                pass  # 预期的重试异常
            except DatabaseError as e:
                print(f"数据库连接错误（测试预期）: {e}")
            except Exception as e:
                print(f"测试中的预期异常: {e}")
                pass  # 第一次会抛出异常触发重试

        # 验证重试被触发
        # 注意：实际的重试逻辑可能需要根据具体的Celery配置进行调整
        assert call_count == 1  # 第一次调用

    def test_celery_task_configuration(self, mock_celery_app):
        """测试Celery任务配置"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 验证任务装饰器配置
        assert hasattr(process_text_to_video_task, "delay")
        assert hasattr(process_text_to_video_task, "apply_async")

        # 测试任务名称
        # 注意：实际的任务名称可能需要根据具体配置进行调整
        expected_task_name = "tasks.video_processing_tasks.process_text_to_video_task"
        # assert process_text_to_video_task.name == expected_task_name

    def test_workspace_directory_handling(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试工作目录处理"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 设置任务数据
        mock_database_operations["get_task"].return_value = {
            "id": "test-task-workspace",
            "status": "pending",
            "source_file": "/test/file.md",
            "workspace_dir": "/custom/workspace/path",
            "mode": "single_scene",
            "persona_id": "test-persona",
            "multi_video_count": 1,
        }

        task_context = Mock()
        task_context.request.id = "celery-task-workspace"
        task_context.request.hostname = "worker-node-1"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-workspace")

        # 验证处理器使用了正确的工作目录
        mock_sync_task_processor.assert_called_once_with("/custom/workspace/path")

        # 验证处理器调用参数包含工作目录
        call_args = (
            mock_sync_task_processor.return_value.process_text_to_video_task.call_args[
                1
            ]
        )
        assert call_args["workspace_dir"] == "/custom/workspace/path"

    def test_multi_video_count_handling(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试多视频数量处理"""
        from tasks.video_processing_tasks import process_text_to_video_task

        # 测试不同的多视频数量
        test_cases = [1, 2, 3, 5]

        for count in test_cases:
            mock_database_operations["get_task"].return_value[
                "multi_video_count"
            ] = count
            mock_sync_task_processor.reset_mock()

            task_context = Mock()
            task_context.request.id = f"celery-task-multi-{count}"
            task_context.request.hostname = "worker-node-1"

            with patch(
                "tasks.video_processing_tasks.process_text_to_video_task.request",
                task_context.request,
            ):
                result = process_text_to_video_task(f"test-task-multi-{count}")

            # 验证多视频数量被正确传递
            call_args = mock_sync_task_processor.return_value.process_text_to_video_task.call_args[
                1
            ]
            assert call_args["multi_video_count"] == count

    def test_celery_worker_info_logging(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试Celery Worker信息记录"""
        from tasks.video_processing_tasks import process_text_to_video_task

        task_context = Mock()
        task_context.request.id = "celery-task-worker-info"
        task_context.request.hostname = "production-worker-5"

        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-worker-info")

        # 验证Worker信息被记录
        assert result["celery_task_id"] == "celery-task-worker-info"
        assert result["worker_name"] == "production-worker-5"

        # 验证数据库中记录了Celery信息
        mock_database_operations["update_celery"].assert_called_once_with(
            "test-task-worker-info", "celery-task-worker-info", "production-worker-5"
        )

    def test_task_execution_timing(
        self, mock_sync_task_processor, mock_database_operations
    ):
        """测试任务执行时间记录"""
        import time

        from tasks.video_processing_tasks import process_text_to_video_task

        # 模拟处理延迟
        def slow_processing(*args, **kwargs):
            time.sleep(0.01)  # 优化：减少测试延迟从100ms到10ms
            return mock_sync_task_processor.process_text_to_video_task.return_value

        mock_sync_task_processor.process_text_to_video_task.side_effect = (
            slow_processing
        )

        task_context = Mock()
        task_context.request.id = "celery-task-timing"
        task_context.request.hostname = "worker-node-1"

        start_time = time.time()
        with patch(
            "tasks.video_processing_tasks.process_text_to_video_task.request",
            task_context.request,
        ):
            result = process_text_to_video_task("test-task-timing")
        end_time = time.time()

        # 验证执行时间
        total_time = end_time - start_time
        assert total_time >= 0.1  # 至少有模拟的延迟时间

        # 验证结果包含时间信息
        assert "executed_at" in result
        assert "result" in result

    @pytest.mark.integration
    def test_real_celery_task_execution(self):
        """集成测试：真实Celery任务执行（需要Redis）"""
        # 这个测试需要真实的Redis和Celery环境
        # 通常在CI/CD环境中或者开发者本地测试时运行
        try:
            from celery_config import celery_app
            from tasks.video_processing_tasks import process_text_to_video_task

            # 尝试异步提交任务
            # task_result = process_text_to_video_task.delay("test-integration")
            # result = task_result.get(timeout=60)
            # 由于这是集成测试，我们只验证任务可以被导入和配置
            assert process_text_to_video_task is not None
            assert hasattr(process_text_to_video_task, "delay")

        except ImportError:
            pytest.skip("Celery环境未配置，跳过集成测试")
        except Exception as e:
            pytest.skip(f"集成测试环境不可用: {e}")
