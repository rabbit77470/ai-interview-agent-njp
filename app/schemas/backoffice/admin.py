from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import EmailStr, Field
from typing import Optional


# ==================== 请求 Schema ====================

class AdminBase(BaseSchema):
    """管理员公共字段"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


class AdminCreate(AdminBase):
    """创建管理员（多一个密码字段）"""
    password: str


class AdminUpdate(BaseSchema):
    """更新管理员（全部可选，传什么改什么）"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class AdminChangePassword(BaseSchema):
    """修改自己的密码（需要旧密码验证）"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class ResetPassword(BaseSchema):
    """重置密码（不需要旧密码，超管或本人操作）"""
    password: str = Field(..., min_length=8)


# ==================== 响应 Schema ====================

@add_padded_id()
class AdminResponse(BaseResponseSchema, AdminBase):
    """管理员响应（带 padded_id 自动补零）"""
    is_active: bool
    padded_id: Optional[str] = None

    @classmethod
    def model_validate(cls, admin):
        return super().model_validate(admin)
