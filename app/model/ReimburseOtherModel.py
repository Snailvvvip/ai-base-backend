from datetime import datetime
from decimal import Decimal

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class ReimburseOtherModel(BasicModel, table=True):
  __tablename__ = "pl_reimburse_other"

  title: str = Field(default=None, description="标题")
  type: str = Field(default=None, description="报销类型")
  amount: Decimal = Field(default=None, description="报销金额")
  recipe_type: str = Field(default=None, description="票据类型")
  reimburse_id: str = Field(default=None, description="报销单id")
  invoice_text: str | None = Field(default=None, title="发票数组json字符串")


ReimburseOtherService = create_model_service(Cls=ReimburseOtherModel)
