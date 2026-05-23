import decimal
from decimal import Decimal
from typing import Optional, List

from pydantic import computed_field
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, select

from app.model.ApproveModel import ApproveModel
from app.model.BasicModel import BasicModel
from app.model.ProjectModel import ProjectModel
from app.model.ReimburseOtherModel import ReimburseOtherModel
from app.model.ReimburseTravelModel import ReimburseTravelModel
from app.model.UserModel import UserModel, UserServiceModel
from app.utils.create_module_service import create_model_service


class ReimburseModel(BasicModel, table=True):
  __tablename__ = "pl_reimburse"

  title: str = Field(default=None, description="标题")
  remarks: str = Field(default=None, description="备注信息")

  # /*---------------------------------------project：报销单所属项目-------------------------------------------*/

  proj_id: str = Field(
    default=None,
    description="所属项目id",
    foreign_key="pl_project.id",  # 添加外键约束
    nullable=True
  )

  proj_rel: Optional["ProjectModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ReimburseModel.proj_id",
      "remote_side": "ProjectModel.id",
      "uselist": False
    }
  )

  @computed_field
  @property
  def project(self) -> Optional[ProjectModel]:
    try:
      return self.proj_rel
    except:
      return None

  @project.setter
  def project(self, value: Optional[ProjectModel]) -> None:
    pass

  # /*---------------------------------------travel_list：报销单子表差旅费用-------------------------------------------*/

  # 新增：与ReimburseTravelModel的一对多关系
  travel_list_rel: Optional[List["ReimburseTravelModel"]] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ReimburseTravelModel.reimburse_id",
      "primaryjoin": "ReimburseModel.id == ReimburseTravelModel.reimburse_id",
    }
  )

  @computed_field
  @property
  def travel_list(self) -> Optional[List["ReimburseTravelModel"]]:
    try:
      return self.travel_list_rel
    except:
      return None

  @travel_list.setter
  def travel_list(self, value: Optional[List["ReimburseTravelModel"]]) -> None:
    pass

  # /*---------------------------------------other_list：报销单子表其他费用-------------------------------------------*/

  other_list_rel: Optional[List["ReimburseOtherModel"]] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ReimburseOtherModel.reimburse_id",
      "primaryjoin": "ReimburseModel.id == ReimburseOtherModel.reimburse_id",
    }
  )

  @computed_field
  @property
  def other_list(self) -> Optional[List["ReimburseOtherModel"]]:
    try:
      return self.other_list_rel
    except:
      return None

  @other_list.setter
  def other_list(self, value: Optional[List["ReimburseOtherModel"]]) -> None:
    pass

  # /*---------------------------------------amount：报销单花费金额-------------------------------------------*/

  @computed_field
  @property
  def amount(self) -> Decimal:
    ret = Decimal(0)
    for other_item in (self.other_list or []):
      ret = ret + (Decimal(other_item.amount) if other_item.amount is not None else 0)
    for travel_item in (self.travel_list or []):
      ret = ret + (Decimal(travel_item.amount) if travel_item.amount is not None else 0)
    return ret

  @amount.setter
  def amount(self, value: decimal) -> None:
    pass

  # /*---------------------------------------approve_id：报销单所关联的审批单-------------------------------------------*/

  approve_id: str = Field(
    default=None,
    description="关联审批单的ID",
    foreign_key="pl_approve.id",  # 添加外键约束
    nullable=True
  )

  approve_rel: Optional["ApproveModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ReimburseModel.approve_id",
      "remote_side": "ApproveModel.id",
      "uselist": False
    }
  )

  @computed_field
  @property
  def approve(self) -> Optional[ApproveModel]:
    try:
      return self.approve_rel
    except:
      return None

  @approve.setter
  def approve(self, value: Optional[ApproveModel]) -> None:
    pass

  # /*---------------------------------------user_id：报销单申请人-------------------------------------------*/

  user_id: str = Field(
    default=None,
    description="项目成员id",
    foreign_key="pl_user.id",  # 添加外键约束
    nullable=True
  )

  user_rel: Optional["UserServiceModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ReimburseModel.user_id",
      "remote_side": "UserServiceModel.id",
      "uselist": False
    }
  )

  @computed_field
  @property
  def user(self) -> Optional[UserServiceModel]:
    try:
      return self.user_rel
    except:
      return None

  @user.setter
  def user(self, value: Optional[UserServiceModel]) -> None:
    pass


ReimburseService = create_model_service(
  Cls=ReimburseModel,
  custom_query=lambda: select(ReimburseModel)
  .options(
    selectinload(ReimburseModel.proj_rel),

    selectinload(ReimburseModel.travel_list_rel),
    selectinload(ReimburseModel.other_list_rel),

    selectinload(ReimburseModel.approve_rel),
    selectinload(ReimburseModel.user_rel),
  )
)
