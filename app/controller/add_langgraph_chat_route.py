import json
import time
from typing import Union

from fastapi import FastAPI
from langchain_core.messages import AIMessage, ToolMessage, AIMessageChunk
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.model.ConversationModel import ConversationService
from app.tools.tool_list import tool_list
from app.tools.tool_project_report import tool_project_report
from app.utils.db_utils import AsyncSessionDep
from app.utils.llm_utils import create_llm
from app.utils.postgres_checkpointer import PostgresCheckpointerManager, AsyncPostgresSaverDep


class ChatMessage(BaseModel):
  id: str = Field(..., description="消息id")
  type: str = Field(..., description="消息类型")
  content: str = Field(..., description="消息内容")


# 对话接口参数类型
class ChatParam(BaseModel):
  thread_id: str = Field(..., description="线程id")
  human_message: ChatMessage = Field(..., description="用户消息")


class ChatAgent:
  @staticmethod
  async def get_agent(system_prompt: str | None = None) -> CompiledStateGraph:
    return create_react_agent(
      model=create_llm("bailian-qwen3-max"),
      tools=tool_list,
      checkpointer=await PostgresCheckpointerManager.get_instance(),
      prompt=system_prompt or """
        - 你是一名擅长使用工具的智能助手，你需要根据用户问题来进行回答，请使用中文进行回答。
        - 当用户问题需要调用工具时再调用工具，否则按照你的知识来回答问题。
        - 你每次只能调用一个工具
        - 特别注意，特别注意，特别注意，如果工具的返回结果是一个数组，你只能回复“工具已经执行完毕”
        """
    )

  @staticmethod
  async def get_chat_state(thread_id: str):
    graph = await ChatAgent.get_agent()
    graph_state = await graph.aget_state(config={"configurable": {"thread_id": thread_id}})
    if graph_state.values.get('messages', None) is None:
      graph_state.values['messages'] = []
    return {
      **graph_state.values,
      "__interrupt__": graph_state.interrupts,
    }


def add_langgraph_chat_route(app: FastAPI):
  @app.post("/project/analysis")
  async def project_analysis(body: dict):

    return await tool_project_report.ainvoke({
      "project_name": body.get('project_name'),
      "start_time": body.get("start_time", None),
      "end_time": body.get("end_time", None),
    })

  # 流式对话接口
  @app.post("/langgraph/stream")
  async def langgraph_stream(
    body: dict,
    request: Request,
  ):
    print(":::::::::::::::::::::::::langgraph_stream:::::::::::::::::::::")
    print(body)
    print(request.state.user)
    print(request.state.token)

    stream_input = body.get('input')
    stream_config = body.get('config')
    stream_config['configurable']['token'] = request.state.token
    stream_config['configurable']['user_id'] = request.state.user.id

    print("stream_input", stream_input)
    print("stream_config", stream_config)

    # 暂时每次对话的时候清理掉对话历史
    # await checkpointer.adelete_thread(stream_config.get('configurable').get('thread_id'))

    async def generator_function():

      system_prompt = stream_input.get('system_prompt', None)
      print("system_prompt ==>> ", system_prompt)

      graph = await ChatAgent.get_agent(
        system_prompt=system_prompt
      )

      # chat_state = await ChatAgent.get_chat_state(thread_id)
      # chat_history_list = chat_state.get('messages')

      # has_emit_message_id 用来优化流式传输，避免将content为空的为AIMessageChunk发送给前端（实际上此时正在输出思考内容）
      # 第一次的时候输出，后续再输出content为空的AIMessageChunk不发送给前端
      has_emit_message_id = {}

      async for chunk in graph.astream(
        stream_input,
        config=stream_config,
        stream_mode=['messages', 'updates']
      ):
        print("chunk-------->>>>>>>>>>", chunk)

        result_template = {
          "choices": [{"delta": {}, "index": 0}],
          "created": time.time(),
          "id": "",
          "usage": None
        }

        emit_chunk = {"stream_type": chunk[0], }

        if emit_chunk['stream_type'] == "messages":

          if isinstance(chunk[1], tuple):
            if isinstance(chunk[1][1], dict):
              langgraph_node = chunk[1][1].get("langgraph_node")
              if langgraph_node == "tools" and isinstance(chunk[1][0], AIMessage):
                print("忽略工具中的message消息")
                continue

          # messages模式流式输出，此时 chunk[1][0] 为AIMessageChunk
          chunk_message = chunk[1][0]
          if not chunk_message.content:
            if has_emit_message_id.get(chunk_message.id):
              continue
        else:
          # updates模式流式输出
          for k, v in chunk[1].items():
            if k == 'agent' or k == 'tool':
              chunk_message = v.get('messages')[0]
            elif k == '__interrupt__':
              chunk_message = AIMessage(content='')
              emit_chunk['stream_type'] = 'interrupt'
              emit_chunk['interrupt'] = v[0].value

        emit_chunk = {
          **emit_chunk,
          "msg_id": chunk_message.id,
          "msg_type": chunk_message.type,
          "msg_content": chunk_message.content,
        }
        has_emit_message_id[chunk_message.id] = True

        if isinstance(chunk_message, AIMessage):
          if chunk_message.tool_calls:
            emit_chunk["tool_calls"] = chunk_message.tool_calls
        elif isinstance(chunk_message, ToolMessage):
          emit_chunk["tool_name"] = chunk_message.name
          emit_chunk["additional_kwargs"] = chunk_message.additional_kwargs

        result_template["choices"][0]["delta"]['content'] = emit_chunk
        result_template["choices"][0]["delta"]['role'] = 'assistant'

        result_template['id'] = chunk_message.id
        result_template['created'] = int(time.time())

        yield f"data: {json.dumps(result_template, ensure_ascii=False)}\n\n"
      # yield "data: [DONE]\n\n"

    return StreamingResponse(generator_function(), media_type="text/event-stream")

  # 恢复中断接口
  @app.post("/langgraph/chat_resume/{thread_id}")
  async def langgraph_chat(
    body: dict,
    thread_id: str,
    request: Request,
  ):
    graph = await ChatAgent.get_agent()
    chat_state = await ChatAgent.get_chat_state(thread_id)
    chat_history_list = chat_state.get('messages')
    graph_state = await graph.ainvoke(
      Command(resume=body.get('resume_data')),
      config={"configurable": {
        "thread_id": thread_id,
        "token": request.state.token,
        "user_id": request.state.user.id,
      }}
    )
    return {
      **graph_state,
      # 这里不需要加1，因为我们并没有往messages中增加消息
      "messages": graph_state.get('messages')[len(chat_history_list):],
    }

  # 查询聊天记录
  @app.get("/langgraph/chat_state/{thread_id}")
  async def langgraph_chat(thread_id: str):
    return await ChatAgent.get_chat_state(thread_id)  # 查询聊天记录

  # 删除聊天记录
  @app.post("/langgraph/chat_remove/{thread_id}")
  async def langgraph_chat(thread_id: str, checkpointer: AsyncPostgresSaverDep, session: AsyncSessionDep):
    await ConversationService.item_delete(session=session, row_dict={"id": thread_id})
    await checkpointer.adelete_thread(thread_id)
    return {"result": "success"}
