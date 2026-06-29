from fastapi import HTTPException #是FastAPI框架内置异常类
from typing import Any, Optional

#继承FastAPI内置HTTPException，拥有原生所有能力，抛出后指定Http状态码，默认detail提示
class APIException(HTTPException):
    """业务异常基类，统一携带业务错误码"""
    def __init__(  #构造函数
        self,
        code: int = 10000,  #业务细分错误码，数字类型，前后端约定好对照表
        message: str = "API 异常", #Messages给用户看的错误文字，赋值给父类detail
        status_code: int = 400, #Http状态码
        data: Any = None, #异常时附带返回的数据
    ) -> None:
        #调用父类的构造方法，完成原生异常初始化
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.data = data

#该异常类继承了apiException，间接继承了HttpException，保留所有异常响应能力
#其实我感觉更像重写了
class ValidationError(APIException):
    """参数验证错误 — code: 1001"""
    def __init__(self, message: str = "参数验证错误", data: Any = None):
        super().__init__(code=1001, message=message, status_code=400, data=data)


class AuthenticationError(APIException):
    """认证失败 — code: 1002"""
    def __init__(self, message: str = "认证失败", data: Any = None):
        super().__init__(code=1002, message=message, status_code=401, data=data)


class AuthorizationError(APIException):
    """权限不足 — code: 1003"""
    def __init__(self, message: str = "权限不足", data: Any = None):
        super().__init__(code=1003, message=message, status_code=403, data=data)


class NotFoundError(APIException):
    """资源不存在 — code: 1004"""
    def __init__(self, message: str = "资源不存在", data: Any = None):
        super().__init__(code=1004, message=message, status_code=404, data=data)


class ServerError(APIException):
    """服务器内部错误 — code: 1005"""
    def __init__(self, message: str = "服务器内部错误", data: Any = None):
        super().__init__(code=1005, message=message, status_code=500, data=data)


class ForeignKeyViolationError(APIException):
    """外键约束冲突 — code: 1006"""
    def __init__(self, message: str = "该记录已关联其他资源，请先将其标记为'停用'以对用户隐藏", data: Any = None):
        super().__init__(code=1006, message=message, status_code=400, data=data)
