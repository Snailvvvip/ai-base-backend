from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from llama_index.llms.openai_like import OpenAILike

from app.config.ai_configs import ai_configs
from app.utils.LLamaIndexEmbeddings import LLamaIndexEmbeddings


def create_llm(
  platform_code='huoshan-doubao',
  temperature=0.5,
  disable_streaming=False,
):
  _ai_config = ai_configs.get(platform_code)

  if _ai_config is None:
    raise Exception('Unknown platform code', platform_code)

  return ChatOpenAI(
    base_url=_ai_config.get('url').replace("chat/completions", ""),
    api_key=_ai_config.get('key'),
    model=_ai_config.get('model'),
    temperature=temperature,
    disable_streaming=disable_streaming,
    extra_body={"enable_thinking": False, "thinking": {"type": "disabled"}}
  )


def create_llama_index_llm(platform_code='huoshan-doubao', temperature=0.5):
  _ai_config = ai_configs.get(platform_code)

  if _ai_config is None:
    raise Exception('Unknown platform code', platform_code)

  return OpenAILike(
    api_base=_ai_config.get('url').replace("chat/completions", ""),
    api_key=_ai_config.get('key'),
    model=_ai_config.get('model'),
    temperature=temperature,
    max_tokens=None,  # 不限制最大token
    is_chat_model=True,  # 明确指定是聊天模型
    timeout=120.0,  # 增加超时时间
  )


def create_embeddings(platform_code="bailian-embedding"):
  """
  创建自定义嵌入模型实例

  参数:
  platform_code: 平台代码，用于从默认配置中查找对应平台的API信息

  返回:
  LLamaIndexEmbeddings类的实例，用于生成文本嵌入向量

  异常:
  当找不到对应平台代码的配置时抛出异常
  """
  # 从默认配置中获取指定平台的AI配置信息
  _ai_config = ai_configs.get(platform_code)

  # 检查配置是否存在
  if _ai_config is None:
    raise Exception('Unknown platform code', platform_code)

  # 创建并返回自定义嵌入模型实例
  return LLamaIndexEmbeddings(
    base_url=_ai_config.get('url').replace("/embeddings", ""),  # API基础URL
    api_key=_ai_config.get('key'),  # API密钥
    model=_ai_config.get('model')  # 嵌入模型名称
  )


def chain_log(format_func=None):
  """创建一个函数，用于在链中打印上一个管道的结果"""

  def func(val):
    print("\033[34m chain log==>>", format_func(val) if format_func is not None else val, '\033[0m')
    return val

  return func


def runnable_chain_log(format_func=None):
  """创建一个Runnable对象，用于在链中打印上一个管道的结果，如果上一个管道是字典对象，那么打印这个字典对象需要使用runnable_chain_log"""
  return RunnableLambda(chain_log(format_func))
