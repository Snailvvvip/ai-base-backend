from typing import Annotated

from langchain_core.tools import tool


@tool(
  name_or_callable="tool_multiply",
  description="一个乘法工具，用于计算两个数字相乘"
)
def tool_multiply(
  number1: Annotated[float, "第一个要相乘的数字"],
  number2: Annotated[float, "第二个要相乘的数字"],
) -> float:
  print("\n invoke tool_multiply", number1, number2, '\n')

  return float(number1) * float(number2)
