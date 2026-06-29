from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.admin import Admin
from app.schemas.backoffice.admin import AdminCreate, AdminResponse
from app.exceptions.http_exceptions import APIException
from typing import Optional
from fastapi import status
from app.core.security import AuthBase


class AdminService:
    """后台管理员 CRUD 服务"""

    @staticmethod
    async def create_admin(db: AsyncSession, admin_data: AdminCreate) -> AdminResponse:
        """创建新管理员"""
        # 检查邮箱是否已存在
        email_query = select(Admin).where(Admin.email == admin_data.email)
        result = await db.execute(email_query)
        if result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="邮箱已存在"
            )

        # 哈希密码
        hashed_password = AuthBase.hash_token(admin_data.password)

        # 创建管理员
        admin = Admin(
            email=admin_data.email,
            first_name=admin_data.first_name,
            last_name=admin_data.last_name,
            password=hashed_password,
            is_active=admin_data.is_active,
            role="superadmin"
        )

        db.add(admin)
        await db.flush()
        await db.refresh(admin)

        return AdminResponse.model_validate(admin)

    @staticmethod
    async def get_admin(db: AsyncSession, admin_id: int) -> Optional[AdminResponse]:
        """获取管理员详情"""
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()

        if not admin:
            return None

        return AdminResponse.model_validate(admin)

    @staticmethod
    async def get_admin_by_email(db: AsyncSession, email: str) -> Optional[Admin]:
        """通过邮箱获取管理员（返回 ORM 对象，给登录用）"""
        admin_query = select(Admin).where(Admin.email == email)
        result = await db.execute(admin_query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_admins_query(db: AsyncSession, email: str = None, sort_by: str = None, sort_order: str = "desc"):
        """构建管理员列表查询（带筛选和排序），返回 Select 对象供分页器使用"""
        query = select(Admin)

        # 邮箱模糊筛选
        if email:
            query = query.where(Admin.email.ilike(f"%{email}%"))

        # 排序
        if sort_by == "email":
            if sort_order.lower() == "asc":
                query = query.order_by(Admin.email.asc())
            else:
                query = query.order_by(Admin.email.desc())
        else:
            # 默认按创建时间排序
            if sort_order.lower() == "asc":
                query = query.order_by(Admin.created_at.asc())
            else:
                query = query.order_by(Admin.created_at.desc())

        return query

    @staticmethod
    async def update_admin(db: AsyncSession, admin_id: int, admin_data: dict) -> Optional[AdminResponse]:
        """更新管理员信息"""
        # 先确认管理员存在
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()

        if not admin:
            return None

        update_data = {}

        # 邮箱：检查是否与已有邮箱冲突
        if "email" in admin_data and admin_data["email"] != admin.email:
            email_query = select(Admin).where(
                Admin.email == admin_data["email"],
                Admin.id != admin_id
            )
            result = await db.execute(email_query)
            if result.scalar_one_or_none():
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="邮箱已存在"
                )
            update_data["email"] = admin_data["email"]

        # 密码：重新哈希
        if "password" in admin_data:
            update_data["password"] = AuthBase.hash_token(admin_data["password"])

        # 名字
        if "first_name" in admin_data:
            update_data["first_name"] = admin_data["first_name"]

        if "last_name" in admin_data:
            update_data["last_name"] = admin_data["last_name"]

        # 激活状态
        if "is_active" in admin_data:
            update_data["is_active"] = admin_data["is_active"]

        # 执行更新
        if update_data:
            stmt = update(Admin).where(Admin.id == admin_id).values(**update_data)
            await db.execute(stmt)

            # 重新查询更新后的数据
            admin_query = select(Admin).where(Admin.id == admin_id)
            result = await db.execute(admin_query)
            admin = result.scalar_one_or_none()

        return AdminResponse.model_validate(admin)

    @staticmethod
    async def delete_admin(db: AsyncSession, admin_id: int) -> bool:
        """删除管理员（先删关联 token，再删管理员）"""
        # 确认管理员存在
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()

        if not admin:
            return False

        # 先删除关联的 admin_tokens
        from app.models.token import AdminToken
        delete_tokens_stmt = delete(AdminToken).where(AdminToken.admin_id == admin_id)
        await db.execute(delete_tokens_stmt)

        # 删除管理员
        stmt = delete(Admin).where(Admin.id == admin_id)
        await db.execute(stmt)

        return True

    @staticmethod
    async def change_password(db: AsyncSession, admin_id: int, current_password: str, new_password: str) -> bool:
        """修改自己的密码（需要验证旧密码）"""
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()

        if not admin:
            return False

        # 验证旧密码
        if not AuthBase.verify_token_hash(current_password, admin.password):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="当前密码不正确"
            )

        # 更新密码
        hashed_password = AuthBase.hash_token(new_password)
        stmt = update(Admin).where(Admin.id == admin_id).values(password=hashed_password)
        await db.execute(stmt)

        return True

    @staticmethod
    async def reset_password(db: AsyncSession, admin_id: int, new_password: str) -> bool:
        """重置密码（不需要旧密码，超管或本人操作）"""
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()

        if not admin:
            return False

        # 直接更新密码
        hashed_password = AuthBase.hash_token(new_password)
        stmt = update(Admin).where(Admin.id == admin_id).values(password=hashed_password)
        await db.execute(stmt)

        return True


# 服务单例
admin_service = AdminService()
