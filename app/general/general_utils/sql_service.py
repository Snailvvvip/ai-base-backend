import datetime
import traceback

from app.config.env import env
from app.general.general_interceptors import invoke_interceptor
from app.general.general_utils.build_delete_sql import build_delete_sql
from app.general.general_utils.build_insert_sql import build_insert_sql
from app.general.general_utils.build_query_sql import build_query_sql
from app.general.general_utils.build_update_sql import build_update_sql
from app.general.general_utils.sql_utils import get_value, create_convertor
from app.model.UserModel import UserServiceModel
from app.utils.db_utils import AsyncSessionDep


def get_default_orders(query_config, module_config):
  orders = get_value(query_config, 'orders', None)
  if orders is not None:
    return orders
  module_config_default_orders = get_value(
    get_value(module_config, 'default', {}),
    'orders',
    None
  )
  if module_config_default_orders is not None:
    return module_config_default_orders
  return {"field": "createdAt", "desc": True}


async def get_id(session: AsyncSessionDep, len: int | None = 1):
  conn = await session.connection()
  if len is None:
    len = 1
  sql = f"select {','.join([f'uuid() as _{idx}' for idx in range(len)])}"
  result = await conn.exec_driver_sql(sql)
  result = [dict(row._mapping) for row in result]

  return [val for key, val in result[0].items()]


