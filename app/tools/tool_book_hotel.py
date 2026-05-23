from typing import Union, TypedDict

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import interrupt

from app.config.env import env


class BookHotelData(TypedDict):
  hotel_id: str
  proj_id: str
  user_id: str


@tool(name_or_callable="tool_book_hotel", description="一个用于预定酒店的工具")
async def tool_book_hotel(config: RunnableConfig) -> str:
  """
  触发中断，输入酒店预定表单信息
  """
  book_hotel_data: Union[BookHotelData, str] = interrupt({"title": "请输入酒店预定信息", "formCode": "bookHotel"})

  if book_hotel_data == "N":
    return f"用户选择取消预定酒店"

  hotel_id = book_hotel_data.get('hotel_id')
  proj_id = book_hotel_data.get('proj_id')
  user_id = book_hotel_data.get('user_id')
  token = config['configurable']['token']

  # print("================  tool_book_hotel  ================")
  # print("hotel_id", hotel_id)
  # print("proj_id", proj_id)
  # print("user_id", user_id)

  async with httpx.AsyncClient(timeout=60) as client:
    response = await client.post(
      url=f"http://localhost:{env.server_port}/book_hotel",
      headers={
        "Authorization": f"Bearer {token}"
      },
      json={
        "hotel_id": hotel_id,
        "user_id": user_id,
        "proj_id": proj_id,
      },
    )
  response_data = response.json()
  # print("================  response_data  ================")
  # print(response_data)
  approve_id = response_data.get('graph_state').get('input_approve_id')
  output_message = "预定成功，" + response_data.get('message')
  return [
    output_message,
    {
      "component": "Link",
      "props": {
        "to": f"/pages/approve/approve-detail?id={approve_id}",
        "children": f"{output_message}，也可以点击这里查看审批进度。"
      }
    }
  ]
