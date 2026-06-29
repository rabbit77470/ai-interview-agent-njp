from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# 构建异步数据库连接 URL
# 格式: postgresql+asyncpg://用户名:密码@主机:端口/数据库名
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# 懒汉式单例：整个应用生命周期只创建一次引擎和会话工厂
engine = None
AsyncSessionLocal = None

#引擎就是翻译官
def get_engine():
    """获取或创建异步数据库引擎"""
    global engine #使用全局变量engine，用来保存数据库引擎实例，所有函数共享
    if engine is None: #如果为空则创建
        engine = create_async_engine( #创建异步引擎
            SQLALCHEMY_DATABASE_URL, #拼接好的数据库地址
            echo=True,            # 开启 SQL 日志
            future=True,          # 使用新版 2.0 ORM 风格
            pool_pre_ping=True,   # 连接可用性预检测
            pool_recycle=1800,    # 30 分钟回收连接
            pool_timeout=30,      # 获取连接超时时间
            max_overflow=10,      # 最大溢出连接数
            pool_size=20,         # 连接池大小
        )
    return engine #返回数据库引擎


def get_session_local():
    """获取或创建异步会话工厂"""
    global AsyncSessionLocal #使用全局变量来存放会话工厂，全局共享
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker( #会话工厂构造器，作用：绑定数据库引擎，批量产出数据库会话
            bind=get_engine(),#把前面创建好的异步数据库引擎绑定给会话工厂，所有从这个工厂生成的会话，都会复用引擎里的连接池与数据库连接
            class_=AsyncSession,#指定会话类型为异步会话

            expire_on_commit=False#提交之后实体对象依然保留数据，不用重复查询数据库
        )
    return AsyncSessionLocal  #返回全局唯一的会话工厂实例


async def close_db_engine():
    """关闭数据库引擎和连接池"""
    global engine
    if engine is not None:
        await engine.dispose() #销毁异步引擎
        engine = None
