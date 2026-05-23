from fastapi import FastAPI
from langchain_core.runnables import RunnableConfig
from langgraph.constants import START
from langgraph.graph import StateGraph

from app.model.ApproveModel import ApproveService, ApproveModel
from app.model.ReimburseModel import ReimburseService, ReimburseModel
from app.utils.db_utils import AsyncSessionDep
from app.utils.llm_approve_utils import get_llm_approve_result
from app.utils.postgres_checkpointer import AsyncPostgresSaverDep
from app.workflow.approve import create_approve_graph, ApproveGraphSchema


def add_reimburse_route(app: FastAPI):
  # 提交报销单接口
  @app.post('/submit_reimburse')
  async def submit_reimburse(
    reimburse: dict,
    session: AsyncSessionDep,
    checkpointer: AsyncPostgresSaverDep,
  ):
    reimburse_id = reimburse.get('id')
    # 先查一遍报销单信息
    reimburse_cls: ReimburseModel = await ReimburseService.query_item(session=session, row_dict={"id": reimburse_id})

    # 1. 没有审批单——
    # 2. 审批单为审批中状态——不处理
    # 3. 审批单为已通过状态——不处理
    # 4. 审批单为已驳回状态——
    # 5. 审批单为已撤回状态——

    # 2,3 的情况下不再提交报销单

    if reimburse_cls.approve:
      if reimburse_cls.approve.status == 'approving':
        return {"message": "报销单已提交审批，请勿重复提交！"}
      if reimburse_cls.approve.status == 'approved':
        return {"message": "报销单已通过审批，请勿重复提交！"}

    llm_response_dict = await get_llm_approve_result(session, reimburse_cls.model_dump())
    # 1,4,5 的情况下新建审批单
    # 创建审批单，使用新的审批单走审批流程

    new_approve_dict = {
      "title": f"{reimburse_cls.user.full_name} - 报销单审批",
      "description": reimburse_cls.title + (f" / {reimburse_cls.remarks}" if reimburse_cls.remarks else ""),
      "status": "approving",
      "amount": reimburse_cls.amount,
      "logs": "[]",
      "user_id": reimburse_cls.user_id,  # 先把审批人的id设置为申请人
      "apply_user_id": reimburse_cls.user_id,
      "proj_id": reimburse_cls.proj_id,
      "approve_from": "reimburse",
      **llm_response_dict,
    }
    insert_approve_cls: ApproveModel = await ApproveService.item_insert(session=session, row_dict=new_approve_dict)

    # 将审批单与报销单管理，设置报销单的approve_id为审批单的id
    await ReimburseService.item_update(session=session, row_dict={"id": reimburse_id, "approve_id": insert_approve_cls.id}, )

    reimburse_graph = create_reimburse_graph(session=session, checkpointer=checkpointer)

    graph_state = await reimburse_graph.ainvoke(
      {"input_user_id": reimburse_cls.user.id, "input_approve_id": insert_approve_cls.id, "input_amount": str(insert_approve_cls.amount)},
      config={"configurable": {"thread_id": insert_approve_cls.id}}
    )

    return {"message": "报销单提交成功！", "graph_state": graph_state}


def create_reimburse_graph(
  checkpointer: AsyncPostgresSaverDep,
  session: AsyncSessionDep,
):
  approve_graph = create_approve_graph(checkpointer, session)

  builder = StateGraph(ApproveGraphSchema)

  async def node(state: ApproveGraphSchema, config: RunnableConfig):
    print('\n\n', ":::::::::::node start::::::::::::", '\n\n')
    print(state)
    print('\n\n', ":::::::::::node end::::::::::::", '\n\n')

    graph_state = await approve_graph.ainvoke(state, config=config)
    approve_flag = graph_state.get('approve_flag')
    # 这里审批结束之后可以做一些事情，比如发送邮件、短信、微信消息等通知用户，因为没有实现对应的模块，这里就不做任何处理
    print("报销单审批流执行结束::::::::::>>>>>>>>>>>", approve_flag)
    return {}

  builder.add_node("node", node)
  builder.add_edge(START, "node")

  return builder.compile(checkpointer=checkpointer)
