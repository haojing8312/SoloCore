"""
认证相关的Pydantic模型
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    is_active: bool = Field(True, description="是否激活")
    timezone: str = Field("UTC", description="时区")
    language: str = Field("zh-CN", description="语言偏好")

    @validator("username")
    def validate_username(cls, v):
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError("用户名只能包含字母、数字、下划线和短横线")
        return v.lower()


class UserCreate(UserBase):
    """用户创建模型"""

    password: str = Field(..., min_length=8, max_length=100, description="密码")
    confirm_password: str = Field(..., description="确认密码")

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("密码确认不匹配")
        return v

    @validator("password")
    def validate_password(cls, v):
        # 简单的密码强度验证
        if len(v) < 8:
            raise ValueError("密码至少需要8个字符")
        if not any(c.isupper() for c in v):
            raise ValueError("密码需要包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码需要包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码需要包含至少一个数字")
        return v


class UserUpdate(BaseModel):
    """用户更新模型"""

    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """用户响应模型"""

    id: UUID
    is_superuser: bool
    is_verified: bool
    avatar_url: Optional[str]
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """数据库中的用户模型（包含敏感信息）"""

    hashed_password: str
    token_version: int


class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")
    device_info: Optional[str] = Field(None, max_length=200, description="设备信息")


class LoginResponse(BaseModel):
    """登录响应模型"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新Token请求模型"""

    refresh_token: str = Field(..., description="刷新Token")


class TokenResponse(BaseModel):
    """Token响应模型"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class PasswordChangeRequest(BaseModel):
    """密码修改请求模型"""

    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")
    confirm_new_password: str = Field(..., description="确认新密码")

    @validator("confirm_new_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("新密码确认不匹配")
        return v

    @validator("new_password")
    def validate_password(cls, v):
        # 复用UserCreate的密码验证逻辑
        if len(v) < 8:
            raise ValueError("密码至少需要8个字符")
        if not any(c.isupper() for c in v):
            raise ValueError("密码需要包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码需要包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码需要包含至少一个数字")
        return v


class PasswordResetRequest(BaseModel):
    """密码重置请求模型"""

    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""

    token: str = Field(..., description="重置Token")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")
    confirm_new_password: str = Field(..., description="确认新密码")

    @validator("confirm_new_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("新密码确认不匹配")
        return v


class EmailVerificationRequest(BaseModel):
    """邮箱验证请求模型"""

    email: EmailStr = Field(..., description="邮箱地址")


class EmailVerificationConfirm(BaseModel):
    """邮箱验证确认模型"""

    token: str = Field(..., description="验证Token")


class UserStatsResponse(BaseModel):
    """用户统计响应模型"""

    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_videos_generated: int
    total_storage_used: int  # 字节数


class APIKeyResponse(BaseModel):
    """API Key响应模型（如果需要API Key功能）"""

    key: str
    name: str
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool
