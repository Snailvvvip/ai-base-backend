import asyncio
import base64
import json
import mimetypes
import os
import sys
import uuid
from http import HTTPStatus
from pathlib import PurePosixPath, Path

import requests
from fastapi import FastAPI
from pydantic import BaseModel, Field
from urllib.parse import urlparse, unquote
from app.config.env import env
from app.utils.path_join import path_join


class ImageGenerateSchema(BaseModel):
  image_url: str = Field(..., description="图片地址")
  prompt: str = Field(..., description="图片描述")
  image_size: str = Field(default="1920*1080", description="图片尺寸")


def add_image_edit_route(app: FastAPI):
  @app.post('/image-generate')
  async def image_generate(body: ImageGenerateSchema):
    return await asyncio.to_thread(sync_generate_image, body)


def sync_generate_image(param: ImageGenerateSchema):
  """
  同步生成图片方法
  """

  # 计算图片的本地访问路径
  image_url_1 = env.file_save_path + param.image_url[len(env.file_public_path):]
  if sys.platform == "win32":
    image_url_1 = path_join('D:/', image_url_1)

  print("image_url_1", image_url_1)

  # 图片文件名
  filename_with_ext = os.path.basename(param.image_url)
  # 新图片的ID
  file_id = str(uuid.uuid4())

  # 新图片所在目录
  Path(path_join(env.file_save_path, file_id)).mkdir(parents=True, exist_ok=True)
  # 新图片的public访问路径
  new_file_public_path = path_join(env.file_public_path, file_id, filename_with_ext)
  # 新图片在服务器上的保存路径
  new_file_save_path = path_join(env.file_save_path, file_id, filename_with_ext)

  # 获取图像的 Base64 编码
  # 调用编码函数，请将 "/path/to/your/image.png" 替换为您的本地图片文件路径，否则无法运行
  image = encode_file(image_url_1)

  request_payload = {
    "prompt": param.prompt,
    "image": image,
    "sequential_image_generation": "disabled",
    "stream": False,
    "optimize_prompt_optionsnew": "fast",
    "response_format": "url",
    "size": "2560x1440",
    "watermark": False,
    "model": "doubao-seedream-4-5-251128"
  }

  response = requests.post(
    url="https://ark.cn-beijing.volces.com/api/v3/images/generations",
    headers={
      "Content-Type": "application/json",
      "Authorization": f"Bearer {env.llm_key_huoshan}",
    },
    data=json.dumps(request_payload),
  )
  response.raise_for_status()
  json_data = response.json()
  print("json_data")
  print(json_data)

  if response.status_code == 200:
    url = json_data["data"][0]["url"]
    file_content = requests.get(url).content
    with open(new_file_save_path, 'wb+') as f:
      f.write(file_content)
      return {"path": new_file_public_path}
  else:
    print(f"HTTP返回码：{response.status_code}")
    print("请参考文档：https://help.aliyun.com/zh/model-studio/error-code")
    raise response

# ---用于 Base64 编码 ---
# 格式为 data:{mime_type};base64,{base64_data}
def encode_file(file_path):
  mime_type, _ = mimetypes.guess_type(file_path)
  if not mime_type or not mime_type.startswith("image/"):
    raise ValueError("不支持或无法识别的图像格式")

  try:
    with open(file_path, "rb") as image_file:
      encoded_string = base64.b64encode(
        image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"
  except IOError as e:
    raise IOError(f"读取文件时出错: {file_path}, 错误: {str(e)}")
