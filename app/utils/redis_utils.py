import json
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Annotated, AsyncContextManager, Any, Callable

import redis.asyncio as redis
from fastapi import Depends

from app.config.env import env

# 设置日志，方便调试
logger = logging.getLogger(__name__)


class RedisUtils:
  def __init__(self):
    self.redis_pool: redis.ConnectionPool | None = None

  # 1. 优化连接池初始化：加入心跳和保活机制
  async def check_redis_connection(self):
    """初始化连接池并执行读写测试"""
    self.redis_pool = redis.ConnectionPool(
      host=env.redis_host,
      port=env.redis_port,
      password=env.redis_password,
      db=env.redis_db,
      encoding="utf-8",
      decode_responses=True,
      # --- 解决 10054 报错的核心配置 ---
      health_check_interval=5,  # 每5秒自动发送PING，保持连接活跃
      socket_keepalive=True,  # 启用TCP层面的保活探测
      socket_connect_timeout=3,  # 连接超时设置
      retry_on_timeout=True,  # 遇到超时自动重试一次
    )

    # 立即对redis做一次读写测试
    async with self.get_redis_connection() as redis_client:
      try:
        await redis_client.ping()
        random_id = str(uuid.uuid4())
        await redis_client.set("__init__setup__", random_id, ex=10)  # 设置10秒过期
        cache_random_id = await redis_client.get("__init__setup__")

        if cache_random_id != random_id:
          raise Exception("Redis 读写测试一致性校验失败")

        print("✅ Redis connection successful：", f"redis://{env.redis_password}@${env.redis_host}:{env.redis_port}/{env.redis_db}")
      except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise e

  # 2. 获取连接：利用连接池自动管理，无需手动关闭 client
  @asynccontextmanager
  async def get_redis_connection(self) -> AsyncContextManager[redis.Redis]:
    if self.redis_pool is None:
      await self.check_redis_connection()

    # 异步连接池中，Redis 实例创建很轻量
    # 上下文管理器结束后，它会自动将连接归还给 pool，而不是物理断开
    redis_client = redis.Redis(connection_pool=self.redis_pool)
    try:
      yield redis_client
    except Exception as e:
      logger.error(f"Redis Connection Error: {e}")
      raise

  # 3. 清理连接池
  async def close_redis_connection(self):
    if self.redis_pool:
      await self.redis_pool.disconnect()
      print("🚀 Redis connection pool closed.")


redis_utils = RedisUtils()


# --- FastAPI 依赖注入 ---
async def get_redis_client() -> redis.Redis:
  async with redis_utils.get_redis_connection() as redis_client:
    yield redis_client


RedisClientDep = Annotated[redis.Redis, Depends(get_redis_client)]


async def get_redis_cache(key: str, default_value_getter):
  """
  从redis中获取key的缓存，如果没有值则执行默认值获取函数，并保存到redis中
  @param  key                         缓存的key
  @param  default_value_getter        如果缓存值不存在的情况下则调用异步函数 default_value_getter 来获取默认值，这个函数的返回值必须是一个字典 dict
  """
  async with redis_utils.get_redis_connection() as redis_client:
    # default_value_getter返回的字段可能嵌套多层对象，这里改成用json字符串缓存
    json_string = await redis_client.get(key)
    exists = False if json_string == "{}" else bool(json_string)
    # print("exists", exists)
    if exists:
      return json.loads(json_string)
    else:
      value = await default_value_getter()
      print("value", value)
      if value is not None:
        new_value = {k: v for k, v in value.items() if v is not None}
        await redis_client.set(key, json.dumps(new_value, ensure_ascii=False))
      return value


# 删除redis缓存
async def remove_redis_cache(key: str):
  async with redis_utils.get_redis_connection() as redis_client:
    result = await redis_client.delete(key)
    return result > 0  # 返回是否删除成功
