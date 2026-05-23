from typing import List, Dict


class GeneralInterceptor():
  def __init__(
    self,
    module: str,
    before_list=None,
    after_list=None,
    before_insert=None,
    after_insert=None,
    before_update=None,
    after_update=None,
    before_batch_insert=None,
    after_batch_insert=None,
    before_batch_update=None,
    after_batch_update=None,
    before_delete=None,
    after_delete=None,
  ):
    self.module = module
    self.before_list = before_list
    self.after_list = after_list
    self.before_insert = before_insert
    self.after_insert = after_insert
    self.before_update = before_update
    self.after_update = after_update
    self.before_batch_insert = before_batch_insert
    self.after_batch_insert = after_batch_insert
    self.before_batch_update = before_batch_update
    self.after_batch_update = after_batch_update
    self.before_delete = before_delete
    self.after_delete = after_delete


_general_interceptors: Dict[str, GeneralInterceptor] = {}


def add_general_interceptor(interceptor: GeneralInterceptor):
  target_interceptor_list = _general_interceptors.get(interceptor.module, [])
  target_interceptor_list.append(interceptor)
  _general_interceptors[interceptor.module] = target_interceptor_list


async def invoke_interceptor(method: str, module: str, **kwargs):
  if module.startswith('/'):
    module = module[1:]
  if module.endswith('/'):
    module = module[:-1]
  match_interceptors = _general_interceptors.get(module, [])
  for item in match_interceptors:
    interceptor_method = getattr(item, method, None)  # 使用 getattr 获取方法
    if interceptor_method and callable(interceptor_method):
      await interceptor_method(**kwargs)  # 调用方法
