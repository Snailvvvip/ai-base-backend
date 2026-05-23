from typing import Annotated

from langchain_core.tools import tool

@tool(
  name_or_callable="tool_add",
  description="一个加法工具，用于计算两个数字相加"
)
def tool_add(
  number1: Annotated[float, "第一个要相加的数字"],
  number2: Annotated[float, "第二个要相加的数字"],
) -> float:
  print("\n invoke tool_add", number1, number2, '\n')

  return float(number1) + float(number2)
