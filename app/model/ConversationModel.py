from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class ConversationModel(BasicModel, table=True):
  __tablename__ = "pl_conversation"

  title: str = Field(default=None, description="会话标题")


ConversationService = create_model_service(ConversationModel)
