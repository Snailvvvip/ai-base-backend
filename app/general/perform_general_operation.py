import json
from typing import Literal

from app.general.ModuleConfigModule import ModuleConfigModule
from app.general.general_utils.sql_service import sql_service
from app.utils.db_utils import AsyncSessionDep
from app.utils.redis_utils import get_redis_cache


async def perform_general_operation(
  session: AsyncSessionDep,
  module: str,
  data: dict,
  debug_data=None,
  user=None,
  type: Literal['list', 'item', 'insert', 'update', 'delete', 'batch_insert', 'batch_update'] = 'query'
):
  if debug_data is None:
    debug_data = []

  module_query_result = await get_module_config(session, module, debug_data, user)

  # print("module_query_result", module_query_result)

  if 'error' in module_query_result:
    return module_query_result

  module_config = (module_query_result.get('result', None) or {}).get('moduleConfig', None)

  if module_config is not None:
    module_config = json.loads(module_config)

  if module_config is None:
    return {
      "error": f"Can't find module config match: {module}",
      "body": module_query_result,
    }

  if type == 'list':
    return await sql_service.list(session, data, module_config, debug_data, user)
  elif type == 'item':
    return await sql_service.item(session, data, module_config, debug_data, user)
  elif type == 'insert':
    return await sql_service.insert(session, data, module_config, debug_data, user)
  elif type == 'update':
    return await sql_service.update(session, data, module_config, debug_data, user)
  elif type == 'batch_insert':
    return await sql_service.batch_insert(session, data, module_config, debug_data, user)
  elif type == 'batch_update':
    return await sql_service.batch_update(session, data, module_config, debug_data, user)
  elif type == 'delete':
    return await sql_service.delete(session, data, module_config, debug_data, user)
  else:
    return {"error": f"Can't handle operation type: {type}"}


async def get_module_config(session: AsyncSessionDep, module: str, debug_data=None, user=None):
  async def default_value_getter():
    return await sql_service.item(session, {"code": module}, ModuleConfigModule, debug_data, user)

  return await get_redis_cache(f"@@general_module_{module}", default_value_getter=default_value_getter)
