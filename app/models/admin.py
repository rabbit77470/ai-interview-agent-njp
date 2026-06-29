from sqlalchemy import Boolean, Column, Integer, String#导入一些orm字段
from .base import BaseModel #代入orm抽象基类
from passlib.context import CryptContext #导入密码加密
import enum #导入枚举类
#加密器
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#定义角色枚举类，
class UserRole(str, enum.Enum): #enum.Enum:python内置枚举基类，用来定义固定常量集合，str，枚举成员本省等价于字符串
    ADMIN = "admin" #普通管理员
    SUPERADMIN = "superadmin" #超级管理员


class Admin(BaseModel): #继承了创建时间，更新时间两个时间字段，
    __tablename__ = "admins"#指定数据库真实表名

    #ID列，类型为integer，是主键，自动创建索引，开启自增
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    #角色列，String类型，默认值为admin，不能为空
    role = Column(String(20), default=UserRole.ADMIN, nullable=False)
    #邮箱列，String类型，唯一，创建索引，不能为空
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)#账号是否可用

#两个密码工具方法
    #生成密码哈希（注册时用）
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
    #实例方法：校验登录密码
    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.password)
