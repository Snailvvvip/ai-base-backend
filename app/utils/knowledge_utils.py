import asyncio
import traceback
from typing import List

from fastapi import UploadFile
from llama_index.core import SimpleDirectoryReader, Document

from app.config.env import env
from app.model.FileModel import FileSaveService
from app.model.KnowledgeDoc import KnowledgeDocModel, KnowledgeDocService
from app.model.UserModel import PublicUser
from app.utils.db_utils import AsyncSessionDep, async_session
from app.utils.milvus_utils import milvus_service


class KnowledgeService:
  def __init__(self):
    pass

  # 为每个文件创建独立的 session 进行文件保存
  async def save_file_with_new_session(self, file: UploadFile):
    # 这里需要根据您的数据库配置创建新的 session
    # 假设您有一个 session factory
    async with async_session() as session:
      return await FileSaveService.saveFile(session=session, file=file, filename=file.filename, file_record={})

  # 将 file_dict_list 保存为 doc_cls_list
  async def save_knowledge_doc_list(
    self,
    session: AsyncSessionDep,
    file_dict_list: List[dict],
    kb_code: str,
    user: PublicUser,
  ):
    # 先插入文档对象

    tobe_insert_kd_list = [
      KnowledgeDocModel(
        id=file_dict["id"],
        created_by=user.id,
        name=file_dict["name"],
        path=file_dict["path"],
        parent_code=kb_code,
        status="process"
      ).model_dump()
      for file_dict in file_dict_list
    ]

    insert_cls_list: List[KnowledgeDocModel] = await KnowledgeDocService.batch_insert(session=session, row_dict_list=tobe_insert_kd_list)

    return insert_cls_list

  # 将doc_cls对应的文件创建索引保存到Milvus中
  async def process_doc_cls(self, doc_cls: KnowledgeDocModel):
    try:
      # 找到文件的保存路径
      file_path = doc_cls.path.replace(env.file_public_path, env.file_save_path)
      # 加载文件内容
      documents = await self.read_document_async(file_path=file_path)
      # 处理文档块的元信息
      documents = [
        Document(
          doc_id=doc_cls.id,
          text=doc.text,
          metadata={
            **doc.metadata,
            **doc_cls.model_dump(),
          }
        )
        for doc in documents
      ]
      # 为文档创建索引
      try:
        await milvus_service.async_create_index_from_documents(documents)
      except  Exception as e:
        raise Exception(f"为文档创建索引失败：{str(e)}")
      # 更新文档状态
      async with async_session() as session:
        await KnowledgeDocService.item_update(session, row_dict={"id": doc_cls.id, "status": "success"})
      return {}
    except Exception as e:
      print(e)
      traceback.print_exc()
      # 更新文档状态
      async with async_session() as session:
        await KnowledgeDocService.item_update(
          session,
          row_dict={
            "id": doc_cls.id,
            "status": "fail",
            "error": str(e)
          }
        )
      return {}

  # 异步读取文件
  async def read_document_async(self, file_path: str) -> List[Document]:
    try:
      def _read_document():
        reader = SimpleDirectoryReader(input_files=[file_path])
        return reader.load_data()

      documents = await asyncio.to_thread(_read_document)
      return documents
    except Exception as e:
      raise Exception(f"读取文档失败：{str(e)}")


knowledge_service = KnowledgeService()
