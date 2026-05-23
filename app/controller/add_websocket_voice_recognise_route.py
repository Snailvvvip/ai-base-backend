import json
import base64
import os
import struct
import asyncio

import websockets
import time
from fastapi import FastAPI, WebSocket, Query
from starlette.websockets import WebSocketState

from app.config.env import env
from app.utils.bailian_voice_recognise.BaiLianVoiceRecogniseSocket import BaiLianVoiceRecogniseSocket


def add_websocket_voice_recognise_route(app: FastAPI):
  @app.websocket("/ws_voice_recognise")
  async def ws_voice_recognise(receive_socket: WebSocket, user_id: str = Query(..., description="用户ID")):
    print("[音频识别]新用户连接", user_id)
    # 接收连接
    await receive_socket.accept()

    # 公共函数，用于向前端发送语音识别结果
    async def send_text(data: dict):
      await receive_socket.send_text(json.dumps(data, ensure_ascii=False))

    # 百炼识别返回的开始说话事件
    async def on_speech_started(item_id: str):
      await send_text({"type": "speech_started", "item_id": item_id})

    # 百炼识别返回的正在说话事件
    async def on_speech_content(item_id: str, content: str):
      await send_text({"type": "speech_content", "item_id": item_id, "content": content})

    # 百炼识别返回的说话结束事件
    async def on_speech_stopped(item_id: str):
      await send_text({"type": "speech_stopped", "item_id": item_id})

    # 百炼识别返回的识别完成事件
    async def on_speech_completed(item_id: str, content: str):
      await send_text({"type": "speech_completed", "item_id": item_id, "content": content})

    # 百炼识别连接错误
    async def on_connect_error(error: Exception):
      await clear_socket()

    # 创建一个百炼语音识别对象
    bvrs = BaiLianVoiceRecogniseSocket(
      on_speech_started=on_speech_started,
      on_speech_content=on_speech_content,
      on_speech_stopped=on_speech_stopped,
      on_speech_completed=on_speech_completed,
      on_connect_error=on_connect_error,
    )

    # 连接百炼websocket
    await bvrs.connect()

    async def clear_socket():
      """
      清理掉百炼以及前端的websocket连接
      """
      await bvrs.close()
      if receive_socket.application_state != WebSocketState.DISCONNECTED:
        print("关闭前端websocket")
        await receive_socket.close()
      print("前端websocket已经关闭", user_id)

    try:
      async def waiting_msg_from_front():
        """
        将前端PCM数据转发到百炼
        """
        try:
          while True:
            int16array_string = await receive_socket.receive_text()
            int16array = json.loads(int16array_string)
            # 将 int16 列表打包成 bytes
            pcm_bytes = struct.pack('<' + 'h' * len(int16array), *int16array)
            # 将二进制PCM数据转换为base64编码
            encoded_data = base64.b64encode(pcm_bytes).decode('utf-8')
            # 构造发送到百炼的事件
            audio_event = {
              "event_id": f"event_{int(time.time() * 1000)}",
              "type": "input_audio_buffer.append",
              "audio": encoded_data
            }
            await bvrs.socket.send(json.dumps(audio_event))

        except Exception as e:
          if "CloseCode.NO_STATUS_RCVD" in str(e):
            print("前端连接已断开(无状态码)")
          else:
            print(f"等待前端的消息出错: {e}")
        finally:
          await clear_socket()

      # 并发运行两个任务
      await asyncio.gather(
        # 等待前端的websocket消息，将前端传递的音频数据转发给百炼识别
        waiting_msg_from_front(),
        # 等待百炼的websocket消息，将识别结果转发给前端
        bvrs.waiting_message_from_socket(),
        return_exceptions=True
      )

    except Exception as e:
      print(f"WebSocket连接错误: {e}")
      raise e
