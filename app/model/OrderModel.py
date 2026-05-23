from decimal import Decimal

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class OrderModel(BasicModel, table=True):
  __tablename__ = "pl_order"

  name: str = Field(default=None, description="订单名称")
  price: Decimal = Field(default=None, description="订单金额")
  user_id: str = Field(default=None, description="申请人id")
  reimburse_id: str = Field(default=None, description="关联报销单id")


OrderService = create_model_service(OrderModel)
