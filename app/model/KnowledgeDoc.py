import asyncio
from enum import Enum
from typing import Optional

from llama_index.core import Document
from pydantic import computed_field
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, select

from app.model.BasicModel import BasicModel
from app.model.UserModel import UserServiceModel
from app.utils.create_module_service import create_model_service
from app.utils.db_utils import AsyncSessionDep
from app.utils.milvus_utils import milvus_service


class KnowledgeDocStatus(Enum):
  process = "process"
  fail = "fail"
  success = "success"


class KnowledgeDocModel(BasicModel, table=True):
  __tablename__ = "pl_knowledge_doc"

  parent_code: str = Field(default=None, description="所属知识库的code")
  name: str = Field(default=None, description="文档名称")
  status: str = Field(default=None, description="文档的处理状态")
  path: str = Field(default=None, description="文档原始文件路径")
  error: Optional[str] = Field(default=None, description="文档处理失败时的错误信息")
  content: Optional[str] = Field(default=None, description="在线可编辑文档内容")
  code: Optional[str] = Field(default=None, description="文档编码")

  # /*---------------------------------------created_by-------------------------------------------*/

  created_by: str = Field(
    default=None,
    description="创建人id",
    foreign_key="pl_user.id",
    nullable=True
  )

  creator_relationship: Optional["UserServiceModel"] = Relationship(
    sa_relationship_kwargs={
      "foreign_keys": "KnowledgeDocModel.created_by",
      "remote_side": "UserServiceModel.id",
      "uselist": False
    }
  )

  @computed_field
  @property
  def creator(self) -> Optional[UserServiceModel]:
    try:
      return self.creator_relationship
    except:
      return None

  @creator.setter
  def creator(self, value: Optional[UserServiceModel]) -> None:
    pass


# 删除文档字后，要删除文档在Milvus中对应的文档块
async def handle_after_delete(delete_cls, row_dict, session):
  await milvus_service.async_delete(delete_cls.id)


# 批量删除文档字后，要删除文档在Milvus中对应的文档块
async def handle_after_batch_delete(delete_cls_list, row_dict_list, session):
  task_list = [
    asyncio.create_task(handle_after_delete(doc_cls, {}, session))
    for doc_cls in delete_cls_list
  ]
  await asyncio.gather(*task_list)


# /*---------------------------------------KnowledgeDocService-------------------------------------------*/

# 专门给KnowledgeService使用的，用来给知识库上传文档的时候操作Mysql数据库中的doc表
KnowledgeDocService = create_model_service(
  KnowledgeDocModel,
  after_delete=handle_after_delete,
  after_batch_delete=handle_after_batch_delete
)


# /*---------------------------------------KnowledgeDocServiceWithCreator-------------------------------------------*/

def _create_document(cls: KnowledgeDocModel):
  metadata = cls.model_dump()
  # 删除metadata中的content属性值，避免将原文内容保存到元信息中
  del metadata['content']
  return Document(
    doc_id=cls.id,
    text=cls.content,
    metadata=metadata
  )


# 新建文档之后，要给对应的文档创建向量索引
async def handle_after_insert(insert_cls: KnowledgeDocModel, row_dict: dict, session: AsyncSessionDep):
  metadata = insert_cls.model_dump()
  # 删除metadata中的content属性值，避免将原文内容保存到元信息中
  del metadata['content']
  await milvus_service.async_create_index_from_documents([_create_document(insert_cls)])


# 批量新建之后，给所有对应的文档创建向量索引
async def handle_after_batch_insert(insert_cls_list: list[KnowledgeDocModel], row_dict_list: list[dict], session: AsyncSessionDep):
  document_list = [_create_document(insert_cls) for insert_cls in insert_cls_list]
  await milvus_service.async_create_index_from_documents(document_list)


# 更新文档之后，先删除文档索引再重新创建
async def handle_after_update(update_cls: KnowledgeDocModel, row_dict: dict, session: AsyncSessionDep):
  await milvus_service.async_delete(update_cls.id)
  await handle_after_insert(update_cls, row_dict, session)


# 批量更新文档之后，先删除文档索引再重新创建
async def handle_after_batch_update(update_cls_list: list[KnowledgeDocModel], row_dict_list: list[dict], session: AsyncSessionDep):
  await handle_after_batch_delete(update_cls_list, row_dict_list, session)
  await handle_after_batch_insert(update_cls_list, row_dict_list, session)


# 专门给在线文档模块使用的
KnowledgeDocServiceWithCreator = create_model_service(
  KnowledgeDocModel,
  after_insert=handle_after_insert,
  after_batch_insert=handle_after_batch_insert,
  after_update=handle_after_update,
  after_batch_update=handle_after_batch_update,
  after_delete=handle_after_delete,
  after_batch_delete=handle_after_batch_delete,
  custom_query=lambda: select(KnowledgeDocModel)
  .options(selectinload(KnowledgeDocModel.creator_relationship))
)
