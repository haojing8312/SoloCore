"""
认证相关工具函数
"""

from typing import Optional

from config import settings


def verify_internal_token(token: Optional[str]) -> bool:
    """
    验证内部测试Token

    Args:
        token: 请求头中的token

    Returns:
        是否验证通过
    """
    if not settings.internal_test_token:
        # 如果没有配置内部测试token，则不允许访问
        return False

    return token == settings.internal_test_token
