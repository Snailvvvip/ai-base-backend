import json

import httpx
import requests
from llama_index.core.base.embeddings.base import BaseEmbedding, Embedding


class LLamaIndexEmbeddings(BaseEmbedding):
  base_url: str = ""
  api_key: str = ""
  model: str = ""
  def __init__(self, base_url, api_key, model):
    super().__init__()
    self.base_url = base_url  # API基础URL
    self.api_key = api_key  # API访问密钥
    self.model = model  # 嵌入模型名称

  def embed_documents(self, texts):
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {self.api_key}"}
    payload = {"input": texts, "model": self.model, "encoding_format": "float"}
    response = requests.post(f"{self.base_url}/embeddings",headers=headers,data=json.dumps(payload))
    response.raise_for_status()
    json_data = response.json()
    return [item["embedding"] for item in json_data["data"]]

  def embed_query(self, text):
    return self.embed_documents([text])[0]

  async def aembed_documents(self, texts):
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {self.api_key}"}
    payload = {"input": texts, "model": self.model, "encoding_format": "float"}
    async with httpx.AsyncClient() as client:
      response = await client.post(url=f"{self.base_url}/embeddings",headers=headers,json=payload)
      json_data = response.json()
    return [item["embedding"] for item in json_data["data"]]

  async def aembed_query(self, text):
    return (await self.aembed_documents([text]))[0]


  def _get_query_embedding(self, query: str) -> Embedding:
    raise Exception("_get_query_embedding: LLamaIndexEmbeddings only support async event loop.")

  async def _aget_query_embedding(self, query: str) -> Embedding:
    return await self.aembed_query(query)

  def _get_text_embedding(self, text: str) -> Embedding:
    return self.embed_query(text)

  # 下面的方法没有用，不论如何都会走_get_text_embedding
  # async def _aget_text_embedding(self, text: str) -> Embedding:
  #   return await self.aembed_query(text)
