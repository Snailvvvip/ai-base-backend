from typing import List, Any

from langchain_core.tools import tool


@tool(
  name_or_callable="tool_query_direct_subordinates",
  description="查询直接下级员工信息"
)
def tool_query_direct_subordinates() -> List[Any]:
  return [
    "已经查询完毕",
    {
      "component": "DirectSubordinates",
      "props": {},
    }
  ]
