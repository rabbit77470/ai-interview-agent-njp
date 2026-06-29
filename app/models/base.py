#func sql内置函数生成器，用于查询，默认值调用数据库原生SQL函数
from sqlalchemy import Column, Integer, func, TIMESTAMP
from app.db.models import Base

#这是一张抽象orm父类，所有业务表模型都继承Basemodel，不用每张表重复写创建时间，更新时间
class BaseModel(Base):
    """抽象基类，提供所有表通用的 created_at 和 updated_at 字段"""
    __abstract__ = True #标记当前类为抽象模型，sqlalchemy不会为Basemodel单独生成一张数据库表

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
