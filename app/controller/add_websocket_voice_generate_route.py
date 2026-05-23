import sys
import threading
from io import BufferedWriter

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from starlette.websockets import WebSocket

import dashscope
from dashscope.audio.tts import SpeechSynthesizer

from app.config.env import env

dashscope.api_key = env.llm_key_bailian


def add_websocket_voice_generate_route(app: FastAPI):
  @app.post("/voice_generate")
  async def voice_generate(body: VoiceGenerateParamSchema):

    result = SpeechSynthesizer.call(**body.model_dump())
    if result.get_audio_data() is not None:
      with open('output.mp3', 'wb') as f:
        f.write(result.get_audio_data())
      print('SUCCESS: get audio data: %dbytes in output.mp3' %
            (sys.getsizeof(result.get_audio_data())))
    else:
      print('ERROR: response is %s' % (result.get_response()))


class VoiceGenerateParamSchema(BaseModel):
  text: str = Field(..., description="要生成的文本")
  model: str = Field(default="sambert-zhichu-v1", description="模型名称")
  sample_rate: int = Field(default=16000, description="采样率")
  format: str = Field(default="mp3", description="音频格式")
  volume: int = Field(default=100, description="音量大小")
  rate: int = Field(default=1, description="语速")
