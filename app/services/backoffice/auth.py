from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta, UTC
from app.models.admin import Admin
from app.models.token import AdminToken
from app.core.security import AuthBase
from app.core.config import settings
from app.db.session import transaction
from app.exceptions.http_exceptions import APIException

#后台管理认证服务，继承了生成JWT令牌的工具类
class BackofficeAuthService(AuthBase):
    """后台管理认证服务，继承 AuthBase 复用 JWT 工具方法"""

#静态异步方法authenticate_admin
    @staticmethod#验证管理员，传入异步数据库会话，所有查询必须传入。传入前端登录提交的邮箱账号密码
    async def authenticate_admin(db: AsyncSession, email: str, password: str) -> Optional[Admin]:
        """根据邮箱查管理员，并验证密码；成功返回 Admin，失败返回 None"""
        #先做一个查询语句
        admin_query = select(Admin).where(Admin.email == email)
        #执行查询语句返回row对象
        result = await db.execute(admin_query)
        #返回匹配到的第一条数据orm对象
        admin = result.scalar_one_or_none()

#如果查询结果为空，或账号存在但是密码校验错误
        if not admin or not admin.verify_password(password):
            return None
        #校验通过，返回管理员orm对象
        return admin

#管理员登录：传入异步会话，邮箱账号密码
    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> Dict:
        """管理员登录：认证 → 吊销旧令牌 → 签发新 JWT 对 → 哈希存库 → 返回令牌"""
        async with transaction(db): #异步数据库事务上下文管理器
            #异步调用管理员验证方法，返回adminorm对象
            admin = await BackofficeAuthService.authenticate_admin(db, email, password)
            if not admin:
                raise APIException(status_code=400, message="邮箱或密码错误")
            if not admin.is_active:
                raise APIException(status_code=400, message="账号已被禁用")

            # 将该管理员所有旧的活跃刷新令牌标记为无效
#更新：同一个管理员在别处登录后，之前设备的刷新令牌全部作废，旧设备无法再通过 refresh_token 续期 access_token，实现同一账号仅一台设备在线。
            stmt = update(AdminToken).where(
                (AdminToken.admin_id == admin.id) &
                (AdminToken.is_active == True)
            ).values(is_active=False)
            await db.execute(stmt)

            # 生成新的 access_token（scope=backoffice，30分钟）和 refresh_token（scope=refresh，7天）
            access_token = AuthBase.create_access_token(
                str(admin.id), #做载荷
                scope="backoffice", #做载荷
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            #生成刷新令牌
            refresh_token = AuthBase.create_refresh_token(str(admin.id))

            # 将 refresh_token 哈希后存入 admin_tokens 表
            hashed_token = AuthBase.hash_token(refresh_token)
            #实例化一个orm对象
            token_record = AdminToken(
                admin_id=admin.id,
                token=hashed_token,
                expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                is_active=True
            )
            db.add(token_record) #把新令牌记录添加到数据库会话缓冲区
            await db.flush() #把缓冲区数据同步带数据库临时区域，但不提交事务

#登录成功了，给控制层返回两个明文令牌，控制层进行包装返回给前端，前端保存到本地
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
#只要请求头带上这个令牌，服务器就认定持有该字符串的人就是合法用户，不需要额外校验签名外的信息。
                "token_type": "bearer"
            }

#当前端 access_token 短期过期后，前端携带长期有效的 refresh_token 调用该接口，后端校验刷新令牌合法性，校验通过后只生成全新 access_token 返回，不用重新登录输入账号密码。
    @staticmethod #刷新令牌：传入异步数据库会话，刷新令牌
    async def refresh_token(db: AsyncSession, refresh_token: str) -> Dict:
        """用 refresh_token 换取新的 access_token"""
        # 验证 JWT 签名、过期、scope，返回载荷
        payload = AuthBase.verify_token(refresh_token, scope="refresh")
        if not payload:
            raise APIException(status_code=401, message="无效的刷新令牌")

#从载荷中获取该管理员id
        admin_id = payload.get("sub")
        # 查数据库中该管理员的活跃令牌，查询现在数据库中有效令牌
        token_query = select(AdminToken).where(
            (AdminToken.admin_id == admin_id) &
            (AdminToken.is_active == True)
        )
        #执行该语句，返回row对象
        result = await db.execute(token_query)
        #货期到该令牌的orm对象
        token_record = result.scalar_one_or_none()

        # 对比哈希，防止令牌已失效或被篡改
        if not token_record or not AuthBase.verify_token_hash(refresh_token, token_record.token):
            raise APIException(status_code=401, message="刷新令牌已失效或过期")

        # 更新最后使用时间
        token_record.last_used_at = datetime.now(UTC)
        await db.commit()

        # 签发新的 access_token
        access_token = AuthBase.create_access_token(
            admin_id,
            scope="backoffice",
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"access_token": access_token, "token_type": "bearer"}

    @staticmethod #登出：传入异步会话数据库，刷新令牌
    async def logout(db: AsyncSession, refresh_token: str) -> None:
        """登出：将 refresh_token 标记为无效"""
        payload = AuthBase.verify_token(refresh_token, scope="refresh")
        if not payload:
            return  # 令牌无效则静默处理

        admin_id = payload.get("sub")
        token_query = select(AdminToken).where(
            (AdminToken.admin_id == admin_id) &
            (AdminToken.is_active == True)
        )
        result = await db.execute(token_query)
        token_record = result.scalar_one_or_none()

        if token_record:
            token_record.is_active = False
            await db.commit()


backoffice_auth_service = BackofficeAuthService()
