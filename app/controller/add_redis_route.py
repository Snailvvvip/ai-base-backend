from fastapi import FastAPI

from app.utils.redis_utils import RedisClientDep


def add_redis_route(app: FastAPI):
  @app.post("/redis_set/{key}")
  async def redis_set(key: str, value: dict, redis_client: RedisClientDep):
    await redis_client.hset(key, mapping=value)
    return {"result": "success"}

  @app.get("/redis_get/{key}")
  async def redis_get(key: str, redis_client: RedisClientDep):
    # exists = bool(await redis_client.exists(key))
    mapping = await redis_client.hgetall(key)
    exists = bool(mapping)
    return {"result": {"exists": exists, "mapping": mapping}}
