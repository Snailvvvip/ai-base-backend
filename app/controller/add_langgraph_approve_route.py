import json
from operator import add
from typing import TypedDict, Annotated, List, Literal

from fastapi import FastAPI
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt, Command
from sqlalchemy.orm.sync import update

from app.model.LgApprove import LgApprove, LgApproveService
from app.model.LgMessage import LgMessageService
from app.utils.db_utils import AsyncSessionDep
from app.utils.next_id import next_id
from app.utils.postgres_checkpointer import AsyncPostgresSaverDep


def add_langgraph_approve_route(app: FastAPI):
  # 提交审批单/创建报销单
  @app.post("/lg_approve/submit")
  async def lg_approve_submit(
    row_dict: dict,
    checkpointer: AsyncPostgresSaverDep,
    session: AsyncSessionDep,
  ):
    thread_id = await next_id()
    graph = create_graph(checkpointer=checkpointer, session=session)
    config = {"configurable": {"thread_id": thread_id}}
    graph_state = await graph.ainvoke({"input_remarks": row_dict.get('remarks')}, config=config)
    print(graph_state)
    return graph_state

  @app.get("/lg_message/feedback/{thread_id}/{approve_flag}")
  async def lg_message_feedback(
    thread_id: str,
    approve_flag: str,
    checkpointer: AsyncPostgresSaverDep,
    session: AsyncSessionDep,
  ):
    graph = create_graph(checkpointer=checkpointer, session=session)
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke(Command(resume=approve_flag), config=config)


def create_graph(
  checkpointer: AsyncPostgresSaver,
  session: AsyncSessionDep,
) -> CompiledStateGraph:
  class ApproveSchema(TypedDict):
    id: str
    remarks: str
    status: str
    result_content: str

  class StateSchema(TypedDict):
    # 图的入参，需要一个报销单的备注信息，实际业务场景中，入参起码还需要有报销单申请人的id，报销类型，报销金额，发票信息等等；
    input_remarks: str
    # 报销单由图中的节点来创建，插入到数据库
    approve: ApproveSchema
    # 图执行的结果标识，成功还是失败
    approve_flag: bool
    # 每个节点执行的日志信息可以塞到这个字符串数组中
    log_list: Annotated[List[str], add]
    # 执行图的时候，如果往消息表中插入了消息数据，也把这个插入的消息记录到状态中
    lg_message_list: Annotated[List[dict], add]

  builder = StateGraph(StateSchema)

  # 创建报销单（审批单）
  async def node_create_approve(state: StateSchema):
    insert_approve_dict = {
      "status": "pending_approval",
      "result_content": '待审批......',
      "remarks": state.get('input_remarks'),
    }
    insert_approve_cls = await LgApproveService.item_insert(session=session, row_dict=insert_approve_dict)
    return {
      "approve": insert_approve_cls.model_dump(),
      "log_list": [f"node_create_approve：创建报销单[{insert_approve_cls.id}]"]
    }

  # 创建消息（提示用户审批）
  async def node_create_message(state: StateSchema, config: RunnableConfig):
    thread_id = config.get('configurable').get('thread_id')

    insert_message_dict = {
      "title": "您有一条报销单待审批。",
      "content": f"您的下属员工「XXX」提交了一份报销单，报销内容为：{state.get('approve').get('remarks')}",
      "status": "pending",
      "render_configs": json.dumps([
        {
          "type": "button",
          "data": {
            "label": "审批通过",
            "type": "primary",
            "submit_url": f"/lg_message/feedback/{thread_id}/Y",
          }
        },
        {
          "type": "button",
          "data": {
            "label": "审批拒绝",
            "submit_url": f"/lg_message/feedback/{thread_id}/N",
          }
        },
      ], ensure_ascii=False),
    }

    insert_message_cls = await LgMessageService.item_insert(session=session, row_dict=insert_message_dict)

    return {
      "log_list": [f"node_create_message：创建审批消息，待商机主管「XXX」审批"],
      "lg_message_list": [insert_message_cls.model_dump()],
    }

  # 触发中断（等待审批恢复重新执行这个节点）
  async def node_wait_for_approve(state: StateSchema) -> Command[Literal["node_approve_accept", "node_approve_reject"]]:

    approve_flag = interrupt({})

    # 下面是中断恢复的代码

    state_message_dict = state.get('lg_message_list')[-1]
    update_message_dict = {
      "id": state_message_dict.get('id'),
      "status": "proceeded"
    }
    update_message_cls = await LgMessageService.item_update(session=session, row_dict=update_message_dict)
    update_message_dict = update_message_cls.model_dump()

    if approve_flag == 'Y':
      return Command(
        goto="node_approve_accept",
        update={
          "log_list": [f"node_wait_for_approve：主管审批通过"],
          "lg_message_list": [update_message_dict],
        }
      )
    else:
      return Command(
        goto="node_approve_reject",
        update={
          "log_list": [f"node_wait_for_approve：主管审批拒绝"],
          "lg_message_list": [update_message_dict],
        }
      )

  # 审批通过处理节点
  async def node_approve_accept(state: StateSchema):
    update_approve_dict = {
      "id": state.get('approve').get('id'),
      "status": "accept_approval",
      "result_content": '审批通过......',
    }
    update_approve_cls = await LgApproveService.item_update(session=session, row_dict=update_approve_dict)
    return {
      "approve": update_approve_cls.model_dump(),
      "log_list": [f"node_approve_accept：审批通过，等待财务打款"],
    }

  # 审批拒绝处理节点
  async def node_approve_reject(state: StateSchema):
    update_approve_dict = {
      "id": state.get('approve').get('id'),
      "status": "reject_approval",
      "result_content": '审批拒绝......',
    }
    update_approve_cls = await LgApproveService.item_update(session=session, row_dict=update_approve_dict)
    return {
      "approve": update_approve_cls.model_dump(),
      "log_list": [f"node_approve_accept：审批已经被拒绝"],
    }

  builder.add_node(node_create_approve)
  builder.add_node(node_create_message)
  builder.add_node(node_wait_for_approve)
  builder.add_node(node_approve_accept)
  builder.add_node(node_approve_reject)

  builder.add_edge(START, 'node_create_approve')
  builder.add_edge("node_create_approve", 'node_create_message')
  builder.add_edge("node_create_message", 'node_wait_for_approve')

  builder.add_edge('node_approve_accept', END)
  builder.add_edge('node_approve_reject', END)

  graph = builder.compile(checkpointer=checkpointer)

  return graph
