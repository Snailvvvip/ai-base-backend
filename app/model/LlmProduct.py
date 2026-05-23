from datetime import datetime

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class LlmProduct(BasicModel, table=True):
  __tablename__ = "llm_product"

  name: str = Field(default=None, description="商品名称")
  price: float = Field(default=None, description="商品价格")
  valid_start: datetime = Field(default=None, description="商品有效开始时间")
  valid_end: datetime = Field(default=None, description="商品有效结束时间")


LlmProductService = create_model_service(LlmProduct)
