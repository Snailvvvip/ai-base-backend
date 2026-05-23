from datetime import datetime

from fastapi import FastAPI
from sqlmodel import select, or_, and_

from app.model.LlmProduct import LlmProduct
from app.model.LlmUser import LlmUser
from app.utils.db_utils import AsyncSessionDep


def add_test_sqlmodel_route(app: FastAPI):
  @app.get("/llm_user_list")
  async def llm_user_list(session: AsyncSessionDep):
    query = select(LlmProduct)
    query = query.where(
      or_(
        and_(
          LlmProduct.name.not_in(['手机', '电脑', '相机']),
          LlmProduct.price > 1000,
        ),
        LlmProduct.price == 300,
      )
    )
    result = await session.execute(query)

    print(type(result), result)
    return {
      # "first": result.scalars().first(),
      "all": result.scalars().all(),
    }

  @app.post("/llm_user")
  async def llm_user(product_dict: dict, session: AsyncSessionDep):
    _product_cls = LlmProduct.model_validate(product_dict)
    return {
      "product": product_dict,
      "_product": _product_cls,
    }
