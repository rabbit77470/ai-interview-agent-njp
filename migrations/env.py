import os
import sys
import glob
import importlib
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ========== 1. 把项目根目录加入 sys.path，让 Alembic 能 import 项目代码 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# ========== 2. 从项目配置中导入 settings 和 SQLAlchemy Base ==========
from app.core.config import settings
from app.db.models import Base #所有模型继承的Base基类


def import_all_models():
    """自动导入 app/models/ 下所有模型文件，确保表定义注册到 Base.metadata"""
    models_path = Path(BASE_DIR) / "app" / "models"
    model_files = glob.glob(str(models_path / "*.py"))

    for model_file in model_files:
        if not model_file.endswith("__init__.py"):
            module_name = Path(model_file).stem
            importlib.import_module(f"app.models.{module_name}")


# ========== 3. 导入所有模型（Admin、AdminToken 等） ==========
import_all_models()

# ========== 4. Alembic 配置对象 ==========
config = context.config

# 用项目 .env 中的数据库配置覆盖 alembic.ini 里的占位 URL
# 注意：Alembic 用 psycopg2（同步驱动），不用 asyncpg
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# 解析 alembic.ini 中的 Python 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ========== 5. 告诉 Alembic 要管理哪些表的元数据 ==========
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL 脚本，不连接数据库"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库，直接执行 DDL"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
