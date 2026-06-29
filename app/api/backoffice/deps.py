from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.security import AuthBase
from app.models.admin import Admin
from app.core.config import settings
#认证依赖注入
# 指定登录接口 URL，Swagger 文档的 "Authorize" 按钮会跳转到此接口
#可依赖对象（Depends 依赖），注入接口时会自动执行逻辑：
#这是一个令牌提取器
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/backoffice/auth/login")


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """从请求头提取 Bearer Token → 验 JWT → 查 DB → 返回 Admin 对象"""
    # 1. 验证 JWT（签名、过期、scope=backoffice），验证前端传过来的token
    payload = AuthBase.verify_token(token, scope="backoffice")
    if not payload:
        raise HTTPException(
            status_code=403,
            detail="身份验证凭据无效",
            #标准协议头部，告诉前端需要携带 Bearer 类型 token 重新登录。
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 2. 从 JWT 中取出 admin_id，查数据库
    admin_id = payload.get("sub")
    admin_query = select(Admin).where(Admin.id == int(admin_id))
    result = await db.execute(admin_query)
    admin = result.scalar_one_or_none()
    # 3. 管理员不存在或已停用
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用或不存在")
    return admin
