# 预先加载NLTK语料库以避免多线程环境中的竞争条件
import asyncio

import nltk
from nltk.data import find


# 判断nltk是否已经存在
def is_nltk_package_downloaded(package_name):
  try:
    find(f'tokenizers/{package_name}')
    return True
  except LookupError:
    return False


# 下载nltk所需要文件
def load_nltk():
  if not is_nltk_package_downloaded("punkt"):
    print("ℹ️ 下载nltk")
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')
    nltk.download('words')
    print("✅ nltk下载成功")
  else:
    print("✅ nltk已经存在，无需下载")


# 检查nltk是否已经下载，用于llama-index做文本分割
async def check_nltk():
  print("nltk_path:", nltk.data.path)
  # 预先加载NLTK语料库以避免多线程环境中的竞争条件
  # 否则在多线程环境下，parser.get_nodes_from_documents 可能会出现报错信息：'WordListCorpusReader' object has no attribute '_LazyCorpusLoader__args'
  await asyncio.wait_for(asyncio.to_thread(load_nltk), timeout=10)
