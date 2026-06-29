#declarative_base是 SQLAlchemy ORM 模块提供的类工厂函数
#核心作用是创建基础orm模型父类，所有数据库表实体模型都要继承这个激烈，实现orm映射
#Python 类 ↔ 数据库表
#类属性 ↔ 表字段
from sqlalchemy.orm import declarative_base

# SQLAlchemy 声明式基类，所有 ORM 模型都继承它
Base = declarative_base()
