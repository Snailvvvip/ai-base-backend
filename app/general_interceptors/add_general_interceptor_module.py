from app.general.general_interceptors import add_general_interceptor, GeneralInterceptor
from app.utils.redis_utils import remove_redis_cache


def add_general_interceptor_module():
  async def before_update(row, session, user):
    module = row.get("code", None)
    await remove_redis_cache(f"@@general_module_{module}")

  add_general_interceptor(GeneralInterceptor(
    module='module',
    before_update=before_update
  ))
