from datetime import datetime
from decimal import Decimal

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class ReimburseTravelModel(BasicModel, table=True):
  __tablename__ = "pl_reimburse_travel"

  title: str = Field(default=None, description="标题")
  type: str = Field(default=None, description="差旅类型")
  depart_time: datetime = Field(default=None, description="出发时间")
  arrive_time: datetime = Field(default=None, description="到达时间")
  depart_city: str = Field(default=None, description="出发城市")
  arrive_city: str = Field(default=None, description="到达城市")
  amount: Decimal = Field(default=None, description="报销金额")
  reimburse_id: str = Field(default=None, description="报销单id")
  invoice_text: str | None = Field(default=None, title="发票数组json字符串")


ReimburseTravelService = create_model_service(Cls=ReimburseTravelModel)
