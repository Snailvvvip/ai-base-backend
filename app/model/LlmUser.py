from datetime import datetime

from sqlmodel import Field

from app.model.BasicModel import BasicModel


class LlmUser(BasicModel, table=True):
  __tablename__ = "llm_user"

  full_name: str = Field(default=None, description="用户名称")
  username: str = Field(default=None, description="用户名")
  password: str = Field(default=None, description="用户密码")
  member_start: datetime = Field(default=None, description="开通会员时间")
  member_end: datetime = Field(default=None, description="会员截止到期时间")
