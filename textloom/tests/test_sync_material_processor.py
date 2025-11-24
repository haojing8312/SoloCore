"""
测试同步素材处理器
验证 processors/sync_material_processor.py 的核心功能
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from tests.conftest import TEST_CONTENT, TEST_MEDIA_FILES


class TestSyncMaterialProcessor:
    """测试同步素材处理器"""

    def test_initialization(self, temp_workspace):
        """测试初始化"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)
        assert processor.workspace_dir == temp_workspace
        assert hasattr(processor, "http_client")
        assert hasattr(processor, "logger")

    def test_extract_content_from_markdown(self, temp_workspace, temp_file):
        """测试从Markdown文件提取内容"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试内容提取
        content = processor._extract_content_from_file_sync(temp_file)

        # 验证提取的内容
        assert "测试文档标题" in content
        assert "章节1" in content
        assert "章节2" in content
        assert len(content) > 0

    def test_extract_urls_from_content(self, temp_workspace):
        """测试从内容中提取URL"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        test_content = """
        # 测试文档
        
        这里有一张图片：![图片](https://example.com/image1.jpg)
        
        还有一个视频：<video src="https://example.com/video1.mp4"></video>
        
        以及一个链接：[链接](https://example.com/page.html)
        """

        # 测试URL提取
        urls = processor._extract_urls_from_content_sync(test_content)

        # 验证提取结果
        assert len(urls) >= 2  # 至少应该提取到图片和视频URL

        # 检查是否包含预期的URL
        image_urls = [
            url for url in urls if url["url"] == "https://example.com/image1.jpg"
        ]
        video_urls = [
            url for url in urls if url["url"] == "https://example.com/video1.mp4"
        ]

        assert len(image_urls) == 1
        assert len(video_urls) == 1
        assert image_urls[0]["type"] == "image"
        assert video_urls[0]["type"] == "video"

    @patch(
        "processors.sync_material_processor.SyncMaterialProcessor._download_file_sync"
    )
    @patch("processors.sync_material_processor.sync_create_media_item")
    def test_download_and_organize_files(
        self, mock_create_media, mock_download, temp_workspace
    ):
        """测试文件下载和组织"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 设置mock返回值
        mock_download.return_value = {
            "success": True,
            "local_path": "/test/path/image1.jpg",
            "file_size": 1024,
            "content_type": "image/jpeg",
        }
        mock_create_media.return_value = {"id": "test-media-1"}

        urls = [
            {
                "url": "https://example.com/image1.jpg",
                "type": "image",
                "context": "测试图片",
            },
            {
                "url": "https://example.com/video1.mp4",
                "type": "video",
                "context": "测试视频",
            },
        ]

        # 测试下载和组织
        result = processor._download_and_organize_files_sync(urls, "test-task-1")

        # 验证结果
        assert isinstance(result, list)
        assert len(result) == 2  # 两个文件都应该被处理

        # 验证mock调用
        assert mock_download.call_count == 2
        assert mock_create_media.call_count == 2

    @patch("utils.sync_clients.get_sync_http_client")
    def test_download_file_success(self, mock_get_client, temp_workspace):
        """测试文件下载成功场景"""
        from processors.sync_material_processor import SyncMaterialProcessor

        # 设置mock HTTP客户端
        mock_client = Mock()
        mock_client.get.return_value = b"fake image data"
        mock_get_client.return_value = mock_client

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试文件下载
        result = processor._download_file_sync(
            url="https://mmbiz.qpic.cn/mmbiz_png/1nQW9CyuwRyWq9JAedgWfoZCsREr3XOP8tOJuduicvickGK8EvvxR1WJm3Ta1XKQvmtV7m45Oiamg2tnxHbyOX4hg/640?wx_fmt=png&from=appmsg",
            filename="test.jpg",
            subfolder="images",
        )

        # 验证结果
        assert result["success"] is True
        assert "local_path" in result
        assert result["file_size"] == 15  # len(b"fake image data")
        assert "image" in result["content_type"]

        # 验证HTTP客户端调用
        mock_client.get.assert_called_once_with(
            "https://mmbiz.qpic.cn/mmbiz_png/1nQW9CyuwRyWq9JAedgWfoZCsREr3XOP8tOJuduicvickGK8EvvxR1WJm3Ta1XKQvmtV7m45Oiamg2tnxHbyOX4hg/640?wx_fmt=png&from=appmsg"
        )

    @patch("utils.sync_clients.get_sync_http_client")
    def test_download_file_failure(self, mock_get_client, temp_workspace):
        """测试文件下载失败场景"""
        from processors.sync_material_processor import SyncMaterialProcessor

        # 设置mock HTTP客户端返回None（下载失败）
        mock_client = Mock()
        mock_client.get.return_value = None
        mock_get_client.return_value = mock_client

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试文件下载失败
        result = processor._download_file_sync(
            url="https://example.com/test.jpg", filename="test.jpg", subfolder="images"
        )

        # 验证失败处理
        assert result["success"] is False
        assert "error" in result

    def test_detect_content_type(self, temp_workspace):
        """测试内容类型检测"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试不同URL的内容类型检测
        test_cases = [
            ("https://example.com/image.jpg", "image"),
            ("https://example.com/image.png", "image"),
            ("https://example.com/video.mp4", "video"),
            ("https://example.com/video.avi", "video"),
            ("https://example.com/unknown.txt", "unknown"),
        ]

        for url, expected_type in test_cases:
            content_type = processor._detect_content_type_sync(url, b"fake data")
            assert expected_type in content_type.lower()

    def test_generate_safe_filename(self, temp_workspace):
        """测试安全文件名生成"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试不同URL的文件名生成
        test_cases = [
            ("https://example.com/test image.jpg", "test_image.jpg"),
            ("https://example.com/测试图片.png", "png"),  # 应该生成安全的文件名
            ("https://example.com/video?param=1", "video"),
            ("https://example.com/path/file.mp4", "file.mp4"),
        ]

        for url, expected_part in test_cases:
            filename = processor._generate_safe_filename_sync(url)
            assert isinstance(filename, str)
            assert len(filename) > 0
            # 文件名应该不包含特殊字符
            assert not any(
                char in filename
                for char in ["/", "\\", "?", "<", ">", ":", "*", "|", '"']
            )

    def test_process_materials_sync_success_real_file(self, temp_workspace):
        """测试完整的素材处理流程成功场景 - 使用真实马斯克文件"""
        import os

        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 使用真实的马斯克文件
        musk_file = "test/马斯克都在夸的独立开发者PieterLevels.md"

        # 确保文件存在
        assert os.path.exists(musk_file), f"测试文件不存在: {musk_file}"

        # 测试完整流程（不使用mock，进行真实测试）
        result = processor.process_materials_sync(
            source_file=musk_file,
            task_id="test-musk-task-1",
            workspace_dir=temp_workspace,
        )

        # 验证结果
        assert (
            result["success"] is True
        ), f"处理失败: {result.get('error', 'Unknown error')}"
        assert "extracted_content" in result
        assert "media_files" in result
        assert "content" in result
        assert len(result["content"]) > 0, "内容不能为空"

        # 验证提取的内容包含关键信息
        content = result["content"]
        assert "马斯克" in content or "Pieter Levels" in content, "内容应包含关键词"

        # 验证提取到了图片（马斯克文件包含多个图片）
        assert (
            result["total_urls"] > 0
        ), f"应该提取到媒体URL，实际提取到: {result['total_urls']}"

        print(f"✅ 成功提取内容长度: {len(content)} 字符")
        print(f"✅ 成功提取媒体URL数量: {result['total_urls']}")
        print(f"✅ 成功处理媒体文件数量: {result['downloaded']}")

    def test_real_article_processing_with_preserved_workspace(self, temp_workspace):
        """测试真实文章处理并保留工作空间目录用于后续素材分析测试"""
        import os
        from pathlib import Path
        from uuid import uuid4

        from processors.sync_material_processor import SyncMaterialProcessor

        # 创建项目下的工作空间目录
        project_root = Path.cwd()
        test_workspace_dir = project_root / "test_workspace"
        test_workspace_dir.mkdir(exist_ok=True)

        # 创建带时间戳的具体工作空间
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        persistent_workspace = test_workspace_dir / f"material_test_{timestamp}"
        persistent_workspace.mkdir(exist_ok=True)

        processor = SyncMaterialProcessor(str(persistent_workspace))

        # 使用真实的马斯克文件
        musk_file = "test/马斯克都在夸的独立开发者PieterLevels.md"

        # 确保文件存在
        assert os.path.exists(musk_file), f"测试文件不存在: {musk_file}"

        # 生成有效的UUID作为task_id
        task_id = str(uuid4())

        # 进行真实的文章处理（不使用mock，下载真实媒体文件）
        result = processor.process_article(
            article_path=musk_file,
            task_id=task_id,
            max_images=10,  # 处理更多图片用于后续分析
            max_videos=3,
        )

        # 验证处理结果
        assert (
            result["success_count"] > 0
        ), f"应该成功处理一些媒体文件，实际成功: {result['success_count']}"
        assert len(result["content"]) > 0, "内容不能为空"

        # 验证文件实际下载到了工作空间
        image_dir = processor.image_dir
        downloaded_images = (
            list(image_dir.glob("*.jpg"))
            + list(image_dir.glob("*.png"))
            + list(image_dir.glob("*.gif"))
        )

        assert (
            len(downloaded_images) > 0
        ), f"应该有下载的图片文件，工作目录: {image_dir}"

        # 输出重要信息，保留工作空间
        print(f"\n🎯 重要：工作空间保留在: {persistent_workspace}")
        print(f"📁 图片目录: {image_dir}")
        print(f"📊 处理结果统计:")
        print(f"   - 提取内容长度: {len(result['content'])} 字符")
        print(f"   - 总媒体项目: {result['total_media_items']}")
        print(f"   - 成功处理: {result['success_count']}")
        print(f"   - 失败数量: {result['failed_count']}")
        print(f"   - 下载的图片文件数: {len(downloaded_images)}")
        print(f"   - 图片文件列表:")
        for img in downloaded_images[:5]:  # 显示前5个文件
            print(f"     * {img.name}")

        # 将工作空间路径写入项目根目录文件，供后续测试使用
        workspace_info_file = project_root / "test_workspace_info.txt"
        with open(workspace_info_file, "w", encoding="utf-8") as f:
            f.write(f"WORKSPACE_PATH={persistent_workspace}\n")
            f.write(f"IMAGE_DIR={image_dir}\n")
            f.write(f"DOWNLOADED_IMAGES_COUNT={len(downloaded_images)}\n")
            f.write(f"SUCCESS_COUNT={result['success_count']}\n")
            f.write(f"TASK_ID={task_id}\n")
            f.write(f"TIMESTAMP={timestamp}\n")

        print(f"📝 工作空间信息已保存到: {workspace_info_file}")

        return {
            "workspace_path": str(persistent_workspace),
            "image_dir": str(image_dir),
            "downloaded_count": len(downloaded_images),
            "result": result,
        }

    @patch(
        "processors.sync_material_processor.SyncMaterialProcessor._extract_content_from_file_sync"
    )
    @patch(
        "processors.sync_material_processor.SyncMaterialProcessor._extract_urls_from_content_sync"
    )
    @patch(
        "processors.sync_material_processor.SyncMaterialProcessor._download_and_organize_files_sync"
    )
    def test_process_materials_sync_success(
        self,
        mock_download,
        mock_extract_urls,
        mock_extract_content,
        temp_workspace,
        temp_file,
    ):
        """测试完整的素材处理流程成功场景"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 设置mock返回值
        mock_extract_content.return_value = TEST_CONTENT
        mock_extract_urls.return_value = [
            {"url": "https://example.com/test.jpg", "type": "image", "context": "测试"}
        ]
        mock_download.return_value = TEST_MEDIA_FILES

        # 测试完整流程
        result = processor.process_materials_sync(
            source_file=temp_file, task_id="test-task-1", workspace_dir=temp_workspace
        )

        # 验证结果
        assert result["success"] is True
        assert "extracted_content" in result
        assert "media_files" in result
        assert len(result["media_files"]) == len(TEST_MEDIA_FILES)

        # 验证各阶段都被调用
        mock_extract_content.assert_called_once()
        mock_extract_urls.assert_called_once()
        mock_download.assert_called_once()

    @patch(
        "processors.sync_material_processor.SyncMaterialProcessor._extract_content_from_file_sync"
    )
    def test_process_materials_sync_failure(
        self, mock_extract_content, temp_workspace, temp_file
    ):
        """测试素材处理流程失败场景"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 设置mock抛出异常
        mock_extract_content.side_effect = Exception("File read error")

        # 测试失败场景
        result = processor.process_materials_sync(
            source_file=temp_file, task_id="test-task-1", workspace_dir=temp_workspace
        )

        # 验证失败处理
        assert result["success"] is False
        assert "error" in result
        assert "File read error" in result["error"]

    def test_concurrent_download_limitation(self, temp_workspace):
        """测试并发下载限制"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 验证并发限制配置
        assert hasattr(processor, "download_semaphore")
        # 默认应该有并发限制（比如最多5个并发下载）
        assert processor.download_semaphore._value <= 10

    def test_workspace_directory_creation(self, temp_workspace):
        """测试工作空间目录创建"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试目录创建
        test_subdir = os.path.join(temp_workspace, "test_materials", "images")
        processor._ensure_directory_exists_sync(test_subdir)

        # 验证目录被创建
        assert os.path.exists(test_subdir)
        assert os.path.isdir(test_subdir)

    def test_url_validation(self, temp_workspace):
        """测试URL验证"""
        from processors.sync_material_processor import SyncMaterialProcessor

        processor = SyncMaterialProcessor(temp_workspace)

        # 测试有效URL
        valid_urls = [
            "https://example.com/image.jpg",
            "http://test.com/video.mp4",
            "https://cdn.example.com/path/to/file.png",
        ]

        for url in valid_urls:
            assert processor._is_valid_url_sync(url) is True

        # 测试无效URL
        invalid_urls = ["not-a-url", "ftp://example.com/file.txt", "", None]

        for url in invalid_urls:
            assert processor._is_valid_url_sync(url) is False
