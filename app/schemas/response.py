from typing import TypeVar, Generic, Optional, Any, List, Callable, Dict
from fastapi import Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from math import ceil
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder
from app.exceptions.http_exceptions import APIException

#依旧经典创建一个泛型
T = TypeVar('T')

#继承Basemodel说明是一个pydentic类，第二参数代表有泛型
#Pydantic 基础模型，FastAPI 自动做序列化、JSON 返回、类型校验，接口返回时自动转标准 JSON 给前端。
class PaginatedData(BaseModel, Generic[T]):
    """分页数据结构"""
    items: List[T]  #当前页的数据列表，T就是查询的业务类型【admin对象1，admin对象2】
    total: int  #符合筛选条件的数据总条数，用于前端计算总页数，展示“共xx条数据”
    per_page: int #每页展示多少条（分页大小，如10,20）
    current_page: int #当前请求的页码（前端传Page=3，该值就是3）
    last_page: int #最后一页页码（总页数），计算公式：last_page = ceil(total / per_page)。
    has_more: bool #是否还有下一页

#全局统一接口成功场景的返回json结构，所有正常接口都调用apiResponse.success（）
#返回数据，前后端约定一套固定的返回格式
class ApiResponse:
    """统一 API 响应格式"""
#静态方法，无需实例化apiResponse，直接调用
    @staticmethod
    def success(  #成功场景方法
        data: Any = None,  #传入业务主体数据，可以是用户对象，分页列表，数字
        message: str = "Success", #提示文案
        body_code: int = 200, #响应体内部业务码
        http_code: int = status.HTTP_200_OK, #Http协议响应状态码
        headers: Dict = None #自定义响应头
    ) -> JSONResponse:
        """成功响应"""
        response_data = { #组装一个json字典
            "code": body_code,
            "message": message,
            #orm模型datetime等不能直接转json，该函数自动转换为标准字段，避免序列化报错
            "data": jsonable_encoder(data) if data is not None else None
        }
#JSONResponse是FastAPI专用返回对象，作用
        return JSONResponse(content=response_data, status_code=http_code, headers=headers)

#专门处理不需要返回任何json内容的成功场景，例如删除资源，清空操作，登出接口
#使用FastAPI原生Response，默认返回Http204，响应体为空，
    @staticmethod
    def success_without_data( #没有数据的成功场景
        http_code: int = status.HTTP_204_NO_CONTENT, #Http状态码
        headers: Dict = None  #自定义响应头
    ) -> Response:
        """无数据的成功响应（204）"""
        return Response(status_code=http_code, headers=headers)


#统一封装业务失败场景的返回json，和success成对配套
    @staticmethod
    def failed(  #业务逻辑出错（参数错误，权限不足，令牌失效），返回标准化错误json
        message: str, #给前端展示的错误提示文案
        body_code: int, #业务自定义错误码
        http_code: int = status.HTTP_400_BAD_REQUEST, #Http协议状态码
        data: Any = None, #错误附加信息
        headers: Dict = None #自定义响应头
    ) -> JSONResponse:
        """失败响应"""
        response_data = {#基础固定结构：必须有业务码+错误信息
            "code": body_code,
            "message": message
        }
        if data is not None: #只有传入data时，才追加data字段
            response_data["data"] = jsonable_encoder(data)
        return JSONResponse(content=response_data, status_code=http_code, headers=headers)

    @staticmethod
    async def paginate(
        db: AsyncSession, #数据库异步会话对象 ，用来执行数据库查询
        query, #SQLalchemy查询语句（select（User）.where(、、、)
        page: int = 1, #当前页码
        per_page: int = 10, #每页展示条数
#Callable[[List[Any]], List[Any]]Callable = 可调用对象（就是函数），用来标注一个函数的入参类型和返回值类型。
#格式规则：Callable[[入参1类型,入参2...], 返回值类型]
        transform_func: Optional[Callable[[List[Any]], List[Any]]] = None,#可选数据转换回调函数，对查询到的数据统一加工
        message: str = "Success", #提示文案
        body_code: int = 200, #响应体内业务成功码
        http_code: int = status.HTTP_200_OK, #Http状态码
        headers: Dict = None #自定义响应头，可选
    ) -> JSONResponse:
        """分页响应"""
        if page < 1 or per_page < 1: #页码，每页条数不能小于1，
            raise APIException(status_code=400, message="无效的分页参数")

        # 总数查询

        #query.subquery()：把传入的业务查询变成子查询，select(func.count())：统计子查询内所有数据行数，也就是筛选条件下的总条数；
        total_query = select(func.count()).select_from(query.subquery())
        #await db.scalar(total_query)：异步执行 SQL，只获取数字结果，性能高
        total = await db.scalar(total_query)

        # 分页计算
        #计算总页数
        last_page = ceil(total / per_page) if per_page > 0 else 0
        if page > last_page and last_page > 0: #校验页码是否超出范围
            raise APIException(status_code=404, message="页码不存在")

        # 分页查询
        offset_query = query.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(offset_query)
        items = result.scalars().all()

        if transform_func is not None: #是否传入转换 函数，有则交给转换函数处理
            items = transform_func(items)

#组装通用分页模型PaginatedData
        paginated_data = PaginatedData(
            items=items,
            total=total,
            per_page=per_page,
            current_page=page,
            last_page=last_page,
            has_more=page < last_page
        )

        return JSONResponse(
            content={
                "code": body_code,
                "message": message,
                "data": jsonable_encoder(paginated_data)
            },
            status_code=http_code,
            headers=headers
        )
