from fastapi import FastAPI
from sqlalchemy.sql.expression import text

from app.utils.db_utils import AsyncSessionDep


def add_test_connection_route(app: FastAPI):
  @app.get("/query_llm_user_list")
  async def query_llm_user_list(session: AsyncSessionDep):
    result = await session.execute(text("select * from llm_user"))
    return [dict(row._mapping) for row in result]

  @app.get("/query_llm_user")
  async def query_llm_user(username: str, session: AsyncSessionDep):
    result = await session.execute(text("select * from llm_user where username = :username"), {"username": username})
    list = [dict(row._mapping) for row in result]
    return {
      "result": list[0] if list else None
    }

  @app.get("/query_llm_user2")
  async def query_llm_user(username: str, session: AsyncSessionDep):
    result = await (await session.connection()).exec_driver_sql(
      "select * from llm_user where username = %s",
      tuple([username])
    )
    print("result", result)
    list = [dict(row._mapping) for row in result]
    return {
      "result": list[0] if list else None
    }