async def list(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  conn = await session.connection()

  n_page = get_value(query_config, 'page', 0)
  n_size = get_value(query_config, 'size', 5)
  n_only_count = get_value(query_config, 'onlyCount', False)
  n_with_count = get_value(query_config, 'withCount', False)

  offset = n_page * n_size
  # 多查一条数据，方便判断是否有下一页数据
  size = n_size + 1

  target_query_config = {
    **query_config,
    "offset": offset,
    "size": size,
    "orders": get_default_orders(query_config, module_config)
  }

  await invoke_interceptor('before_list', module_config['base'], query_config=target_query_config, session=session, user=user)

  sql, values = build_query_sql(target_query_config, module_config)

  try:

    debug_data.append({"sql": sql, "values": values})
    result = await conn.exec_driver_sql(sql, tuple(values))
    result = [dict(row._mapping) for row in result]

    create_convertor(module_config)['decode_list'](result)

    await invoke_interceptor('after_list', module_config['base'], rows=result, session=session, user=user)

    if n_only_count:
      return {
        "total": int(result[0]['total'])
      }
    else:
      has_next = False if get_value(query_config, 'all', False) else len(result) == n_size + 1
      if has_next:
        result.pop()

      count_result = await list(
        session,
        query_config={**query_config, "onlyCount": True},
        module_config=module_config,
        debug_data=debug_data,
        user=user
      ) if n_with_count else {}
      return {
        "hasNext": has_next,
        **count_result,
        "list": result,
      }
  except Exception as err:
    print(err)
    traceback.print_exc()
    return {
      "error": f"Error: {err}",
    }


async def item(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  target_query_config = {
    "offset": 0,
    "size": 1,
    "filters": [],
    "orders": {"field": "createdAt", "desc": True},
  }
  for humpName, value in query_config.items():
    target_query_config['filters'].append({
      "field": humpName,
      "value": value,
      "operator": "="
    })

  result = await list(session=session, query_config=target_query_config, module_config=module_config, debug_data=debug_data, user=user)

  if "error" in result:
    return result

  return {"result": None if "list" not in result or len(result['list']) == 0 else result['list'][0]}


async def insert(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  conn = await session.connection()

  row = get_value(query_config, 'row', None)
  if row is None:
    return {
      "error": "row parameter is missing",
    }
  create_convertor(module_config)['encode_list']([row])

  row_id = get_value(row, 'id', None)

  # 自动设置row_id
  if row_id is None:
    row_id = (await get_id(session, 1))[0]
    row['id'] = row_id

  # 自动设置创建时间
  if get_value(row, 'createdAt', None):
    row['createdAt'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  # 自动设置更新时间
  if get_value(row, 'updatedAt', None):
    row['updatedAt'] = row['createdAt']

  if user:
    row['createdBy'] = user.id
    row['updatedBy'] = user.id

  await invoke_interceptor('before_insert', module_config['base'], row=row, session=session, user=user)

  try:
    sql, values = build_insert_sql(module_config, row)

    debug_data.append({"sql": sql, "values": values})
    await conn.exec_driver_sql(sql, tuple(values))
    await session.commit()

    result = await item(session, query_config={"id": row_id}, module_config=module_config, debug_data=debug_data)

    if "error" in result:
      return result

    item_dict = get_value(result, 'result', None)

    await invoke_interceptor('after_insert', module_config['base'], row=item_dict, session=session, user=user)

    if item_dict is not None:
      return {
        "result": item_dict
      }
    else:
      return {
        "error": "insert failed, query result is empty",
      }

  except Exception as err:
    print(err)
    traceback.print_exc()
    return {
      "error": f"Error: {err}",
    }


async def batch_insert(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  conn = await session.connection()

  rows = get_value(query_config, 'rows', None)
  if rows is None or len(rows) == 0:
    return {
      "error": "rows parameter is missing",
    }
  create_convertor(module_config)['encode_list'](rows)

  # 自动填充row id
  rows_without_id = [row for row in rows if get_value(row, 'id', None) is None]
  if rows_without_id:
    new_id_list = await get_id(session, len(rows_without_id))
    for index, row in enumerate(rows_without_id):
      row['id'] = new_id_list[index]

  for row in rows:
    # 自动设置创建时间
    if get_value(row, 'createdAt', None):
      row['createdAt'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 自动设置更新时间
    if get_value(row, 'updatedAt', None):
      row['updatedAt'] = row['createdAt']

    if user:
      row['createdBy'] = user.id
      row['updatedBy'] = user.id

  await invoke_interceptor('before_batch_insert', module_config['base'], rows=rows, session=session, user=user)

  try:
    for row in rows:
      sql, values = build_insert_sql(module_config, row)
      debug_data.append({"sql": sql, "values": values})
      await conn.exec_driver_sql(sql, tuple(values))

    await session.commit()

    row_id_list = [row['id'] for row in rows]
    query_config = {"all": True, "filters": [{"field": "id", "operator": "in", "value": row_id_list}]}

    result = await list(session, query_config=query_config, module_config=module_config, debug_data=debug_data)
    result = get_value(result, 'list', [])

    if len(result) > 0:

      await invoke_interceptor('after_batch_insert', module_config['base'], rows=result, session=session, user=user)

      return {
        "result": result
      }
    else:
      return {
        "error": "insert failed, query result is empty",
      }

  except Exception as err:
    print(err)
    traceback.print_exc()
    return {
      "error": f"Error: {err}",
    }


async def update(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  conn = await session.connection()

  row = get_value(query_config, 'row', None)
  update_by_fields = get_value(query_config, 'updateByFields', env.default_update_by_fields)

  if row is None:
    return {
      "error": "row parameter is missing",
    }

  row_id = get_value(row, 'id', None)

  if row_id is None:
    return {
      "error": "row is missing field: id",
    }

  row['updatedAt'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  if user:
    row['updatedBy'] = user.id

  create_convertor(module_config)['encode_list']([row])

  await invoke_interceptor('before_update', module_config['base'], row=row, session=session, user=user)

  try:
    sql, values = build_update_sql(module_config, row, row.keys() if update_by_fields else None)

    debug_data.append({"sql": sql, "values": values})
    await conn.exec_driver_sql(sql, tuple(values))
    await session.commit()

    result = await item(session, query_config={"id": row_id}, module_config=module_config, debug_data=debug_data)

    if "error" in result:
      return result

    item_dict = get_value(result, 'result', None)

    await invoke_interceptor('after_update', module_config['base'], row=item_dict, session=session, user=user)

    if item_dict is not None:
      return {
        "result": item_dict
      }
    else:
      return {
        "error": "update failed, query result is empty",
      }

  except Exception as err:
    print(err)
    traceback.print_exc()
    return {
      "error": f"Error: {err}",
    }


async def batch_update(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  conn = await session.connection()

  rows = get_value(query_config, 'rows', None)
  update_by_fields = get_value(query_config, 'updateByFields', env.default_update_by_fields)

  if rows is None or len(rows) == 0:
    return {
      "error": "rows parameter is missing",
    }
  create_convertor(module_config)['encode_list'](rows)

  rows_without_id = [row for row in rows if get_value(row, 'id', None) is None]
  if rows_without_id:
    return {
      "error": "row is missing field: id",
      "rows": rows_without_id,
    }

  current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  for row in rows:
    row['updatedAt'] = current_datetime
    if user:
      row['updatedBy'] = user.id

  await invoke_interceptor('before_batch_update', module_config['base'], rows=rows, session=session, user=user)

  try:
    for row in rows:
      sql, values = build_update_sql(module_config, row, row.keys() if update_by_fields else None)
      debug_data.append({"sql": sql, "values": values})
      await conn.exec_driver_sql(sql, tuple(values))

    await session.commit()

    row_id_list = [row['id'] for row in rows]
    query_config = {"all": True, "filters": [{"field": "id", "operator": "in", "value": row_id_list}]}

    result = await list(session, query_config=query_config, module_config=module_config, debug_data=debug_data)
    result = get_value(result, 'list', [])

    if len(result) > 0:

      await invoke_interceptor('after_batch_update', module_config['base'], rows=result, session=session, user=user)

      return {
        "result": result
      }
    else:
      return {
        "error": "update failed, query result is empty",
      }

  except Exception as err:
    print(err)
    traceback.print_exc()
    return {
      "error": f"Error: {err}",
    }


async def delete(session: AsyncSessionDep, query_config, module_config, debug_data=[], user: UserServiceModel | None = None):
  conn = await session.connection()

  id = get_value(query_config, 'id', None)
  if id is None:
    return {
      "error": "id parameter is missing",
    }

  await invoke_interceptor('before_delete', module_config['base'], query_config=query_config, session=session, user=user)

  try:
    sql, values = build_delete_sql(module_config, id)
    debug_data.append({"sql": sql, "values": values})
    result = await conn.exec_driver_sql(sql, tuple(values))
    await session.commit()
    deleted_rows = result.rowcount

    if deleted_rows >= 1:

      await invoke_interceptor('after_delete', module_config['base'], query_config=query_config, session=session, user=user)

      return {"deletedRows": deleted_rows}
    else:
      return {"error": f"delete failed, delete rows is {deleted_rows}", }
  except Exception as err:
    print(err)
    traceback.print_exc()
    return {
      "error": f"Error: {err}",
    }


class SqlService():
  def __init__(self):
    self.list = list
    self.item = item
    self.insert = insert
    self.update = update
    self.delete = delete
    self.batch_insert = batch_insert
    self.batch_update = batch_update


sql_service = SqlService()
