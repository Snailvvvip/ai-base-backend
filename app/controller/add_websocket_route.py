import asyncio
from typing import List, Optional

from fastapi import FastAPI, WebSocket, Query
from starlette.websockets import WebSocketState


def add_websocket_route(app: FastAPI):
  person_name_to_socket: dict[str, WebSocket] = {}

  @app.websocket("/ws")
  async def websocket_endpoint(websocket: WebSocket, name: str = Query(..., description="用户名称")):
    if person_name_to_socket.get(name, None) is not None:
      raise Exception("用户已经连接")
    print("新用户连接", name)
    # 接收连接
    await websocket.accept()
    # 保存连接
    person_name_to_socket[name] = websocket
    try:
      while True:
        # 将接收得到消息发送供其他用户
        data = await websocket.receive_text()
        for person_name, person_socket in person_name_to_socket.items():
          if person_name != name:
            await person_socket.send_text(data)

    except Exception as e:
      print(f"WebSocket error: {e}")
    finally:
      if websocket.application_state == WebSocketState.CONNECTING:
        print("关闭websocket")
        await websocket.close()
      del person_name_to_socket[name]
      print("websocket已经关闭", name)
