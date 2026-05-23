from datetime import datetime

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class LlmOrder(BasicModel, table=True):
  __tablename__ = "llm_order"

  prod_id: str = Field(default=None, description="商品ID")
  user_id: str = Field(default=None, description="用户ID")


LlmOrderService = create_model_service(LlmOrder)
