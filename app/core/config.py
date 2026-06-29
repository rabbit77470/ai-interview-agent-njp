#pydantic单独拆分出来的配置专用库，Basesetting是该库提供的基础配置模板类
#继承它就能自动读取项目环境配置
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 环境配置
    ENV: str = "development"

    # 基础配置
    PROJECT_NAME: str = "AI-Interview"
    API_V1_STR: str = "/api/v1"
    API_PORT: int = 8006
    FRONTEND_URL: str = "http://localhost:3000"

    # 数据库配置
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "123456"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ai_interview"

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # JWT 配置
    SECRET_KEY: str = "ai-interview-dev-secret-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 管理员邮箱
    ADMIN_EMAIL: str = "admin@ai-interview.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

#全局生成一份可复用，带校验的配置单例，不用每次读取环境变量，统一管理所有项目参数
settings = Settings()
