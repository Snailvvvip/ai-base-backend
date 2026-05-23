from decimal import Decimal
from typing import Optional, List

from pydantic import computed_field
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, select

from app.model.BasicModel import BasicModel
from app.model.UserModel import UserServiceModel
from app.utils.create_module_service import create_model_service


class ProjectModel(BasicModel, table=True):
  __tablename__ = "pl_project"

  name: str = Field(default=None, description="项目名称")
  description: str = Field(default=None, description="项目描述")
  budget: Decimal = Field(default=None, description="项目预算金额")
  # version: int = Field(default=None, description="项目版本号")

  # /*---------------------------------------leader_id-------------------------------------------*/

  leader_id: str = Field(
    default=None,
    description="项目负责人id",
    foreign_key="pl_user.id",  # 添加外键约束
    nullable=True
  )

  leader: Optional["UserServiceModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ProjectModel.leader_id",
      "remote_side": "UserServiceModel.id",
      "uselist": False
    }
  )

  @computed_field
  @property
  def leader_name(self) -> Optional[str]:
    try:
      return self.leader.full_name if self.leader else None
    except:
      return None

  @leader_name.setter
  def leader_name(self, value: Optional[str]) -> None:
    pass

  # /*---------------------------------------approve_list-------------------------------------------*/

  approve_list_relationship: Optional[List["ApproveModel"]] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ApproveModel.proj_id",
      "primaryjoin": "ProjectModel.id == ApproveModel.proj_id",
    }
  )

  # /*---------------------------------------spent: 已花费金额-------------------------------------------*/
  @computed_field
  @property
  def spent(self) -> Optional[Decimal]:
    try:
      total_amount = Decimal(0)
      for approve_item in self.approve_list_relationship:
        if approve_item.status == 'approved':
          total_amount = total_amount + approve_item.amount
      return total_amount
    except:
      return None

  @spent.setter
  def spent(self, value: Optional[Decimal]) -> None:
    pass

  # /*---------------------------------------balance：剩余预算金额-------------------------------------------*/
  @computed_field
  @property
  def balance(self) -> Optional[Decimal]:
    if self.spent is not None:
      return self.budget - self.spent
    else:
      return None

  @balance.setter
  def balance(self, value: Optional[Decimal]) -> None:
    pass


ProjectService = create_model_service(
  Cls=ProjectModel,
  custom_query=lambda: select(ProjectModel)
  .options(
    selectinload(ProjectModel.leader),
    selectinload(ProjectModel.approve_list_relationship)
  ),
)
