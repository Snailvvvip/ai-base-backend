from fastapi import FastAPI
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.controller.add_hotel_route import create_book_hotel_graph
from app.controller.add_reimburse_route import create_reimburse_graph
from app.model.ApproveModel import ApproveService, ApproveModel
from app.utils.db_utils import AsyncSessionDep
from app.utils.postgres_checkpointer import AsyncPostgresSaverDep
from app.workflow.approve import ApproveResult


def add_approve_route(app: FastAPI):
  class ProcessApproveClass(BaseModel):
    flag: bool = Field(..., description="审批标识，是审批通过还是审批驳回")
    reason: str = Field(default=None, description="审批驳回原因")
    user_id: str = Field(..., description="审批人id")
    approve_id: str = Field(..., description="审批单id")

  # 审批接口
  @app.post('/process_approve')
  async def process_approve(
    body: ProcessApproveClass,
    session: AsyncSessionDep,
    checkpointer: AsyncPostgresSaverDep,
  ):
    approve_cls: ApproveModel = await ApproveService.query_item(session, row_dict={"id": body.approve_id})
    if approve_cls.approve_from == 'reimburse':
      graph = create_reimburse_graph(session=session, checkpointer=checkpointer)
    elif approve_cls.approve_from == 'book_hotel':
      graph = create_book_hotel_graph(session=session, checkpointer=checkpointer)
    else:
      raise Exception("未知的审批来源：" + approve_cls.approve_from)

    approve_result: ApproveResult = {
      "flag": body.flag,
      "reason": body.reason,
      "user_id": body.user_id,
    }

    print('\n\n', ":::::::::::process_approve start::::::::::::", '\n\n')
    print(approve_result)
    print('\n\n', ":::::::::::process_approve end::::::::::::", '\n\n')

    return await graph.ainvoke(Command(resume=approve_result), config={"configurable": {"thread_id": body.approve_id}})
