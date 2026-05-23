
from app.utils.llm_utils import create_embeddings

# 通用测试方法，获取模型的向量维度
def get_embedding_dimension(model, test_text="test"):
  embedding = model.embed_query(test_text)
  # print("embedding", embedding)
  return len(embedding) if hasattr(embedding, '__len__') else embedding.shape[-1]


dimension = get_embedding_dimension(create_embeddings("bailian-embedding"))
print(f"模型向量维度: {dimension}")
