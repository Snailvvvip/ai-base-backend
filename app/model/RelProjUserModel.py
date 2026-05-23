from typing import Optional

from pydantic import computed_field
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, select

from app.model.BasicModel import BasicModel
from app.model.PosModel import PosModel
from app.model.ProjectModel import ProjectModel
from app.model.UserModel import UserServiceModel
from app.utils.create_module_service import create_model_service


class RelProjUserModel(BasicModel, table=True):
  __tablename__ = "pl_rel_proj_user"

  # /*---------------------------------------user_id-------------------------------------------*/

  user_id: str = Field(
    default=None,
    description="项目成员id",
    foreign_key="pl_user.id",  # 添加外键约束
    nullable=True
  )

  user_rel: Optional["UserServiceModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "RelProjUserModel.user_id",
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

  # /*---------------------------------------proj_id-------------------------------------------*/

  proj_id: str = Field(
    default=None,
    description="项目id",
    foreign_key="pl_project.id",  # 添加外键约束
    nullable=True
  )

  proj_rel: Optional["ProjectModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "RelProjUserModel.proj_id",
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


RelProjUserService = create_model_service(
  Cls=RelProjUserModel,
  custom_query=lambda: select(RelProjUserModel)
  .options(
    selectinload(RelProjUserModel.user_rel).
    selectinload(UserServiceModel.position)
  )
  .options(
    selectinload(RelProjUserModel.proj_rel).
    selectinload(ProjectModel.leader)
  ),
)
