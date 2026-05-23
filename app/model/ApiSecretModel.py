import uuid
from datetime import timedelta

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.model.UserModel import UserService, UserServiceModel
from app.utils.CrpyUtils import CryptUtils
from app.utils.api_secret_utils import api_secret_utils
from app.utils.create_module_service import create_model_service


class ApiSecretModel(BasicModel, table=True):
  __tablename__ = "pl_api_secret"

  secret: str = Field(..., description="api秘钥")
  description: str = Field(..., description="描述信息")


# 插入数据之前，查询当前用户信息，使用username生成一个access_token作为秘钥保存到 ApiSecretModel中
async def before_insert(row_dict, session):
  user: UserServiceModel = await UserService.query_item(session, {"id": row_dict.get("created_by")})
  row_dict["secret"] = CryptUtils.create_token(user.username, "api", timedelta(days=9999))
  raise Exception("ApiSecretModel service is desperate!")


# 删除ApiSecret凭据之前，先清理掉缓存中的秘钥信息
async def before_delete(row_dict, session):
  row_cls: ApiSecretModel = await  ApiSecretService.query_item(session, {"id": row_dict.get("id")})
  await api_secret_utils.remove_secret(row_cls.secret)
  raise Exception("ApiSecretModel service is desperate!")


# 更新ApiSecret凭据之前，先清理掉缓存中的秘钥信息
async def before_update(row_dict, session):
  row_cls: ApiSecretModel = await  ApiSecretService.query_item(session, {"id": row_dict.get("id")})
  await api_secret_utils.remove_secret(row_cls.secret)
  raise Exception("ApiSecretModel service is desperate!")


# 不允许批量处理ApiSecret凭据信息
async def before_batch_method(row_dict_list, session):
  raise Exception("秘钥不支持批量操作！")


ApiSecretService = create_model_service(
  Cls=ApiSecretModel,
  before_insert=before_insert,
  before_update=before_update,
  before_delete=before_delete,

  before_batch_insert=before_batch_method,
  before_batch_update=before_batch_method,
  before_batch_delete=before_batch_method,
)
