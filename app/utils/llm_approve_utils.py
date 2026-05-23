import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.model.KnowledgeDoc import KnowledgeDocServiceWithCreator, KnowledgeDocModel
from app.utils.db_utils import AsyncSessionDep
from app.utils.llm_utils import create_llm


class LlmApproveResult(BaseModel):
  llm_flag: bool = Field(..., description='AI审核是否通过')
  llm_reason: str | None = Field(default=None, description="审核不通过时的原因")


async def get_llm_approve_result(session: AsyncSessionDep, reimburse_dict: dict):
  try:
    reimburse_document: KnowledgeDocModel = await KnowledgeDocServiceWithCreator.query_item(session, {"code": "REIMBURSE"})
  except Exception as e:
    raise Exception(f"获取报销规范文档失败: {e}")

  chain = ChatPromptTemplate.from_template("""
          你是一名专业的报销单审核专家，你需要根据报销规范文档审核报销单信息，报销规范如<document/>标签中的内容所示：
          <document>
          {document_content}
          </document>
          报销单信息如下<reimburse/>标签中的内容所示：
          <reimburse>
          {reimburse_content}
          </reimburse>
          你需要返回一个json对象，类型为：{response_description}，其中llm_flag表示审核是否通过，为布尔值；llm_reason为审核不通过的原因，审核通过reason为空；
          """) | create_llm("bailian-qwen3-max") | StrOutputParser()

  print(":::::::::::::::报销规则:::::::::::::::::::")
  print(reimburse_document.content)

  print(":::::::::::::::报销单描述::::::::::::::::::::::::")
  reimburse_description = get_reimburse_description(reimburse_dict)
  print(reimburse_description)

  llm_response_content = await chain.ainvoke({
    "document_content": reimburse_document.content,
    "reimburse_content": reimburse_description,
    "response_description": '{"llm_flag":true, "llm_reason":""}'
  })

  print("::::::::::::::LLM审核结果:::::::::::::::::::::::")
  print(llm_response_content)

  llm_response_dict = json.loads(llm_response_content)
  return llm_response_dict


def get_reimburse_description(reimburse_dict: dict):
  if not reimburse_dict["project"]:
    raise Exception("报销单关联项目不存在")

  reimbruse_content = f"""
      报销申请人：{reimburse_dict["user"]["full_name"]}
      报销单标题：{str(reimburse_dict["title"])}
      报销单金额：{str(reimburse_dict["amount"])}
      报销单备注信息：{str(reimburse_dict["remarks"])}
      报销项目：{str(reimburse_dict["project"]["name"])}
    """

  for index, travel_item in enumerate(reimburse_dict["travel_list"]):
    reimbruse_content += f"""

      第{index + 1}条差旅费用信息：
      差旅费用名称：{travel_item["title"]}
      差旅费用类型：{travel_item["type"]}
      差旅出发时间：{travel_item["depart_time"]}
      差旅出发地点：{travel_item["depart_city"]}
      差旅到达时间：{travel_item["arrive_time"]}
      差旅到达地点：{travel_item["arrive_city"]}
      差旅报销金额：{travel_item["amount"]}
      """

  for index, other_item in enumerate(reimburse_dict["other_list"]):
    reimbruse_content += f"""

      第{index + 1}条费用信息：
      费用名称：{other_item["title"]}
      费用类型：{other_item["type"]}
      报销金额：{other_item["amount"]}
      票据类型：{other_item["recipe_type"]}
      """
  return reimbruse_content
