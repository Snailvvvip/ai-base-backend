from fastapi import FastAPI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langserve import add_routes
from pydantic import Field

from app.utils.ModelInputSchema import ModelInputSchema
from app.utils.llm_utils import create_llm


class ModelInputSchema2(ModelInputSchema):
  language: str = Field(..., description="要求模型回答使用的语言")


_doubao_chain2 = (
  ChatPromptTemplate.from_messages([
    ('system', "你需要使用语言“{language}”来回答用户的问题, 不论如何，你必须使用“{language}”来回答用户"),
    MessagesPlaceholder(variable_name="messages")
  ]) |
  create_llm() |
  StrOutputParser()
)


def add_custom_chat_playground_route(app: FastAPI):
  add_routes(
    app=app,
    runnable=_doubao_chain2,
    input_type=ModelInputSchema2,
    path="/doubao2"
  )

  add_routes(
    app=app,
    runnable={
               "messages": lambda x: x['messages'],
               "language": lambda x: "英语"
             } | _doubao_chain2,
    input_type=ModelInputSchema,
    path="/doubao2_playgroud",
  )
