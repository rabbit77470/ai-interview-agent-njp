from ..base import BaseSchema, BaseResponseSchema
from pydantic import EmailStr
from datetime import datetime
from typing import Optional

#继承了baseschema，#接受前端发来的邮箱和密码，请求DTO
class Login(BaseSchema):
    """管理员登录请求"""
    email: EmailStr #EmailStr 是 Pydantic 内置邮箱专用类型；
    password: str

#接收前端传来的访问令牌和刷新令牌和令牌类型
class Token(BaseSchema):
    """登录/刷新后返回的令牌对"""
    access_token: str
    refresh_token: str
    token_type: str

#接受前端的刷新令牌
class RefreshToken(BaseSchema):
    """刷新令牌请求"""
    refresh_token: str

#接收刷新令牌
class Logout(BaseSchema):
    """登出请求"""
    refresh_token: str

#响应管理员信息（角色，邮箱，姓名，是否可用）
class AdminInfo(BaseResponseSchema):
    """当前管理员信息响应"""
    role: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
