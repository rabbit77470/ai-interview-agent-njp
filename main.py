from app.route import create_app #导入路由文件
from app.core.config import settings #导入配置类
import logging #导入日志

#python内置标准日志库，用来打印分级日志，代替简陋print（）
#getLogger（）货期一个日志器对象，同名智慧创建一个实例
#__name__为python内置模块变量，等于该模块导入路径
logger = logging.getLogger(__name__)

app = create_app() #这个自定义函数创建了FastAPI实例

if __name__ == "__main__":
    import uvicorn
#uvicon是ASGI高性能服务器，专门运行FastAPI异步项目
    uvicorn.run(
        "main:app", #指定服务实例位置，main文件里的app对象
        host="0.0.0.0", #哪些地址可以访问这个接口
        port=settings.API_PORT, #服务运行端口
        reload=settings.ENV == "development", #代码热重载开关，修改代码自动重启服务
        workers=1 if settings.ENV == "development" else 4,#工作进程数量
        env_file=".env" #让uvicorn启动时自动加载项目根目录的env配置文件，提前注入环境变量
    )
