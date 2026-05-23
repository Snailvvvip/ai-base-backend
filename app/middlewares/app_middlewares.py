import time
import traceback

import jwt
from fastapi import FastAPI, HTTPException
from passlib.exc import InvalidTokenError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.env import env
from app.controller.add_user_route import unauthorized_exception, get_current_user
from app.model.ApiSecretModel import ApiSecretService
from app.model.PosModel import PosModel
from app.model.UserModel import UserServiceModel
from app.utils.CrpyUtils import TokenInfo, CryptUtils
from app.utils.api_secret_utils import api_secret_utils, ApiSecretStatus
from app.utils.db_utils import async_session
from app.utils.redis_utils import get_redis_cache


def add_app_middlewares(app: FastAPI):
  @app.middleware("http")
  async def add_process_time_header(request: Request, call_next):
    print("time start")
    start_time = time.time()
    response = await call_next(request)
    process_time = f"time:{time.time() - start_time}s"
    response.headers['x-Process-Time'] = process_time
    print("time end")
    return response

  # @app.middleware("http")
  # async def middleware2(request: Request, call_next):
  #   print("middleware2 start")
  #   response = await call_next(request)
  #   print("middleware2 end")
  #   return response

  @app.middleware("http")
  async def add_oauth_middleware(request: Request, call_next):
    if not env.jwt_global_enable or request.method == "OPTIONS":
      # 没有开启全局的接口认证功能
      request.state.user = None
      request.state.token = None
      return await call_next(request)

    # 判断接口是否为认证白名单中的接口
    if request.url.path in env.jwt_white_list:
      return await call_next(request)

    token: str | None = None
    oauth_header = request.headers.get("Authorization")
    if oauth_header and oauth_header.startswith("Bearer "):
      token = oauth_header.split(" ")[1].strip()

    # 没有得到token信息，直接返回错误
    if not token:
      raise unauthorized_exception

    # 从token秘钥中解析token信息
    try:
      token_info: TokenInfo = CryptUtils.get_token_info(token)
      # 既不是access token，也不是api token，直接返回错误信息
      if token_info.get('type') != 'access' and token_info.get('type') != 'api':
        raise unauthorized_exception
    except InvalidTokenError:
      raise unauthorized_exception
    except jwt.exceptions.InvalidSignatureError:
      raise unauthorized_exception
    except jwt.exceptions.ExpiredSignatureError:
      raise unauthorized_exception
    except jwt.exceptions.DecodeError:
      raise unauthorized_exception

    async def get_default_cache_value():
      async with async_session() as session:
        try:
          user_dict = await get_current_user(session, token)
          return user_dict
        except InvalidTokenError:
          return None

    user_dict = await get_redis_cache(
      f"access_token_username_{token_info.get('username')}",
      get_default_cache_value
    )
    if not user_dict:
      raise unauthorized_exception

    print("user_dict", user_dict)
    request.state.user = UserServiceModel(**user_dict)
    user_pos_dict = user_dict.get('pos')
    if user_pos_dict:
      request.state.user.position = PosModel(**user_pos_dict)
    request.state.token = token

    # 如果请求的是api接口
    # api开头的接口需要额外验证秘钥
    if request.url.path.startswith("/api/"):
      # /api/开头的接口，只能使用 api token 访问
      if token_info.get('type') != "api":
        raise unauthorized_exception
      # 验证秘钥状态
      secret_status = await api_secret_utils.verify_secret(token)
      print("secret_status", secret_status)
      if secret_status == ApiSecretStatus.invalid:
        # 秘钥无效
        raise unauthorized_exception
      elif secret_status == ApiSecretStatus.not_exist:
        # 秘钥没有缓存
        async with async_session() as session:
          query_cls = await ApiSecretService.query_item(session, {"secret": token})
          if query_cls:
            # 秘钥存在
            await api_secret_utils.save_secret(token, ApiSecretStatus.valid)
          else:
            # 秘钥不存在
            await api_secret_utils.save_secret(token, ApiSecretStatus.invalid)
            raise unauthorized_exception
      else:
        # 秘钥有效
        pass
    else:
      # 非/api/接口，智能使用 access token 访问
      if token_info.get('type') != "access":
        raise unauthorized_exception
    response = await call_next(request)
    return response

  @app.middleware("http")
  async def catch_authorized(request: Request, call_next):
    try:
      response = await call_next(request)
    except HTTPException as e:
      print(e)
      if e.status_code == status.HTTP_401_UNAUTHORIZED:
        return JSONResponse(content={"message": e.detail}, status_code=status.HTTP_401_UNAUTHORIZED)
      else:
        return JSONResponse(content={"message": e.detail}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
      print(e)
      traceback.print_exc()
      return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
