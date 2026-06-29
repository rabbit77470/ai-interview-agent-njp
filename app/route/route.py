from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.base import close_db_engine
from app.exceptions.http_exceptions import APIException
from app.schemas.response import ApiResponse
#创建当前模块日志对象
logger = logging.getLogger(__name__)

# 开发环境允许所有来源，生产环境需限定具体域名
#无论什么环境，都允许全部跨域
ALLOWED_ORIGINS = ["*"] if settings.ENV in ("development", "preview") else ["*"]

#
@asynccontextmanager#异步上下文管理器装饰器
#FastAPI 的 lifespan 是应用生命周期钩子
async def lifespan(application: FastAPI):
    """应用生命周期管理"""
    # === 启动时 ===
    logger.info("应用启动中...")
    yield
    # === 关闭时 ===
    await close_db_engine()
    logger.info("应用已关闭")


def create_app():
    """FastAPI 应用工厂"""
    app = FastAPI(
        lifespan=lifespan,#绑定应用启停钩子，启动自动执行yield前初始化逻辑，关闭自动执行yield后资源释放
        title=settings.PROJECT_NAME, #接口文档首页大标题
        description="AI 智能面试系统 - 后台管理", #接口文档描述
        version="1.0.0", #版本
        docs_url="/docs", #Swagger 交互式接口文档访问地址：浏览器打开 http://127.0.0.1:8000/docs 可在线调试所有接口
        redoc_url="/redoc",#另一种风格静态文档页面，地址 /redoc，纯展示无调试功能；同样填 None 可关闭。
    )

    # CORS 跨域配置
    app.add_middleware(#给应用全局挂载中间件，所有接口请求都会先走中间件处理
        CORSMiddleware,#FastAPI 内置跨域处理中间件，自动处理浏览器 OPTIONS 预检请求、返回跨域响应头。
        allow_origins=ALLOWED_ORIGINS, #允许跨域的前端域名白名单
        allow_credentials=True, #允许跨域请求携带身份凭证
        allow_methods=["*"], #允许前端使用的Http请求方法：["*"] 代表放行全部：GET、POST、PUT、DELETE、OPTIONS 等
        allow_headers=["*"], #允许前端请求携带的自定义请求头：["*"] 放行所有头部，包括鉴权用的 Authorization: Bearer xxx；
    )

    # ==================== 路由注册 ====================
    from app.api.backoffice.v1.auth import router as auth_router
    #app.include_router() 是 FastAPI 主应用挂载子路由分组的核心方法，
    #把模块内所有接口注册到全局主 app，接口才能被外部访问。
    app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/backoffice/auth", tags=["后台管理-认证"])

    from app.api.backoffice.v1.admin import router as admin_router
    app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/backoffice/admins", tags=["后台管理-管理员"])

    # ==================== 异常处理 ====================
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        logger.error(f"API异常: {exc.status_code} - {exc.code} - {exc.detail}")
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.code,
            http_code=exc.status_code,
            data=exc.data
        )

#全局自定义业务异常捕获处理器
    @app.exception_handler(HTTPException)#FastAPI 全局异常捕获装饰器，拦截指定类型异常，统一自定义返回格式，不再返回框架默认的报错 JSON；
    #request: Request：当前完整 HTTP 请求对象
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
        return ApiResponse.failed(
            message=exc.detail,
            body_code=exc.status_code,
            http_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"参数验证错误: {exc.errors()}")
        return ApiResponse.failed(
            message="参数验证错误",
            body_code=1001,
            http_code=status.HTTP_400_BAD_REQUEST,
            data=exc.errors()
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"未处理异常: {str(exc)}")
        return ApiResponse.failed(
            message="服务器内部错误",
            body_code=1005,
            http_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return app
