from fastapi import FastAPI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langserve import add_routes
from pydantic import BaseModel, Field

from app.utils.llm_utils import create_llm


class TranslateChainInputSchema(BaseModel):
  language: str = Field(..., description="要翻译的目标语言")
  input: str = Field(..., description="要翻译的内容")


translate_chain = ChatPromptTemplate.from_messages([
  ('system', '你需要把用户的内容翻译为：{language}'),
  ('user', "{input}")
]) | create_llm() | StrOutputParser()


def add_translate_route(app: FastAPI):
  add_routes(
    app=app,
    runnable=translate_chain,
    input_type=TranslateChainInputSchema,
    path="/translate",
  )
