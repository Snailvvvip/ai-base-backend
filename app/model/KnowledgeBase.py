from datetime import datetime

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class KnowledgeBaseModel(BasicModel, table=True):
  __tablename__ = "pl_knowledge_base"

  code: str = Field(default=None, description="知识库编码")
  name: str = Field(default=None, description="知识库名称")


KnowledgeBaseService = create_model_service(KnowledgeBaseModel)
