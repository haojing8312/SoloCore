"""
测试同步任务处理器
验证 services/sync_task_processor.py 的完整4阶段处理流程
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from models.script_generation import ScriptStyle
from tests.conftest import TEST_ANALYSIS_RESULTS, TEST_CONTENT, TEST_MEDIA_FILES


class TestSyncTaskProcessor:
    """测试同步任务处理器"""

    @pytest.fixture
    def mock_components(self):
        """模拟所有组件"""
        with (
            patch(
                "services.sync_task_processor.SyncMaterialProcessor"
            ) as material_proc,
            patch(
                "services.sync_task_processor.SyncMaterialAnalyzer"
            ) as material_analyzer,
            patch("services.sync_task_processor.SyncScriptGenerator") as script_gen,
            patch("services.sync_task_processor.SyncVideoGenerator") as video_gen,
        ):

            # 设置模拟返回值
            material_proc.return_value.process_materials_sync.return_value = {
                "success": True,
                "media_files": TEST_MEDIA_FILES,
                "extracted_content": TEST_CONTENT,
            }

            material_analyzer.return_value.analyze_materials_sync.return_value = {
                "success": True,
                "material_context": {"images": ["test.jpg"]},
                "analysis_results": TEST_ANALYSIS_RESULTS,
            }

            script_gen.return_value.generate_multi_scripts_sync.return_value = {
                "success": True,
                "successful_results": [
                    {
                        "script_id": "script1",
                        "title": "测试视频1",
                        "description": "描述1",
                        "narration": "旁白1",
                        "scenes": [],
                        "script_style": "default",
                    },
                    {
                        "script_id": "script2",
                        "title": "测试视频2",
                        "description": "描述2",
                        "narration": "旁白2",
                        "scenes": [],
                        "script_style": "product_geek",
                    },
                ],
                "failed_results": [],
            }

            video_gen.return_value.generate_multiple_videos_sync.return_value = [
                {
                    "success": True,
                    "sub_task_id": "sub1",
                    "sub_task_index": 1,
                    "script_style": "default",
                    "video_url": "https://example.com/video1.mp4",
                    "thumbnail_url": "https://example.com/thumb1.jpg",
                    "duration": 120,
                    "course_media_id": "media1",
                },
                {
                    "success": True,
                    "sub_task_id": "sub2",
                    "sub_task_index": 2,
                    "script_style": "product_geek",
                    "video_url": "https://example.com/video2.mp4",
                    "thumbnail_url": "https://example.com/thumb2.jpg",
                    "duration": 130,
                    "course_media_id": "media2",
                },
            ]

            yield {
                "material_processor": material_proc.return_value,
                "material_analyzer": material_analyzer.return_value,
                "script_generator": script_gen.return_value,
                "video_generator": video_gen.return_value,
            }

    @pytest.fixture
    def mock_database_operations(self):
        """模拟数据库操作"""
        with (
            patch(
                "services.sync_task_processor.sync_update_task_status"
            ) as update_status,
            patch(
                "services.sync_task_processor.sync_update_task_progress"
            ) as update_progress,
            patch(
                "services.sync_task_processor.sync_update_task_multi_video_results"
            ) as update_results,
        ):
            yield {
                "update_status": update_status,
                "update_progress": update_progress,
                "update_results": update_results,
            }

    @pytest.fixture
    def progress_callback_mock(self):
        """模拟进度回调"""
        return Mock()

    def test_complete_text_to_video_task_success(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试完整文本转视频任务成功"""
        from services.sync_task_processor import SyncTaskProcessor

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-task-123",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=2,
            progress_callback=progress_callback_mock,
        )

        # 验证结果
        assert result["task_id"] == "test-task-123"
        assert result["status"] == "completed"
        assert result["progress"] == 100
        assert result["successful_video_count"] == 2
        assert result["failed_video_count"] == 0
        assert result["material_count"] == len(TEST_MEDIA_FILES)
        assert result["script_count"] == 2
        assert result["video_url"] == "https://example.com/video1.mp4"

        # 验证4个阶段都被执行
        mock_components[
            "material_processor"
        ].process_materials_sync.assert_called_once()
        mock_components["material_analyzer"].analyze_materials_sync.assert_called_once()
        mock_components[
            "script_generator"
        ].generate_multi_scripts_sync.assert_called_once()
        mock_components[
            "video_generator"
        ].generate_multiple_videos_sync.assert_called_once()

        # 验证进度回调
        assert progress_callback_mock.call_count >= 4  # 至少4次进度更新
        progress_calls = [call.args for call in progress_callback_mock.call_args_list]

        # 验证进度递增
        progress_values = [call[0] for call in progress_calls]
        assert progress_values == sorted(progress_values)  # 进度应该是递增的
        assert progress_values[-1] == 100  # 最后进度应该是100

        # 验证数据库操作
        mock_database_operations["update_status"].assert_called()
        mock_database_operations["update_progress"].assert_called()
        mock_database_operations["update_results"].assert_called_once()

    def test_material_processing_failure(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试素材处理阶段失败"""
        from services.sync_task_processor import SyncTaskProcessor

        # 设置素材处理失败
        mock_components["material_processor"].process_materials_sync.return_value = {
            "success": False,
            "error": "文件读取失败",
        }

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-task-fail",
            source_file="/invalid/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=1,
            progress_callback=progress_callback_mock,
        )

        # 验证失败结果
        assert result["task_id"] == "test-task-fail"
        assert result["status"] == "failed"
        assert "文件读取失败" in result["error"]

        # 验证只执行了素材处理阶段
        mock_components[
            "material_processor"
        ].process_materials_sync.assert_called_once()
        mock_components["material_analyzer"].analyze_materials_sync.assert_not_called()
        mock_components[
            "script_generator"
        ].generate_multi_scripts_sync.assert_not_called()
        mock_components[
            "video_generator"
        ].generate_multiple_videos_sync.assert_not_called()

        # 验证失败状态更新
        mock_database_operations["update_status"].assert_called_with(
            "test-task-fail", "failed", mock.ANY
        )

    def test_material_analysis_failure(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试素材分析阶段失败"""
        from services.sync_task_processor import SyncTaskProcessor

        # 设置素材分析失败
        mock_components["material_analyzer"].analyze_materials_sync.return_value = {
            "success": False,
            "error": "AI分析服务不可用",
        }

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-task-analysis-fail",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="single_scene",
            persona_id="test-persona",
            multi_video_count=1,
            progress_callback=progress_callback_mock,
        )

        # 验证失败结果
        assert result["status"] == "failed"
        assert "AI分析服务不可用" in result["error"]

        # 验证执行到分析阶段后停止
        mock_components[
            "material_processor"
        ].process_materials_sync.assert_called_once()
        mock_components["material_analyzer"].analyze_materials_sync.assert_called_once()
        mock_components[
            "script_generator"
        ].generate_multi_scripts_sync.assert_not_called()

    def test_script_generation_failure(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试脚本生成阶段失败"""
        from services.sync_task_processor import SyncTaskProcessor

        # 设置脚本生成失败
        mock_components["script_generator"].generate_multi_scripts_sync.return_value = {
            "success": True,
            "successful_results": [],  # 没有成功的脚本
            "failed_results": ["脚本生成失败1", "脚本生成失败2"],
        }

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-task-script-fail",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=2,
            progress_callback=progress_callback_mock,
        )

        # 验证失败结果
        assert result["status"] == "failed"
        assert "脚本生成失败" in result["error"]

        # 验证执行到脚本生成阶段后停止
        mock_components[
            "video_generator"
        ].generate_multiple_videos_sync.assert_not_called()

    def test_video_generation_partial_failure(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试视频生成阶段部分失败"""
        from services.sync_task_processor import SyncTaskProcessor

        # 设置部分视频生成失败
        mock_components[
            "video_generator"
        ].generate_multiple_videos_sync.return_value = [
            {
                "success": True,
                "sub_task_id": "sub1",
                "sub_task_index": 1,
                "script_style": "default",
                "video_url": "https://example.com/video1.mp4",
                "thumbnail_url": "https://example.com/thumb1.jpg",
                "duration": 120,
                "course_media_id": "media1",
            },
            {
                "success": False,
                "sub_task_id": "sub2",
                "sub_task_index": 2,
                "script_style": "product_geek",
                "error": "视频生成服务超时",
            },
        ]

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-task-partial-fail",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=2,
            progress_callback=progress_callback_mock,
        )

        # 部分成功应该标记为completed
        assert result["status"] == "completed"
        assert result["successful_video_count"] == 1
        assert result["failed_video_count"] == 1
        assert (
            result["video_url"] == "https://example.com/video1.mp4"
        )  # 第一个成功的视频

    def test_video_generation_complete_failure(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试视频生成完全失败"""
        from services.sync_task_processor import SyncTaskProcessor

        # 设置所有视频生成失败
        mock_components[
            "video_generator"
        ].generate_multiple_videos_sync.return_value = [
            {
                "success": False,
                "sub_task_id": "sub1",
                "sub_task_index": 1,
                "error": "服务器错误",
            },
            {
                "success": False,
                "sub_task_id": "sub2",
                "sub_task_index": 2,
                "error": "网络超时",
            },
        ]

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-task-video-fail",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="single_scene",
            persona_id="test-persona",
            multi_video_count=2,
            progress_callback=progress_callback_mock,
        )

        # 所有视频失败应该标记为failed
        assert result["status"] == "failed"
        assert result["progress"] == 75  # 脚本生成完成但视频失败
        assert result["successful_video_count"] == 0
        assert result["failed_video_count"] == 2
        assert result["video_url"] is None

    def test_multi_video_count_script_styles(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试多视频数量对应的脚本风格"""
        from services.sync_task_processor import SyncTaskProcessor

        processor = SyncTaskProcessor("/tmp/workspace")

        # 测试单视频
        processor.process_text_to_video_task(
            task_id="test-single",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=1,
            progress_callback=progress_callback_mock,
        )

        # 验证只生成一个默认风格脚本
        script_call = mock_components[
            "script_generator"
        ].generate_multi_scripts_sync.call_args
        styles = script_call[1]["styles"]
        assert len(styles) == 1
        assert styles[0] == ScriptStyle.DEFAULT

        # 重置mock
        mock_components["script_generator"].reset_mock()

        # 测试双视频
        processor.process_text_to_video_task(
            task_id="test-double",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=2,
            progress_callback=progress_callback_mock,
        )

        # 验证生成默认和产品极客两种风格
        script_call = mock_components[
            "script_generator"
        ].generate_multi_scripts_sync.call_args
        styles = script_call[1]["styles"]
        assert len(styles) == 2
        assert ScriptStyle.DEFAULT in styles
        assert ScriptStyle.PRODUCT_GEEK in styles

    def test_topic_extraction(self):
        """测试主题提取功能"""
        from services.sync_task_processor import SyncTaskProcessor

        processor = SyncTaskProcessor("/tmp/workspace")

        # 测试Markdown标题提取
        content_with_title = "# 这是主标题\n\n这是内容..."
        topic = processor._extract_topic_from_content_sync(content_with_title)
        assert topic == "这是主标题"

        # 测试无标题情况
        content_without_title = "这是一段没有标题的内容，应该截取前面的部分作为主题。"
        topic = processor._extract_topic_from_content_sync(content_without_title)
        assert len(topic) <= 53  # 应该截取并添加...
        assert topic.startswith("这是一段没有标题的内容")

        # 测试空内容
        topic = processor._extract_topic_from_content_sync("")
        assert topic == "视频内容"

    def test_progress_callback_sequence(
        self, mock_components, mock_database_operations
    ):
        """测试进度回调序列"""
        from services.sync_task_processor import SyncTaskProcessor

        progress_calls = []

        def track_progress(progress, stage, description):
            progress_calls.append((progress, stage, description))

        processor = SyncTaskProcessor("/tmp/workspace")

        processor.process_text_to_video_task(
            task_id="test-progress",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=2,
            progress_callback=track_progress,
        )

        # 验证进度回调序列
        assert len(progress_calls) >= 4

        # 验证阶段顺序
        stages = [call[1] for call in progress_calls]
        expected_stages = [
            "material_processing",
            "material_analysis",
            "script_generation",
            "completed",
        ]
        for expected_stage in expected_stages:
            assert expected_stage in stages

        # 验证进度递增
        progress_values = [call[0] for call in progress_calls]
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

    def test_processing_time_tracking(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试处理时间跟踪"""
        import time

        from services.sync_task_processor import SyncTaskProcessor

        # 模拟处理延迟
        def slow_process(*args, **kwargs):
            time.sleep(0.01)  # 优化：减少测试延迟从100ms到10ms
            return mock_components[
                "material_processor"
            ].process_materials_sync.return_value

        mock_components["material_processor"].process_materials_sync.side_effect = (
            slow_process
        )

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-timing",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=1,
            progress_callback=progress_callback_mock,
        )

        # 验证处理时间被记录
        assert "processing_time" in result
        assert result["processing_time"] > 0.09  # 应该至少有延迟时间
        assert "completed_at" in result

    def test_exception_handling_and_cleanup(
        self, mock_components, mock_database_operations, progress_callback_mock
    ):
        """测试异常处理和清理"""
        from services.sync_task_processor import SyncTaskProcessor

        # 模拟处理过程中发生异常
        mock_components["material_analyzer"].analyze_materials_sync.side_effect = (
            Exception("模拟系统异常")
        )

        processor = SyncTaskProcessor("/tmp/workspace")

        result = processor.process_text_to_video_task(
            task_id="test-exception",
            source_file="/test/file.md",
            workspace_dir="/tmp/workspace",
            mode="multi_scene",
            persona_id="test-persona",
            multi_video_count=1,
            progress_callback=progress_callback_mock,
        )

        # 验证异常被正确处理
        assert result["status"] == "failed"
        assert "模拟系统异常" in result["error"]
        assert "processing_time" in result
        assert "failed_at" in result

        # 验证失败状态被更新到数据库
        mock_database_operations["update_status"].assert_called_with(
            "test-exception", "failed", mock.ANY
        )

        # 验证进度回调被调用
        progress_callback_mock.assert_called_with(0, "failed", mock.ANY)
