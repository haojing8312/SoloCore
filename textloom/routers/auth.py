"""
认证路由
提供用户注册、登录、JWT Token管理等功能
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from models.auth_models import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserStatsResponse,
    UserUpdate,
)
from models.db_connection import get_db_session
from models.db_models import RefreshTokenTable, TaskTable, UserTable
from utils.auth_middleware import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
    verify_refresh_token,
)
from utils.jwt_auth import get_password_hash, jwt_manager, verify_password
from utils.api_key_auth import APIKeyAuth

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_by_username_or_email(
    username_or_email: str, db_session: Session
) -> UserTable:
    """根据用户名或邮箱获取用户"""
    # 尝试按用户名查找
    stmt = select(UserTable).where(UserTable.username == username_or_email.lower())
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # 尝试按邮箱查找
        stmt = select(UserTable).where(UserTable.email == username_or_email.lower())
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

    return user


async def create_refresh_token_record(
    user_id: UUID,
    jti: str,
    token: str,
    device_info: str = None,
    ip_address: str = None,
    db_session: Session = None,
):
    """创建刷新Token记录"""
    expires_at = datetime.utcnow() + timedelta(days=7)  # 7天过期
    token_hash = jwt_manager.get_token_hash(token)

    refresh_token_record = RefreshTokenTable(
        user_id=user_id,
        jti=jti,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address,
    )

    db_session.add(refresh_token_record)
    await db_session.commit()


# 公开用户注册已禁用 - API用户由管理员后台创建
# @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
# async def register_user(user_data: UserCreate):
#     """用户注册 - 已禁用，仅允许管理员创建API用户"""
#     raise HTTPException(
#         status_code=status.HTTP_403_FORBIDDEN, 
#         detail="公开注册已禁用，请联系管理员获取API访问权限"
#     )


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request):
    """用户登录"""
    async with get_db_session() as db_session:
        # 获取用户
        user = await get_user_by_username_or_email(login_data.username, db_session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
            )

        # 验证密码
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
            )

        # 检查用户状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户账户已被禁用"
            )

        # 生成Token对
        tokens = jwt_manager.create_token_pair(
            user_id=user.id,
            username=user.username,
            email=user.email,
            is_superuser=user.is_superuser,
            token_version=user.token_version,
        )

        # 获取设备信息和IP
        device_info = login_data.device_info or request.headers.get(
            "User-Agent", "Unknown"
        )
        ip_address = request.client.host if request.client else None

        # 保存刷新Token
        jti = jwt_manager.extract_jti_from_token(tokens.refresh_token)
        await create_refresh_token_record(
            user_id=user.id,
            jti=jti,
            token=tokens.refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            db_session=db_session,
        )

        # 更新最后登录时间
        stmt = (
            update(UserTable)
            .where(UserTable.id == user.id)
            .values(last_login_at=datetime.utcnow())
        )
        await db_session.execute(stmt)
        await db_session.commit()

        # 刷新用户数据
        await db_session.refresh(user)

        logger.info(f"用户登录成功: {user.username}")

        return LoginResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=UserResponse.from_orm(user),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(refresh_data: RefreshTokenRequest):
    """刷新访问Token"""
    # 验证刷新Token
    token_data = await verify_refresh_token(refresh_data.refresh_token)

    async with get_db_session() as db_session:
        # 获取用户信息
        stmt = select(UserTable).where(UserTable.id == token_data.user_id)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
            )

        # 生成新的访问Token
        new_access_token = jwt_manager.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            is_superuser=user.is_superuser,
            token_version=user.token_version,
        )

        logger.info(f"Token刷新成功: {user.username}")

        return TokenResponse(
            access_token=new_access_token,
            expires_in=jwt_manager.access_token_expire_minutes * 60,
        )


@router.post("/logout")
async def logout(
    refresh_data: RefreshTokenRequest,
    current_user: UserResponse = Depends(get_current_active_user),
):
    """用户登出（撤销刷新Token）"""
    async with get_db_session() as db_session:
        # 提取JTI
        jti = jwt_manager.extract_jti_from_token(refresh_data.refresh_token)
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="无效的刷新Token"
            )

        # 撤销刷新Token
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.jti == jti,
                RefreshTokenTable.user_id == current_user.id,
            )
            .values(is_revoked=True)
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="刷新Token不存在"
            )

        logger.info(f"用户登出成功: {current_user.username}")

        return {"message": "登出成功"}


@router.post("/logout-all")
async def logout_all_devices(
    current_user: UserResponse = Depends(get_current_active_user),
):
    """从所有设备登出（撤销所有刷新Token并增加token版本）"""
    async with get_db_session() as db_session:
        # 撤销所有刷新Token
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.user_id == current_user.id,
                RefreshTokenTable.is_revoked == False,
            )
            .values(is_revoked=True)
        )

        await db_session.execute(stmt)

        # 增加token版本（使所有现有的访问Token失效）
        stmt = (
            update(UserTable)
            .where(UserTable.id == current_user.id)
            .values(token_version=UserTable.token_version + 1)
        )

        await db_session.execute(stmt)
        await db_session.commit()

        logger.info(f"用户从所有设备登出: {current_user.username}")

        return {"message": "已从所有设备登出"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user),
):
    """获取当前用户信息"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_active_user),
):
    """更新当前用户信息"""
    async with get_db_session() as db_session:
        # 构建更新数据
        update_data = {}
        for field, value in user_update.dict(exclude_unset=True).items():
            if field == "email" and value:
                # 检查邮箱是否已被其他用户使用
                stmt = select(UserTable).where(
                    UserTable.email == value.lower(), UserTable.id != current_user.id
                )
                result = await db_session.execute(stmt)
                if result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邮箱已被其他用户使用",
                    )
                update_data["email"] = value.lower()
            elif value is not None:
                update_data[field] = value

        if update_data:
            update_data["updated_at"] = datetime.utcnow()

            stmt = (
                update(UserTable)
                .where(UserTable.id == current_user.id)
                .values(**update_data)
            )
            await db_session.execute(stmt)
            await db_session.commit()

        # 获取更新后的用户信息
        stmt = select(UserTable).where(UserTable.id == current_user.id)
        result = await db_session.execute(stmt)
        updated_user = result.scalar_one()

        return UserResponse.from_orm(updated_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: UserResponse = Depends(get_current_active_user),
):
    """修改密码"""
    async with get_db_session() as db_session:
        # 获取用户当前密码哈希
        stmt = select(UserTable.hashed_password).where(UserTable.id == current_user.id)
        result = await db_session.execute(stmt)
        current_hashed_password = result.scalar_one()

        # 验证当前密码
        if not verify_password(password_data.current_password, current_hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误"
            )

        # 更新密码和token版本（使现有token失效）
        new_hashed_password = get_password_hash(password_data.new_password)

        stmt = (
            update(UserTable)
            .where(UserTable.id == current_user.id)
            .values(
                hashed_password=new_hashed_password,
                token_version=UserTable.token_version + 1,
                updated_at=datetime.utcnow(),
            )
        )

        await db_session.execute(stmt)

        # 撤销所有刷新Token
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.user_id == current_user.id,
                RefreshTokenTable.is_revoked == False,
            )
            .values(is_revoked=True)
        )

        await db_session.execute(stmt)
        await db_session.commit()

        logger.info(f"用户修改密码成功: {current_user.username}")

        return {"message": "密码修改成功，请重新登录"}


