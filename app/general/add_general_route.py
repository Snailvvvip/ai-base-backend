from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.general.perform_general_operation import perform_general_operation
from app.utils.db_utils import AsyncSessionDep


def add_general_route(app: FastAPI):
  types = ['list', 'item', 'insert', 'update', 'delete', 'batch_insert', 'batch_update']
  for type in types:
    @app.post("/general/{module}/" + type)
    async def func(module: str, query_param: dict, session: AsyncSessionDep, request: Request, type=type):
      try:
        result = await perform_general_operation(session=session, module=module, data=query_param, debug_data=[], user=request.state.user, type=type)
        if "error" in result:
          return JSONResponse(content=result, status_code=500)
        else:
          return result
      finally:
        await session.close()
