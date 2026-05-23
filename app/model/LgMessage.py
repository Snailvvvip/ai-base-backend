from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class LgMessage(BasicModel, table=True):
  __tablename__ = "lg_message"

  title: str = Field(default=None, description="消息标题")
  content: str = Field(default=None, description="消息内容")
  status: str = Field(default=None, description="消息的状态")
  render_configs: str = Field(default=None, description="渲染配置")


LgMessageService = create_model_service(LgMessage)
