"""
测试配置和固定装置(fixtures)
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

# 测试用的模拟数据
TEST_CONTENT = """
# 测试文档标题

这是一个测试用的文档内容，用于验证系统功能。

![测试图片](https://example.com/test.jpg)

## 章节1
这里是一些测试内容。

## 章节2  
更多测试内容。
"""

TEST_MEDIA_FILES = [
    {
        "id": "test-media-1",
        "url": "https://example.com/test1.jpg",
        "filename": "test1.jpg",
        "file_type": "image",
        "file_size": 1024,
    },
    {
        "id": "test-media-2",
        "url": "https://example.com/test2.mp4",
        "filename": "test2.mp4",
        "file_type": "video",
        "file_size": 2048,
    },
]

TEST_ANALYSIS_RESULTS = [
    {
        "media_item_id": "test-media-1",
        "ai_description": "一张展示科技产品的图片",
        "key_objects": ["手机", "科技", "创新"],
        "analysis_status": "completed",
    },
    {
        "media_item_id": "test-media-2",
        "ai_description": "一个产品演示视频",
        "key_objects": ["演示", "界面", "操作"],
        "analysis_status": "completed",
    },
]

TEST_SCRIPT_RESULT = {
    "title": "测试视频标题",
    "description": "测试视频描述",
    "narration": "这是测试用的旁白内容。",
    "scenes": [
        {
            "scene_id": 1,
            "narration": "开场旁白",
            "material_id": "test-media-1",
            "duration": 5.0,
            "scene_type": "opening",
        },
        {
            "scene_id": 2,
            "narration": "主要内容旁白",
            "material_id": "test-media-2",
            "duration": 10.0,
            "scene_type": "main",
        },
    ],
    "script_style": "default",
}

TEST_VIDEO_RESULT = {
    "success": True,
    "video_url": "https://example.com/test-video.mp4",
    "thumbnail_url": "https://example.com/test-thumb.jpg",
    "duration": 60,
    "course_media_id": "test-course-123",
    "status": "completed",
}


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = tempfile.mkdtemp(prefix="textloom_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_file():
    """创建临时文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(TEST_CONTENT)
        temp_file_path = f.name

    yield temp_file_path

    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        # 文件已被删除，无需处理
        pass
    except OSError as e:
        # 文件系统权限或其他OS级别错误
        print(f"Warning: 无法删除临时文件 {temp_file_path}: {e}")
    except Exception as e:
        # 其他未预期错误
        print(f"Error: 删除临时文件时发生未预期错误 {temp_file_path}: {e}")


@pytest.fixture
def mock_openai_client():
    """模拟OpenAI客户端"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = (
        "这是一张科技产品的图片，展示了最新的创新技术。"
    )
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """模拟Gemini客户端"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = '{"title": "测试视频", "narration": "测试旁白", "scenes": []}'
    mock_client.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_http_client():
    """模拟HTTP客户端"""
    mock_client = Mock()
    mock_client.get.return_value = b"fake image data"
    mock_client.post_json.return_value = {
        "success": True,
        "course_media_id": "test-123",
    }
    mock_client.get_json.return_value = {
        "success": True,
        "result": {"status": 2, "merge_video": "test-video.mp4"},
    }
    return mock_client


@pytest.fixture
def mock_database():
    """模拟数据库操作"""
    db_mock = Mock()

    # 模拟任务相关操作
    db_mock.sync_get_task_by_id.return_value = {
        "id": "test-task-1",
        "status": "processing",
        "progress": 50,
    }
    db_mock.sync_update_task_status.return_value = True
    db_mock.sync_update_task_progress.return_value = True

    # 模拟媒体项操作
    db_mock.sync_create_media_item.return_value = {"id": "test-media-1"}
    db_mock.sync_create_material_analysis.return_value = {"id": "test-analysis-1"}

    # 模拟脚本操作
    db_mock.sync_create_script_content.return_value = {"id": "test-script-1"}
    db_mock.sync_get_persona_by_id.return_value = {
        "id": 1,
        "name": "测试人设",
        "description": "测试用人设",
    }

    return db_mock


class MockProgressCallback:
    """模拟进度回调"""

    def __init__(self):
        self.calls = []

    def __call__(self, progress: int, stage: str, message: str):
        self.calls.append(
            {
                "progress": progress,
                "stage": stage,
                "message": message,
                "timestamp": datetime.utcnow(),
            }
        )
