import json
import time
from typing import Any, List

from fastapi import APIRouter, FastAPI
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from starlette.responses import StreamingResponse


def format_ai_message(ai_message: AIMessage):
  return {
    "choices": [{
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "content": ai_message.content,
        "role": "assistant"
      }
    }],
    "created": int(time.time()),
    "id": ai_message.id,
    "usage": ai_message.response_metadata.get('token_usage')
  }


def add_async_route(
  app: FastAPI,
  runnable: Runnable,
  path: str,
  input_type: Any = None, # 设置接口的传入参数类型，input_type实际上是一个pydantic类
):
  router = APIRouter(prefix=path, tags=[path])

  _input_type = input_type or runnable.input_schema

  @router.post('/ainvoke')
  async def ainvoke(input: _input_type):
    ai_message = await runnable.ainvoke(input.model_dump())
    return format_ai_message(ai_message)

  @router.post('/abatch')
  async def abatch(inputs: List[_input_type]):
    ai_message_list = await runnable.abatch([input.model_dump() for input in inputs])
    return [format_ai_message(ai_message) for ai_message in ai_message_list]

  @router.post('/astream')
  async def astream(input: _input_type):
    async def generator_function():
      result_template = {
        "choices": [{"delta": {}, "index": 0}],
        "created": time.time(),
        "id": "",
        "usage": None
      }
      async for chunk in runnable.astream(input.model_dump()):
        result_template["choices"][0]["delta"]['content'] = chunk.content
        result_template["choices"][0]["delta"]['role'] = 'assistant'

        if chunk.response_metadata.get('finish_reason') is not None:
          result_template["choices"][0]["delta"]['finish_reason'] = chunk.response_metadata.get('finish_reason')

        result_template['id'] = chunk.id
        result_template['created'] = int(time.time())
        yield f"data: {json.dumps(result_template, ensure_ascii=False)}\n\n"
      yield "data: [DONE]\n\n"

    return StreamingResponse(generator_function(), media_type="text/event-stream")

  app.include_router(router)
