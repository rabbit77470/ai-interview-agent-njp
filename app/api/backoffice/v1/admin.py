from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, transaction
from app.schemas.backoffice.admin import AdminCreate, AdminResponse, AdminUpdate, AdminChangePassword, ResetPassword
from app.services.backoffice.admin import admin_service
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.paginator import Paginator
from app.exceptions.http_exceptions import APIException


router = APIRouter()


# ==================== 创建管理员 ====================
@router.post("", response_model=AdminResponse)
async def create_admin(
    admin_data: AdminCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """创建新管理员（仅超管可操作）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=400,
            message="权限不足，仅超级管理员可创建"
        )

    async with transaction(db):
        result = await admin_service.create_admin(db, admin_data)
        return ApiResponse.success(data=result)


# ==================== 管理员列表 ====================
@router.get("")
async def list_admins(
    page: int = 1,
    per_page: int = 10,
    email: str = None,
    sort_by: str = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """管理员列表（仅超管可查看）

    Args:
        page: 页码，从 1 开始
        per_page: 每页条数
        email: 按邮箱模糊筛选
        sort_by: 排序字段，支持 email 或 created_at
        sort_order: 排序方向，asc 或 desc
    """
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=400,
            message="权限不足，仅超级管理员可查看"
        )

    # 构建查询
    query = await admin_service.get_admins_query(db, email=email, sort_by=sort_by, sort_order=sort_order)

    # 分页
    paginator = Paginator(query, db)
    result = await paginator.paginate(page, per_page)
    result = result.map(AdminResponse)

    return result.response()


# ==================== 管理员详情 ====================
@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """管理员详情（超管可看任何人，普通管理员只能看自己）"""
    if not current_admin.role == "superadmin" and current_admin.id != admin_id:
        raise APIException(
            status_code=403,
            message="权限不足"
        )

    result = await admin_service.get_admin(db, admin_id)
    if not result:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="管理员不存在"
        )

    return ApiResponse.success(data=result)


# ==================== 更新管理员 ====================
@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_data: AdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """更新管理员信息（超管可更新任何人，普通管理员只能更新自己）"""
    if not current_admin.role == "superadmin" and current_admin.id != admin_id:
        raise APIException(
            status_code=403,
            message="权限不足"
        )

    # 普通管理员不能把自己改成超管
    if not current_admin.role == "superadmin" and admin_data.role == "superadmin":
        raise APIException(
            status_code=403,
            message="无权修改超级管理员状态"
        )

    async with transaction(db):
        result = await admin_service.update_admin(db, admin_id, admin_data.model_dump(exclude_unset=True))
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="管理员不存在"
            )

        return ApiResponse.success_without_data()


# ==================== 删除管理员 ====================
@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除管理员（仅超管可操作，不能删自己）"""
    if not current_admin.role == "superadmin":
        raise APIException(
            status_code=403,
            message="权限不足，仅超级管理员可删除"
        )

    # 不能删除自己
    if current_admin.id == admin_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="不能删除自己"
        )

    async with transaction(db):
        result = await admin_service.delete_admin(db, admin_id)
        if not result:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="管理员不存在"
            )

        return ApiResponse.success_without_data()


# ==================== 修改密码 ====================
@router.post("/{admin_id}/change-password")
async def change_password(
    admin_id: int,
    password_data: AdminChangePassword,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """修改自己的密码（需要旧密码验证）"""
    if current_admin.id != admin_id:
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="只能修改自己的密码"
        )

    async with transaction(db):
        result = await admin_service.change_password(
            db,
            admin_id,
            password_data.current_password,
            password_data.new_password
        )

        return ApiResponse.success_without_data()


# ==================== 重置密码 ====================
@router.post("/{admin_id}/reset-password")
async def reset_password(
    admin_id: int,
    password_data: ResetPassword,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """重置密码（超管或本人可操作，不需要旧密码）"""
    if current_admin.role != "superadmin" and current_admin.id != admin_id:
        raise APIException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="权限不足"
        )

    async with transaction(db):
        result = await admin_service.reset_password(
            db,
            admin_id,
            password_data.password
        )

        return ApiResponse.success_without_data()
