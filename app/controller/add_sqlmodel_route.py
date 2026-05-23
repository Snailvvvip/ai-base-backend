from fastapi import FastAPI, HTTPException
from sqlmodel import select

from app.model.LlmUser import LlmUser
from app.utils.db_utils import AsyncSessionDep
from app.utils.next_id import next_id


def add_sqlmodel_route(app: FastAPI):
  @app.post("/llm_user/insert")
  async def llm_user_insert(user: LlmUser, session: AsyncSessionDep):
    if user.id is None:
      user.id = await next_id()

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"result": user}

  @app.post("/llm_user/update")
  async def llm_user_insert(user_dict: dict, session: AsyncSessionDep):

    if user_dict.get("id") is None:
      raise HTTPException(status_code=500, detail="Update row missing id")

    update_user = (await session.execute(select(LlmUser).where(LlmUser.id == user_dict["id"]))).first()
    if update_user is None:
      raise HTTPException(status_code=500, detail="Update row not found")

    for key, value in user_dict.items():
      setattr(update_user, key, value)

    session.add(update_user)
    await session.commit()
    await session.refresh(update_user)
    return {"result": update_user}

  @app.post("/llm_user/delete")
  async def llm_user_delete(user_dict: dict, session: AsyncSessionDep):

    if user_dict.get("id") is None:
      raise HTTPException(status_code=500, detail="Update row missing id")

    delete_user: LlmUser = (await session.execute(select(LlmUser).where(LlmUser.id == user_dict["id"]))).first()

    if delete_user is None:
      raise HTTPException(status_code=500, detail="Delete row not found")

    await session.delete(delete_user)
    await session.commit()

    return {"result": True}
