from typing import Optional

from pydantic import computed_field
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, select

from app.model.ProjectModel import ProjectModel
from app.model.PublicApproveModel import PublicApproveModel
from app.model.UserModel import UserServiceModel
from app.utils.create_module_service import create_model_service


# 自动查询project信息的审批单类
class ApproveModel(PublicApproveModel, table=True):
  __tablename__ = "pl_approve"
  __table_args__ = {'extend_existing': True}

  llm_flag: Optional[bool] = Field(default=None, description="LLM审核是否通过表示")
  llm_reason: Optional[str] = Field(default=None, description="LLM审核不通过原因")

  # /*---------------------------------------project-------------------------------------------*/

  proj_id: str = Field(
    default=None,
    description="所属项目id",
    foreign_key="pl_project.id",  # 添加外键约束
    nullable=True
  )

  proj_rel: Optional["ProjectModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ApproveModel.proj_id",
      "remote_side": "ProjectModel.id",
      "uselist": False,
      "overlaps": "approve_list_relationship"
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

  # /*---------------------------------------user-------------------------------------------*/

  apply_user_id: str = Field(
    default=None,
    description="申请人ID",
    foreign_key="pl_user.id",
    nullable=True
  )

  apply_user_relationship: Optional["UserServiceModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "ApproveModel.apply_user_id",
      "remote_side": "UserServiceModel.id",
      "uselist": False
    }
  )

  @computed_field
  @property
  def apply_user(self) -> Optional["UserServiceModel"]:
    try:
      return self.apply_user_relationship
    except:
      return None

  @apply_user.setter
  def apply_user(self, value: Optional["UserServiceModel"]) -> None:
    pass


ApproveService = create_model_service(
  Cls=ApproveModel,
  custom_query=lambda: select(ApproveModel)
  .options(
    selectinload(ApproveModel.proj_rel),
    selectinload(ApproveModel.apply_user_relationship),
  )
)
