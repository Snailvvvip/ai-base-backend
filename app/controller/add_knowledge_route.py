import asyncio
import json
from typing import List

from fastapi import UploadFile, File, Form, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from starlette import status
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse

from app.general.perform_general_operation import perform_general_operation
from app.utils.db_utils import AsyncSessionDep
from app.utils.knowledge_utils import knowledge_service
from app.utils.llm_utils import create_llm
from app.utils.milvus_utils import milvus_service, KnowledgeQueryParam


def add_knowledge_route(app):
  @app.post("/knowledge/search")
  async def knowledge_search(param: KnowledgeQueryParam):
    return await milvus_service.async_search(param)

  @app.post("/knowledge/recall/stream")
  async def knowledge_search(body: dict):

    param = KnowledgeQueryParam(**body.get('input'))

    async def generator_function():
      search_response = await milvus_service.async_search(param)

      chain = create_llm() | StrOutputParser()

      # 先把检索结果返回前端
      yield f'data: {json.dumps({"type": "retrieve", "data": json.dumps(search_response.model_dump())}, ensure_ascii=False)}\n\n'

      external_prompt = body.get('input', {}).get('prompt', '')

      # print("external_prompt", external_prompt)

      async for chunk in chain.astream([
        SystemMessage(content=f"""你需要根据如下内容来回答用户的问题：{search_response.answer}，如果内容为'在提供的资料中未找到相关信息'，你需要根据你自己的知识来回答用户问题。""" + external_prompt),
        HumanMessage(content=param.question)
      ]):
        yield f'data: {json.dumps({"type": "messages", "data": chunk}, ensure_ascii=False)}\n\n'

    return StreamingResponse(generator_function(), media_type="text/event-stream")

  @app.post("/knowledge/qa/stream")
  async def knowledge_search(body: dict, session: AsyncSessionDep, request: Request):

    # 机器人的id，用来一会查询知识库编码以及判断机器人是否已经禁用
    qaId = body.get('input').get('qaId')
    # 聊天历史
    messages = body.get('input').get('messages')
    # 用户问题
    question = body.get('input').get('question')

    # 查询qa_bot信息
    perform_result = await perform_general_operation(
      session=session,
      module='knowledge_qa_bot',
      data={"id": qaId},
      debug_data=[],
      user=request.state.user,
      type='item'
    )
    if 'error' in perform_result:
      return JSONResponse(content={"message": perform_result.get('error')}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    qa_record_bot = perform_result.get('result', None)

    # 找不到机器人
    if not qa_record_bot:
      return JSONResponse(content={"message": f"""无法找到对应问答机器人的编号:{qaId}"""}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 机器人已经被禁用
    if qa_record_bot.get('disable') == 'Y':
      return JSONResponse(content={"message": "该问答机器人已经禁用"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 查询rel_qa_kb信息
    perform_result = await perform_general_operation(
      session=session,
      module='rel_qa_base',
      data={"all": True, "filters": [{"id": "01", "field": "qaId", "operator": "=", "value": qaId}]},
      debug_data=[],
      user=request.state.user,
      type='list'
    )

    if 'error' in perform_result:
      return JSONResponse(content={"message": perform_result.get('error')}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    rel_qa_kb_list = perform_result.get('list', [])

    kb_codes = [item.get('kbCode') for item in rel_qa_kb_list]

    async def generator_function():

      param = KnowledgeQueryParam(kb_code=kb_codes, question=question)
      search_response = await milvus_service.async_search(param)

      chain = create_llm() | StrOutputParser()

      # 先把检索结果返回前端
      yield f'data: {json.dumps({"type": "retrieve", "data": json.dumps(search_response.model_dump())}, ensure_ascii=False)}\n\n'

      external_prompt = qa_record_bot.get('prompt', '')

      print("external_prompt", external_prompt, qa_record_bot)

      async for chunk in chain.astream([
        SystemMessage(content=f"""你需要根据如下内容来回答用户的问题：{search_response.answer}，如果内容为'在提供的资料中未找到相关信息'，你需要根据你自己的知识来回答用户问题。""" + external_prompt),
        *messages,
      ]):
        yield f'data: {json.dumps({"type": "messages", "data": chunk}, ensure_ascii=False)}\n\n'

    return StreamingResponse(generator_function(), media_type="text/event-stream")

  # @app.post("/knowledge/embed_text")
  # async def knowledge_embed_text(text_list: List[str]):
  #   id_list = await next_id(len(text_list))
  #   document_list = [
  #     Document(
  #       text=text,
  #       id=id_list[index],
  #       metadata={"kb_id": "cde"}
  #     )
  #     for index, text in enumerate(text_list)
  #   ]
  #   await milvus_service.async_create_index_from_documents(document_list)
  #   search_result = await milvus_service.async_search("hello")
  #   return {
  #     "result": "嵌入成功:",
  #     "origin_documents": [document.to_dict() for document in document_list],
  #     "search_documents": search_result,
  #   }
  #
  @app.post("/knowledge/delete")
  async def knowledge_embed_text(body: dict):
    await milvus_service.async_delete(body.get('id'))
    return {
      "result": "删除成功",
    }

  @app.post("/knowledge/upload_files")
  async def knowledge_search(
    session: AsyncSessionDep,
    request: Request,
    files: List[UploadFile] = File(...),
    kb_code: str = Form(..., description="所属知识库的编码"),
  ):
    """
    批量上传文档并嵌入到向量数据库（同步响应版本）
    """
    if not files:
      raise HTTPException(status_code=400, detail="No files provided")

    # 限制文件数量
    if len(files) > 20:
      raise HTTPException(status_code=400, detail="Maximum 20 files allowed per upload")

    # 先将所有文件直接保存到本地
    task_list = [asyncio.create_task(knowledge_service.save_file_with_new_session(file=file)) for file in files]
    task_result_list = await asyncio.gather(*task_list)
    file_dict_list = [item["result"] for item in task_result_list]

    # 插入对应的文档对象记录
    doc_cls_list = await knowledge_service.save_knowledge_doc_list(
      session=session,
      file_dict_list=file_dict_list,
      kb_code=kb_code,
      user=request.state.user,
    )

    # 异步处理嵌入文档，不再等待
    [asyncio.create_task(knowledge_service.process_doc_cls(doc_cls=doc_cls)) for doc_cls in doc_cls_list]

    # 直接返回文档对象
    return {"message": f"正在处理 {len(doc_cls_list)} 个文档，请刷新列表查看文档状态。", "result": [item.model_dump() for item in doc_cls_list]}
