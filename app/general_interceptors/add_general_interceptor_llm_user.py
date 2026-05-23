from app.general.general_interceptors import add_general_interceptor, GeneralInterceptor
from app.model.UserModel import UserServiceModel, UserService
from app.utils.redis_utils import remove_redis_cache


def add_general_interceptor_llm_user():
  async def before_list(query_config, session, user):
    print("before_list:llm_user", query_config, session, user)

  async def after_list(rows, session, user):
    print("after_list:llm_user", rows, session, user)

  async def before_insert(row, session, user):
    print("before_insert:llm_user", row, session, user)

  async def after_insert(row, session, user):
    print("after_insert:llm_user", row, session, user)

  async def before_update(row, session, user):
    print("before_update:llm_user", row, session, user)
    user_cls: UserServiceModel = await UserService.query_item(session, {"id": row["id"]})
    await remove_redis_cache(f"access_token_username_{user_cls.username}")

  async def after_update(row, session, user):
    print("after_update:llm_user", row, session, user)

  async def before_batch_insert(rows, session, user):
    print("before_batch_insert:llm_user", rows, session, user)

  async def after_batch_insert(rows, session, user):
    print("after_batch_insert:llm_user", rows, session, user)

  async def before_batch_update(rows, session, user):
    print("before_batch_update:llm_user", rows, session, user)

  async def after_batch_update(rows, session, user):
    print("after_batch_update:llm_user", rows, session, user)

  async def before_delete(query_config, session, user):
    print("before_delete:llm_user", query_config, session, user)
    user_cls: UserServiceModel = await UserService.query_item(session, {"id": query_config["id"]})
    await remove_redis_cache(f"access_token_username_{user_cls.username}")

  async def after_delete(query_config, session, user):
    print("after_delete:llm_user", query_config, session, user)

  add_general_interceptor(GeneralInterceptor(
    module="llm_user",
    before_list=before_list,
    after_list=after_list,
    before_insert=before_insert,
    after_insert=after_insert,
    before_update=before_update,
    after_update=after_update,
    before_batch_insert=before_batch_insert,
    after_batch_insert=after_batch_insert,
    before_batch_update=before_batch_update,
    after_batch_update=after_batch_update,
    before_delete=before_delete,
    after_delete=after_delete,
  ))
