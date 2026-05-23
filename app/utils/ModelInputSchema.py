from typing import List, Union

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field


class ModelInputSchema(BaseModel):
  """Input for the chat endpoint."""

  messages: List[Union[HumanMessage, AIMessage, SystemMessage]] = Field(
    ...,
    description="当前对话中的消息历史",
  )
