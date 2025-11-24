"""
测试同步客户端
验证 utils/sync_clients.py 中的 OpenAI、Gemini、HTTP 客户端功能
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from tests.conftest import TEST_CONTENT


class TestSyncOpenAIClient:
    """测试同步OpenAI客户端"""

    @patch("utils.sync_clients.OpenAI")
    def test_openai_client_initialization(self, mock_openai_class):
        """测试OpenAI客户端初始化"""
        from utils.sync_clients import SyncOpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # 测试初始化
        sync_client = SyncOpenAIClient()

        # 验证初始化调用
        mock_openai_class.assert_called_once()
        assert sync_client.client == mock_client

    @patch("utils.sync_clients.OpenAI")
    def test_analyze_image_success(self, mock_openai_class):
        """测试图片分析成功场景"""
        from utils.sync_clients import SyncOpenAIClient

        # 设置mock响应
        mock_client = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()

        mock_message.content = "这是一张展示科技产品的图片，包含手机和创新技术元素。"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # 创建客户端并测试
        sync_client = SyncOpenAIClient()
        result = sync_client.analyze_image(
            image_url="https://example.com/test.jpg", context="测试上下文"
        )

        # 验证结果
        assert result == "这是一张展示科技产品的图片，包含手机和创新技术元素。"

        # 验证API调用
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] is not None
        assert len(call_args[1]["messages"]) > 0

    @patch("utils.sync_clients.OpenAI")
    def test_analyze_image_with_retry(self, mock_openai_class):
        """测试图片分析重试机制"""
        from utils.sync_clients import SyncOpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # 第一次调用失败，第二次成功
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "重试后的分析结果"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_client.chat.completions.create.side_effect = [
            Exception("Rate limit exceeded"),
            mock_response,
        ]

        sync_client = SyncOpenAIClient()
        result = sync_client.analyze_image(
            image_url="https://example.com/test.jpg", context="测试上下文"
        )

        # 验证重试成功
        assert result == "重试后的分析结果"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("utils.sync_clients.OpenAI")
    def test_analyze_image_failure(self, mock_openai_class):
        """测试图片分析失败场景"""
        from utils.sync_clients import SyncOpenAIClient

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # 模拟持续失败
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        sync_client = SyncOpenAIClient()
        result = sync_client.analyze_image(
            image_url="https://example.com/test.jpg", context="测试上下文"
        )

        # 验证失败处理
        assert result is None
        assert mock_client.chat.completions.create.call_count == 3  # 默认重试3次


class TestSyncGeminiClient:
    """测试同步Gemini客户端"""

    @patch("utils.sync_clients.genai")
    def test_gemini_client_initialization(self, mock_genai):
        """测试Gemini客户端初始化"""
        from utils.sync_clients import SyncGeminiClient

        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # 测试初始化
        sync_client = SyncGeminiClient()

        # 验证初始化
        mock_genai.configure.assert_called_once()
        mock_genai.GenerativeModel.assert_called_once()
        assert sync_client.model == mock_model

    @patch("utils.sync_clients.genai")
    def test_generate_script_success(self, mock_genai):
        """测试脚本生成成功场景"""
        from utils.sync_clients import SyncGeminiClient

        # 设置mock响应
        mock_model = Mock()
        mock_response = Mock()
        test_script = '{"title": "测试视频", "narration": "测试旁白内容", "scenes": []}'
        mock_response.text = test_script
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # 创建客户端并测试
        sync_client = SyncGeminiClient()
        result = sync_client.generate_script(
            prompt="生成一个测试脚本", max_tokens=1000, temperature=0.7
        )

        # 验证结果
        assert result == test_script

        # 验证API调用
        mock_model.generate_content.assert_called_once_with("生成一个测试脚本")

    @patch("utils.sync_clients.genai")
    def test_generate_script_with_retry(self, mock_genai):
        """测试脚本生成重试机制"""
        from utils.sync_clients import SyncGeminiClient

        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # 第一次失败，第二次成功
        mock_response = Mock()
        mock_response.text = "重试后的脚本内容"

        mock_model.generate_content.side_effect = [
            Exception("Service temporarily unavailable"),
            mock_response,
        ]

        sync_client = SyncGeminiClient()
        result = sync_client.generate_script(
            prompt="生成一个测试脚本", max_tokens=1000, temperature=0.7
        )

        # 验证重试成功
        assert result == "重试后的脚本内容"
        assert mock_model.generate_content.call_count == 2

    @patch("utils.sync_clients.genai")
    def test_generate_script_failure(self, mock_genai):
        """测试脚本生成失败场景"""
        from utils.sync_clients import SyncGeminiClient

        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        # 模拟持续失败
        mock_model.generate_content.side_effect = Exception("API Error")

        sync_client = SyncGeminiClient()
        result = sync_client.generate_script(
            prompt="生成一个测试脚本", max_tokens=1000, temperature=0.7
        )

        # 验证失败处理
        assert result is None
        assert mock_model.generate_content.call_count == 3

    @patch("utils.sync_clients.genai")
    def test_generate_script_empty_response(self, mock_genai):
        """当Gemini返回无text候选时，应返回None并不抛异常（由上层决定失败语义）"""
        from utils.sync_clients import SyncGeminiClient

        mock_model = Mock()
        # 模拟返回对象没有可用text
        mock_response = Mock()
        mock_response.text = None
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        client = SyncGeminiClient()
        result = client.generate_script(prompt="p")

        assert result is None
        mock_model.generate_content.assert_called()


class TestSyncHTTPClient:
    """测试同步HTTP客户端"""

    def test_http_client_initialization(self):
        """测试HTTP客户端初始化"""
        from utils.sync_clients import SyncHTTPClient

        client = SyncHTTPClient()

        assert client.session is not None
        assert client.max_retries > 0
        assert client.retry_delay > 0
        assert hasattr(client, "timeout")

    @patch("requests.Session.get")
    def test_get_request_success(self, mock_get):
        """测试GET请求成功场景"""
        from utils.sync_clients import SyncHTTPClient

        # 设置mock响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test image data"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # 测试GET请求
        client = SyncHTTPClient()
        result = client.get("https://example.com/test.jpg")

        # 验证结果
        assert result == b"test image data"

        # 验证调用
        mock_get.assert_called_once_with(
            "https://example.com/test.jpg", timeout=30, headers=None, params=None
        )

    @patch("requests.Session.get")
    def test_get_request_with_retry(self, mock_get):
        """测试GET请求重试机制"""
        from utils.sync_clients import SyncHTTPClient

        # 第一次失败，第二次成功
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"retry success data"
        mock_response.raise_for_status.return_value = None

        mock_get.side_effect = [
            requests.RequestException("Connection timeout"),
            mock_response,
        ]

        client = SyncHTTPClient()
        result = client.get("https://example.com/test.jpg")

        # 验证重试成功
        assert result == b"retry success data"
        assert mock_get.call_count == 2

    @patch("requests.Session.post")
    def test_post_json_success(self, mock_post):
        """测试POST JSON请求成功场景"""
        from utils.sync_clients import SyncHTTPClient

        # 设置mock响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "id": "test-123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # 测试POST请求
        client = SyncHTTPClient()
        test_data = {"key": "value"}
        result = client.post_json("https://api.example.com/submit", data=test_data)

        # 验证结果
        assert result == {"success": True, "id": "test-123"}

        # 验证调用
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.example.com/submit"
        assert call_args[1]["json"] == test_data

    @patch("requests.Session.get")
    def test_get_json_success(self, mock_get):
        """测试GET JSON请求成功场景"""
        from utils.sync_clients import SyncHTTPClient

        # 设置mock响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "completed", "result": "success"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # 测试GET JSON请求
        client = SyncHTTPClient()
        result = client.get_json(
            "https://api.example.com/status", params={"id": "test-123"}
        )

        # 验证结果
        assert result == {"status": "completed", "result": "success"}

        # 验证调用
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.example.com/status"
        assert call_args[1]["params"] == {"id": "test-123"}

    @patch("requests.Session.get")
    def test_request_failure_handling(self, mock_get):
        """测试请求失败处理"""
        from utils.sync_clients import SyncHTTPClient

        # 模拟持续失败
        mock_get.side_effect = requests.RequestException("Network error")

        client = SyncHTTPClient()
        result = client.get("https://example.com/test.jpg")

        # 验证失败处理
        assert result is None
        assert mock_get.call_count == 3  # 默认重试3次


class TestClientFactories:
    """测试客户端工厂函数"""

    @patch("utils.sync_clients.SyncOpenAIClient")
    def test_get_sync_openai_client_singleton(self, mock_client_class):
        """测试OpenAI客户端单例模式"""
        from utils.sync_clients import get_sync_openai_client

        mock_instance = Mock()
        mock_client_class.return_value = mock_instance

        # 多次调用应该返回同一个实例
        client1 = get_sync_openai_client()
        client2 = get_sync_openai_client()

        assert client1 == client2
        mock_client_class.assert_called_once()  # 只初始化一次

    @patch("utils.sync_clients.SyncGeminiClient")
    def test_get_sync_gemini_client_singleton(self, mock_client_class):
        """测试Gemini客户端单例模式"""
        from utils.sync_clients import get_sync_gemini_client

        mock_instance = Mock()
        mock_client_class.return_value = mock_instance

        # 多次调用应该返回同一个实例
        client1 = get_sync_gemini_client()
        client2 = get_sync_gemini_client()

        assert client1 == client2
        mock_client_class.assert_called_once()  # 只初始化一次

    @patch("utils.sync_clients.SyncHTTPClient")
    def test_get_sync_http_client_singleton(self, mock_client_class):
        """测试HTTP客户端单例模式"""
        from utils.sync_clients import get_sync_http_client

        mock_instance = Mock()
        mock_client_class.return_value = mock_instance

        # 多次调用应该返回同一个实例
        client1 = get_sync_http_client()
        client2 = get_sync_http_client()

        assert client1 == client2
        mock_client_class.assert_called_once()  # 只初始化一次