@router.get("/sessions")
async def get_user_sessions(
    current_user: UserResponse = Depends(get_current_active_user),
):
    """获取用户的活跃会话列表"""
    async with get_db_session() as db_session:
        stmt = (
            select(RefreshTokenTable)
            .where(
                RefreshTokenTable.user_id == current_user.id,
                RefreshTokenTable.is_revoked == False,
                RefreshTokenTable.expires_at > datetime.utcnow(),
            )
            .order_by(RefreshTokenTable.created_at.desc())
        )

        result = await db_session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": session.jti,
                "device_info": session.device_info,
                "ip_address": session.ip_address,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
            }
            for session in sessions
        ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str, current_user: UserResponse = Depends(get_current_active_user)
):
    """撤销指定会话"""
    async with get_db_session() as db_session:
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.jti == session_id,
                RefreshTokenTable.user_id == current_user.id,
            )
            .values(is_revoked=True)
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
            )

        return {"message": "会话已撤销"}


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: UserResponse = Depends(get_current_active_user)):
    """获取用户统计信息"""
    async with get_db_session() as db_session:
        # 统计任务信息
        stmt = select(TaskTable).where(TaskTable.creator_id == str(current_user.id))
        result = await db_session.execute(stmt)
        tasks = result.scalars().all()

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        failed_tasks = len([t for t in tasks if t.status == "failed"])

        # 统计生成的视频数量 - SubVideoTask 已移除，每个任务最多1个视频
        total_videos = 0
        for task in tasks:
            if task.video_url:
                total_videos += 1

        # TODO: 统计存储使用量（需要实现文件大小统计）
        total_storage_used = 0

        return UserStatsResponse(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            total_videos_generated=total_videos,
            total_storage_used=total_storage_used,
        )


