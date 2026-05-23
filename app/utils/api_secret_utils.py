from enum import Enum

from app.utils.redis_utils import redis_utils, remove_redis_cache


class ApiSecretStatus(Enum):
  valid = "valid"  # 秘钥有效
  invalid = "invalid"  # 秘钥无效
  not_exist = "not_exist"  # 秘钥不存在


class ApiSecretUtils():
  def __init__(self):
    self.cache = {}

  # 验证秘钥状态
  async def verify_secret(self, secret: str) -> ApiSecretStatus:
    async with redis_utils.get_redis_connection() as redis_client:
      cache_value = await redis_client.get(f"api_secret_status_${secret}")
      print("cache_value", cache_value)

    api_secret_status = cache_value
    print("verify_secret", api_secret_status, secret)
    return api_secret_status or ApiSecretStatus.not_exist

  # 保存秘钥状态
  async def save_secret(self, secret: str, status: ApiSecretStatus):
    print("save_secret", secret)
    async with redis_utils.get_redis_connection() as redis_client:
      await redis_client.set(f"api_secret_status_${secret}", str(status))

  # 移除秘钥缓存
  async def remove_secret(self, secret: str):
    await remove_redis_cache(f"api_secret_status_${secret}")


api_secret_utils = ApiSecretUtils()
