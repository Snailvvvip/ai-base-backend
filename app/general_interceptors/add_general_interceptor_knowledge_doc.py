import asyncio

from llama_index.core import Document

from app.general.general_interceptors import GeneralInterceptor, add_general_interceptor
from app.utils.milvus_utils import milvus_service


def add_general_interceptor_knowledge_doc():
  # 根据文档的id删除milvus中的文档块
  async def handle_delete_knowledge_doc(id: str):
    print(f"handle_delete_knowledge_doc[{id}], 根据文档的id删除milvus中的文档块")
    await milvus_service.async_delete(id)

  # 删除文档之后，要删除milvus中的文档块
  async def after_delete(query_config, session, user):
    query_config_or_row = query_config
    id_or_list = query_config_or_row['id']
    id_list = [id_or_list] if isinstance(id_or_list, str) else id_or_list
    await asyncio.gather(*[handle_delete_knowledge_doc(id) for id in id_list])

  # 创建文档
  def _create_document(row_dict: dict):
    print(f"_create_document[{row_dict['id']}], 创建文档")
    row_dict = {**row_dict}
    text = row_dict['content']
    # 删除metadata中的content属性值，避免将原文内容保存到元信息中
    del row_dict['content']
    return Document(
      doc_id=row_dict['id'],
      text=text,
      metadata=row_dict
    )

  # 新建文档之后，要给对应的文档创建文档块
  async def after_insert(row, session, user):
    await milvus_service.async_create_index_from_documents([_create_document(row)])

  # 批量新建文档之后，要给对应的文档创建文档块
  async def after_batch_insert(rows, session, user):
    document_list = [_create_document(row) for row in rows]
    await milvus_service.async_create_index_from_documents(document_list)

  # 更新文档之后，要删除对应的文档块，再重新创建
  async def after_update(row, session, user):
    await milvus_service.async_delete(row['id'])
    await after_insert(row, session, user)

  # 批量更新文档之后，要删除对应的文档块，再重新创建
  async def after_batch_update(rows, session, user):
    row_id_list = [row['id'] for row in rows]
    await after_delete({'id': row_id_list}, session, user)
    await after_batch_insert(rows, session, user)

  # 添加拦截器
  add_general_interceptor(GeneralInterceptor(
    module="knowledge_doc",
    after_insert=after_insert,
    after_batch_insert=after_batch_insert,
    after_update=after_update,
    after_batch_update=after_batch_update,
    after_delete=after_delete,
  ))
