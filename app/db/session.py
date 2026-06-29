from typing import AsyncGenerator#专门标注异步生成器的类型
from sqlalchemy.ext.asyncio import AsyncSession #AsyncSession 是 SQLAlchemy 异步专用数据库会话，支持 await 非阻塞操作数据库，是 FastAPI 异步项目执行增删改查、管理事务的核心对象。
from contextlib import asynccontextmanager #是专门用来创建异步上下文管理器的装饰器。
from .base import get_session_local ####导入封装好的会话工厂货期函数

#定义一个获取数据库会话的异步方法，返回的是异步生成器，会产出AsyncSession 会话，无发送值
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（FastAPI 依赖注入用）"""
    AsyncSessionLocal = get_session_local() #通过自定义会话工厂函数货期一个会话（带有数据库连接）
    #AsyncSession 实现了异步上下文协议
    async with AsyncSessionLocal() as session:
        yield session

#把当前函数转换为异步上下文管理器，
@asynccontextmanager
async def transaction(db: AsyncSession):
    """事务上下文管理器，自动提交或回滚"""
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
