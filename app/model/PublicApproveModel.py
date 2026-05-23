from decimal import Decimal

from sqlmodel import Field

from app.model.BasicModel import BasicModel


class PublicApproveModel(BasicModel):
  title: str = Field(default=None, description="审批标题")
  description: str = Field(default=None, description="审批描述信息")
  status: str = Field(default=None, description="审批状态")
  amount: Decimal = Field(default=None, description="审批金额")
  logs: str = Field(default=None, description="审批日志")
  approve_from: str = Field(default=None, description="审批来源")

  user_id: str = Field(default=None, description="当前审批人id")
  apply_user_id: str = Field(default=None, description="申请人id")
