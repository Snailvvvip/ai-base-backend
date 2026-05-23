from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service
from app.utils.redis_utils import remove_redis_cache


class ModuleModel(BasicModel, table=True):
  __tablename__ = "pl_module"

  label: str = Field(default=None, description="模块名称")
  code: str = Field(default=None, description="模块标识")
  remarks: str = Field(default=None, description="模块备注信息")
  module_config: str = Field(default=None, description="模块配置信息")


async def before_update(row_dict, session):
  module = row_dict.get("code", None)
  await remove_redis_cache(f"@@general_module_{module}")


ModuleService = create_model_service(ModuleModel, before_update=before_update)
