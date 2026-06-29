from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Any, Type
#functools是python标准内置工具库，wrap是其中专门用于装饰器修复函数元信息的装饰器，
#完整保留被装饰原函数的名称，文档注释，元数据
from functools import wraps


# ==================== 基础 Schema ====================
#最底层基类，from_attributes=True 让 Pydantic 能读 ORM 对象
# 最底层基类，开启 ORM 兼容模式，允许 Pydantic 直接读取 SQLAlchemy ORM 对象
#Baseschema是项目所有pydantic序列化模型（返回vo，查询DTO）的公共父类。
#只配置了一条核心规则from_attributes=True，解决「SQLAlchemy ORM 对象 → Pydantic 模型」自动赋值的问题。
class BaseSchema(BaseModel):
    #差不多是：开启【从对象属性读取数据】功能
    model_config = ConfigDict(from_attributes=True)


# 响应模型通用基类，定义所有响应共有的字段
#可以直接把数据库查询出来的orm对象丢给这个schema做校验，转json，不用手动转字典
#项目里所有的数据库表几乎都标配这3个字段：逐渐id，创建时间，更新时间，抽取正公共父类
#所有返回vo直接继承，不用重复写
class BaseResponseSchema(BaseSchema):
    id: int
    created_at: datetime = Field(default=0)
    updated_at: datetime = Field(default=0)


# ==================== 时间格式化工具 ====================
#函数作用：格式化日期时间对象，传入datetime实例或者none
def format_datetime(dt: Optional[datetime]) -> str:
    """将 datetime 转为 ISO 格式字符串，None 转为空字符串"""
    if dt is None:
        return ""
    #isoformat内置方法，生成ISO标准时间字符串2026-06-29T14:30:25.123456
    return dt.isoformat()

#将各种类型时间输入转换为时间戳
def to_timestamp(v: Any) -> int:
    """将各种时间格式转换为时间戳整数，None 转为 0"""
    if isinstance(v, datetime): #如果输入时datetime对象，
        return int(v.timestamp()) #timestamp转换为浮点时间戳
    elif v is None: #如果是空
        return 0 #返回0
    try:
        return int(v) #输入是数字，数字字符串（直接转时间戳
    except (TypeError, ValueError):
        raise ValueError("time fields must be valid datetime or a number")


# ==================== padded_id 装饰器 ====================
# 自动把数字 id 补零格式化为固定长度字符串（如 id=1 → padded_id="0001"）
# 用在 AdminResponse 等响应类上，前端展示友好
#感觉像面向切面
def add_padded_id(pad_length: int = 4):
    """装饰器：给 Pydantic 响应模型自动注入 padded_id 字段和格式化逻辑"""

    def decorator(cls: Type): #真正的修饰类，修饰目标pydantic类
        # 动态添加 padded_id 字段
        if not hasattr(cls, 'padded_id'):  #判断类是否有该字段，没有则
            cls.padded_id = Field(default=None, init=False)

        # 保存原始 model_validate 这个方法是用于orm对象转模型实例的
        original_validate = getattr(cls, 'model_validate', None)

        @classmethod#类方法
        @wraps(original_validate or (lambda cls, obj: cls.model_construct(**obj.__dict__)))
        def enhanced_validate(cls, obj: Any):
            # 调用原始验证
            if original_validate and original_validate != enhanced_validate:
                instance = original_validate(obj)
            else:
                instance = cls.model_construct(**obj.__dict__)

            # 自动设置 padded_id
            instance.padded_id = str(instance.id).zfill(pad_length)
            return instance

        cls.model_validate = enhanced_validate
        return cls

    return decorator
