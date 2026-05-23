from datetime import timedelta

from app.general.general_interceptors import add_general_interceptor, GeneralInterceptor
from app.model.ApiSecretModel import ApiSecretModel, ApiSecretService
from app.model.UserModel import UserServiceModel, UserService
from app.utils.CrpyUtils import CryptUtils
from app.utils.api_secret_utils import api_secret_utils


# 插入数据之前，查询当前用户信息，使用username生成一个access_token作为秘钥保存到 ApiSecretModel中
async def before_insert(row, session, user):
  user: UserServiceModel = await UserService.query_item(session, {"id": user.id})
  row["secret"] = CryptUtils.create_token(user.username, "api", timedelta(days=9999))


# 删除ApiSecret凭据之前，先清理掉缓存中的秘钥信息
async def before_delete(query_config, session, user):
  row_cls: ApiSecretModel = await  ApiSecretService.query_item(session, {"id": query_config.get("id")})
  await api_secret_utils.remove_secret(row_cls.secret)


# 更新ApiSecret凭据之前，先清理掉缓存中的秘钥信息
async def before_update(row_dict, session):
  row_cls: ApiSecretModel = await  ApiSecretService.query_item(session, {"id": row_dict.get("id")})
  await api_secret_utils.remove_secret(row_cls.secret)


# 不允许批量处理ApiSecret凭据信息
async def before_batch_method(row_dict_list, session):
  raise Exception("秘钥不支持批量操作！")


def add_general_interceptor_api_secret():
  add_general_interceptor(GeneralInterceptor(
    module="api_secret",
    before_insert=before_insert,
    before_delete=before_delete,
    before_update=before_update,
    before_batch_insert=before_batch_method,
    before_batch_update=before_batch_method,
  ))
