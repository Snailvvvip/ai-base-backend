from typing import Annotated

from langchain_core.tools import tool

from app.utils.milvus_utils import milvus_service, KnowledgeQueryParam


@tool(
  name_or_callable="tool_retrieve_documents",
  description="检索企业内部文档工具"
)
async def tool_retrieve_documents(question: Annotated[str, "用户的问题"]) -> str:
  result = await milvus_service.async_search(param=KnowledgeQueryParam(
    question=question,
    kb_code="online_document",
    top_k=10,
  ))
  return result.answer
