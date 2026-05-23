import json
from traceback import print_stack
from typing import Callable, TypedDict, Awaitable

import websockets
from websockets.client import ClientConnection

from app.config.env import env


class BaiLianVoiceRecogniseSocket:
  """
  通义千问——实时语音识别
  官方文档：https://help.aliyun.com/zh/model-studio/qwen-real-time-speech-recognition?spm=a2c4g.11186623.0.0.620e5a26eUNz80#0d1b30e0a1glp
  客户端事件：https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-client-events
  服务端事件：https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-server-events?spm=a2c4g.11186623.help-menu-2400256.d_2_6_8_1.620e5acdS0URfG
  """

  def __init__(
    self,
    # 百炼平台的api key，https://bailian.console.aliyun.com/?spm=5176.28326591.0.0.4d0555e3pzewCB&tab=model#/api-key
    api_key: str = env.llm_key_bailian,
    # 模型名称，支持“qwen3-asr-flash-realtime”与“qwen3-asr-flash-realtime-2025-10-27”
    qwen_model: str = "qwen3-asr-flash-realtime",
    # websocket接口地址
    base_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
    # 可选的附加头信息
    additional_headers: dict | None = None,
    # 是否启用vad模式，否则启用manual模式
    # vad模式：服务端自动检测语音的起点和终点（断句）。开发者只需持续发送音频流，服务端会在检测到一句话结束时自动返回最终识别结果。此模式适用于实时对话、会议记录等场景。
    # vad文档：https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-interaction-process?spm=a2c4g.11186623.0.0.16fe44488GkDZB#9b49887720jcw
    # manual模式：由客户端控制断句。客户端需要发送完一整句话的音频后，再发送一个input_audio_buffer.commit事件来通知服务端。此模式适用于客户端能明确判断语句边界的场景，如聊天软件中的发送语音。
    # manual文档：https://help.aliyun.com/zh/model-studio/qwen-asr-realtime-interaction-process?spm=a2c4g.11186623.0.0.16fe44488GkDZB#ee09a3493fsuc
    enable_server_vad: bool = True,

    # 监听开始说话动作，参数为item_id
    on_speech_started: Callable[[str], Awaitable[None]] | None = None,
    # 监听正在说话的内容，参数为item_id以及本次说话叠加的完整内容
    on_speech_content: Callable[[str, str], Awaitable[None]] | None = None,
    # 监听说话结束动作，参数为item_id
    on_speech_stopped: Callable[[str], Awaitable[None]] | None = None,
    # 监听说话完毕动作，参数为item_id以及本次说话万恒内容
    on_speech_completed: Callable[[str, str], Awaitable[None]] | None = None,
    # 连接错误处理
    on_connect_error: Callable[[Exception], Awaitable[None]] | None = None,
  ):
    """
    构造函数，会自动设置连接百炼实时语音识别websocket接口所需要的秘钥，模型名称，websocket接口地址，以及可选的附加头信息
    """
    self.api_key = api_key
    self.qwen_model = qwen_model
    self.base_url = base_url
    self.additional_headers = additional_headers or {}
    self.enable_server_vad = enable_server_vad

    self.on_speech_started = on_speech_started
    self.on_speech_content = on_speech_content
    self.on_speech_stopped = on_speech_stopped
    self.on_speech_completed = on_speech_completed
    self.on_connect_error = on_connect_error

    socket: ClientConnection | None = None
    self.socket = socket

  @staticmethod
  def log(message):
    print("BaiLianVoiceRecognise: " + message)

  async def connect(self):
    """
    连接websocket接口，得到socket对象
    """
    url = f"{self.base_url}?model={self.qwen_model}"
    headers = {
      "Authorization": f"Bearer {self.api_key}",
      "OpenAI-Beta": "realtime=v1",
      **self.additional_headers,
    }
    self.socket = await websockets.connect(url, additional_headers=headers)

    await self.send_session_update_event()

  async def send_session_update_event(self):
    """
    发送session.update事件，通知百炼接口启用vad模式还是manual模式
    """
    if not self.socket:
      raise Exception("请先调用connect方法初始化websocket连接")
    # 会话更新事件
    event_manual = {
      "event_id": "event_123",
      "type": "session.update",
      "session": {
        "modalities": ["text"],
        "input_audio_format": "pcm",
        "sample_rate": 16000,
        "input_audio_transcription": {
          # 语种标识，可选，如果有明确的语种信息，建议设置
          "language": "zh"
          # 语料，可选，如果有语料，建议设置以增强识别效果
          # "corpus": {
          #     "text": ""
          # }
        },
        "turn_detection": None
      }
    }
    event_vad = {
      "event_id": "event_123",
      "type": "session.update",
      "session": {
        "modalities": ["text"],
        "input_audio_format": "pcm",
        "sample_rate": 16000,
        "input_audio_transcription": {
          "language": "zh"
        },
        "turn_detection": {
          "type": "server_vad",
          "threshold": 0.2,
          "silence_duration_ms": 800
        }
      }
    }
    if self.enable_server_vad:
      await self.socket.send(json.dumps(event_vad))
    else:
      await self.socket.send(json.dumps(event_manual))

  async def waiting_message_from_socket(self):
    """将百炼识别结果转发到客户端"""
    try:
      async for message in self.socket:
        data = json.loads(message)
        print("data", data)

        message_data_type = data.get('type', None)
        message_data_item_id = data.get('item_id', None)

        if message_data_type == "input_audio_buffer.speech_started":
          await self.on_speech_started(message_data_item_id)
        if message_data_type == "conversation.item.input_audio_transcription.text":
          await self.on_speech_content(message_data_item_id, data.get('stash', ""))
        if message_data_type == "input_audio_buffer.speech_stopped":
          await self.on_speech_stopped(message_data_item_id)
        if message_data_type == "conversation.item.input_audio_transcription.completed":
          await self.on_speech_completed(message_data_item_id, data.get('transcript', ""))

    except Exception as e:
      print_stack(e)
      print(f"等待百炼的消息出错: {e}")
      await self.on_connect_error(e)

  async def close(self):
    """
    关闭websocket连接
    """
    if self.socket:
      try:
        print("准备关闭百炼websocket")
        await self.socket.close()
        print("百炼websocket已经关闭")
      except:
        pass
      finally:
        self.socket = None


class BaiLianRecogniseMessage(TypedDict):
  event_id: str
  type: str
  item_id: str
  content_index: int
  text: str
  stash: str
