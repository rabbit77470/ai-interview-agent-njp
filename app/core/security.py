from datetime import datetime, timedelta, UTC
from typing import Optional, Dict
from jose import jwt, JWTError
from app.core.config import settings
import uuid
from passlib.context import CryptContext

# bcrypt 密码加密器
#CryptContext来自第三方库passlib，是统一的密码加密、校验工具类，专门进行密码加密存储，密码比对
#schemes=["bcrypt"]为指定使用bcrypt哈希算法加密密码，deprecated="auto"自动处理算法兼容：
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#AuthBase：是认证工具类
class AuthBase:
    """认证基类，提供 JWT 令牌的生成和校验方法"""
#静态方法
    @staticmethod
    def create_access_token( #这个方法专门生成登录用的JWT访问令牌
        subject: str, #令牌主体，一般传用户ID，代表这个token属于哪个用户
        scope: str, #自定义权限标识，用于区分你是普通用户还是管理员，后面可以拦截
        expires_delta: Optional[timedelta] = None #可选自定义过期时长，不传则使用配置文件默认30分钟过期
    ) -> str:
        """创建访问令牌（Access Token），默认 30 分钟过期"""
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

#JWT载荷payload to_encode字典
        to_encode = {
            "exp": expire,          # 过期时间
            "sub": str(subject),     # 令牌主体（用户ID/管理员ID）
            "scope": scope,          # 权限范围（client / backoffice）
            "jti": str(uuid.uuid4()) # 令牌唯一标识
        }
        #jwt.encode加密生成令牌，to_encode要存入token的业务载荷，
        # 第二个参数为项目全局密钥，第三个参数为指定加密算法
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

#生成刷新令牌，和之前access token（访问令牌）搭配使用，解决短时效访问令牌频繁登录问题
    @staticmethod
    #第一个参数，用户唯一ID，第二个参数：过期时间（可选自定义过期时长，不传走配置默认7天）
    def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
        """创建刷新令牌（Refresh Token），默认 7 天过期"""
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "jti": str(uuid.uuid4()),
            "scope": "refresh"
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_token(token: str, scope: str = None) -> Optional[Dict]:
        """验证令牌，返回 payload 字典；校验失败或 scope 不匹配返回 None"""
        try:#校验令牌
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            if scope and payload.get("scope") != scope:
                return None
            return payload
        except JWTError:
            return None

    @staticmethod
    def hash_token(token: str) -> str:
        """对令牌进行 bcrypt 哈希（存入数据库防止泄露）"""
        return pwd_context.hash(token)

    @staticmethod
    def verify_token_hash(plain_token: str, hashed_token: str) -> bool:
        """验证明文令牌与数据库中的哈希是否匹配"""
        return pwd_context.verify(plain_token, hashed_token)
