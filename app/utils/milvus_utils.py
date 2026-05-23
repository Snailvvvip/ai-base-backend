import asyncio
from typing import List, Optional, Union

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from llama_index.vector_stores.milvus import MilvusVectorStore
from pydantic import BaseModel, Field

from app.config.env import env
from app.utils.llm_utils import create_embeddings, create_llm
from app.utils.nltk_utils import load_nltk


class KnowledgeQueryParam(BaseModel):
  question: str = Field(..., description="问题文本")
  kb_code: Union[str, List[str]] = Field(..., description="知识库编码")
  top_k: int = Field(default=5, description="返回结果数量")


class MilvusSearchNode(BaseModel):
  id: str = Field(..., description="文档id")
  text: str = Field(..., description="文档内容")
  metadata: dict = Field(..., description="文档元信息")
  score: float = Field(..., description="相似度分数")


class MilvusSearchResponse(BaseModel):
  answer: str = Field(..., description="根据用户问题从检索结果中提取的内容")
  nodes: List[MilvusSearchNode] = Field(..., description="搜索结果")


class MilvusService:
  def __init__(self):
    milvus_vector_store: Optional[MilvusVectorStore] = None
    self._milvus_vector_store = milvus_vector_store

    self.embeddings = create_embeddings()

  # 获取一个MilvusVectorStore实例，如果不存在就异步创建
  async def get_vector_store(self):
    if not self._milvus_vector_store:
      print("create new_vector_store...")
      self._milvus_vector_store = MilvusVectorStore(
        uri=env.milvus_uri,
        user=env.milvus_username,
        password=env.milvus_password,

        db_name=env.llama_index_database,
        collection_name=env.llama_index_collection,
        dim=env.llama_index_dimension,

        embedding_field="embedding",
        # text_field="text",  # 添加文本字段支持混合检索
        id_field="id",
        similarity_metric="COSINE",
        consistency_level="Strong",
        overwrite=False,
        # enable_hybrid=True,  # 启用混合检索
      )
    return self._milvus_vector_store

  # 检查Milvus连接是否正常
  async def check_milvus_connection(self):
    await asyncio.sleep(0.5)
    await self.async_search(KnowledgeQueryParam(question="hello", kb_code=""))
    print("✅ Milvus connection successful：", f"Milvus://{env.milvus_username}:{env.milvus_password}@{env.milvus_uri}/{env.llama_index_database}/{env.llama_index_collection}")

  async def async_create_index_from_documents(self, documents: List[Document]) -> VectorStoreIndex:
    vector_store = await self.get_vector_store()
    """异步创建向量索引并插入文档"""
    vector_index: VectorStoreIndex = VectorStoreIndex.from_vector_store(
      vector_store=vector_store,
      embed_model=self.embeddings,
    )

    from llama_index.core.node_parser import SimpleNodeParser
    # parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[2048, 512, 128])
    parser = SimpleNodeParser()
    # nodes = await parser.aget_nodes_from_documents(documents)
    # 使用同步方法并包装在 asyncio.to_thread 中
    nodes = await asyncio.to_thread(parser.get_nodes_from_documents, documents)
    await vector_index.ainsert_nodes(nodes)
    return vector_index

  # 检索milvus文档
  async def async_search(self, param: KnowledgeQueryParam) -> MilvusSearchResponse:
    """异步向量搜索"""
    # 创建查询引擎，设置top_k参数
    vector_index = VectorStoreIndex.from_vector_store(
      vector_store=await self.get_vector_store(),
      embed_model=self.embeddings,
    )

    filters = MetadataFilters(filters=[MetadataFilter(key="parent_code", value=param.kb_code, operator=FilterOperator.IN if isinstance(param.kb_code, list) else FilterOperator.EQ)])

    retriever = vector_index.as_retriever(
      retriever_mode="hybrid",  # 启用混合模式
      filters=filters,
      similarity_top_k=param.top_k
    )

    result_nodes = await retriever.aretrieve(param.question)

    [print(node.node.metadata.get('name', None), node.score) for node in result_nodes]

    result_nodes = [node for node in result_nodes if node.score >= 0.3]

    chain = ChatPromptTemplate.from_template("""
        请从context标签中的内容提取与用户有关的内容来回答用户问题，如果不存在与用户问题相关的内容，请回答"在提供的资料中未找到相关信息"；

        <context>
        {context}
        </context>

        处理要求：
        - 不要添加检索结果之外的额外知识
        - 回答时优先使用检索结果中的原文表述

        用户的问题是：{question}
      """) | create_llm(disable_streaming=True) | StrOutputParser()

    rag_context = "\n-----------------分隔符------------------\n".join([
      f"""
文件名：{node.node.metadata.get('name', "未命名文件.txt")}
文件内容:
{node.node.text}
    """ for node in result_nodes
    ])

    chain_input = {"context": rag_context, "question": param.question}

    print("chain_input", chain_input)
    relative_content = await chain.ainvoke(chain_input)

    # print("milvus search answer", relative_content)
    # print("milvus search nodes", [node.node.text for node in result_nodes])

    return MilvusSearchResponse(
      answer=relative_content,
      nodes=[
        MilvusSearchNode(
          id=node.node.node_id,
          text=node.node.text,
          metadata=node.node.metadata,
          score=node.score
        )
        for node in result_nodes
      ]
    )

  async def async_delete(self, doc_id: str):
    vector_index = VectorStoreIndex.from_vector_store(
      vector_store=await self.get_vector_store(),
      embed_model=self.embeddings,
    )
    await vector_index.adelete_ref_doc(doc_id)
    return None


# 全局实例
milvus_service = MilvusService()