# 管理员功能
@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_superuser),
):
    """获取用户列表（管理员）"""
    async with get_db_session() as db_session:
        stmt = (
            select(UserTable)
            .offset(skip)
            .limit(limit)
            .order_by(UserTable.created_at.desc())
        )
        result = await db_session.execute(stmt)
        users = result.scalars().all()

        return [UserResponse.from_orm(user) for user in users]


@router.put("/admin/users/{user_id}/activate")
async def activate_user(
    user_id: UUID, current_user: UserResponse = Depends(get_current_superuser)
):
    """激活用户（管理员）"""
    async with get_db_session() as db_session:
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(is_active=True, updated_at=datetime.utcnow())
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        return {"message": "用户已激活"}


@router.put("/admin/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID, current_user: UserResponse = Depends(get_current_superuser)
):
    """停用用户（管理员）"""
    async with get_db_session() as db_session:
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
            )

        return {"message": "用户已停用"}


# API用户管理接口
@router.post("/admin/api-users")
async def create_api_user(
    username: str = Form(..., description="用户名"),
    email: str = Form(..., description="邮箱"),
    full_name: str = Form(None, description="全名"),
    quota_limit: Optional[int] = Form(None, description="月度API调用配额"),
    current_user: UserResponse = Depends(get_current_superuser),
):
    """创建API用户（管理员）"""
    try:
        user, api_key = await APIKeyAuth.create_api_user(
            username=username,
            email=email,
            full_name=full_name,
            quota_limit=quota_limit,
        )
        
        return {
            "message": "API用户创建成功",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "quota_limit": user.api_quota_limit,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "api_key": api_key,  # 仅在创建时返回明文API Key
            "warning": "请妥善保存API Key，系统不会再次显示完整密钥"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建API用户失败: {e}")
        raise HTTPException(status_code=500, detail="创建API用户失败")


@router.get("/admin/api-users")
async def list_api_users(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_superuser),
):
    """获取API用户列表（管理员）"""
    async with get_db_session() as db_session:
        stmt = (
            select(UserTable)
            .where(UserTable.user_type == "api_user")
            .offset(skip)
            .limit(limit)
            .order_by(UserTable.created_at.desc())
        )
        result = await db_session.execute(stmt)
        users = result.scalars().all()

        return {
            "users": [
                {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "api_key_enabled": user.api_key_enabled,
                    "api_key_preview": f"{user.api_key[:8]}..." if user.api_key else None,
                    "quota_limit": user.api_quota_limit,
                    "quota_used": user.api_quota_used,
                    "quota_reset_at": user.quota_reset_at.isoformat() if user.quota_reset_at else None,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                for user in users
            ],
            "total": len(users),
        }


@router.put("/admin/api-users/{user_id}/quota")
async def update_api_user_quota(
    user_id: UUID,
    quota_limit: Optional[int] = Form(None, description="新的配额限制"),
    current_user: UserResponse = Depends(get_current_superuser),
):
    """更新API用户配额（管理员）"""
    async with get_db_session() as db_session:
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id, UserTable.user_type == "api_user")
            .values(api_quota_limit=quota_limit)
        )
        result = await db_session.execute(stmt)
        await db_session.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="API用户不存在")

        return {"message": "配额更新成功", "new_quota_limit": quota_limit}


@router.post("/admin/api-users/{user_id}/regenerate-key")
async def regenerate_api_key(
    user_id: UUID,
    current_user: UserResponse = Depends(get_current_superuser),
):
    """重新生成API Key（管理员）"""
    new_api_key = await APIKeyAuth.regenerate_api_key(user_id)
    if not new_api_key:
        raise HTTPException(status_code=404, detail="API用户不存在")

    return {
        "message": "API Key重新生成成功",
        "new_api_key": new_api_key,
        "warning": "请妥善保存新的API Key，旧密钥已失效"
    }


@router.put("/admin/api-users/{user_id}/disable")
async def disable_api_user(
    user_id: UUID,
    current_user: UserResponse = Depends(get_current_superuser),
):
    """禁用API用户（管理员）"""
    success = await APIKeyAuth.disable_api_key(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="API用户不存在")

    return {"message": "API用户已禁用"}
