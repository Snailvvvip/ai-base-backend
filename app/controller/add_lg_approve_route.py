import random
from operator import add
from typing import Annotated, List, TypedDict

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

from app.utils.postgres_checkpointer import AsyncPostgresSaverDep


def add_lg_approve_route(app: FastAPI):
  @app.get("/lg/approve/submit")
  async def lg_approve_submit(thread_id: str, checkpointer: AsyncPostgresSaverDep):
    graph = create_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke({"name_list": [f"initial:{thread_id}"]}, config=config)

  @app.get("/lg/approve/state")
  async def lg_approve_get_state(thread_id: str, checkpointer: AsyncPostgresSaverDep):
    graph = create_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = await graph.aget_state(config)
    graph_state = state_snapshot.values
    return {
      **graph_state,
      "__interrupt__": state_snapshot.interrupts,
    }

  @app.get("/lg/approve/resume")
  async def lg_approve_resume(
    thread_id: str,
    is_approve: str,
    checkpointer: AsyncPostgresSaverDep
  ):
    graph = create_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke(Command(resume=is_approve), config=config)


def create_graph(checkpointer: AsyncPostgresSaver):
  class StateSchema(TypedDict):
    name_list: Annotated[List[str], add]

  builder = StateGraph(StateSchema)

  def node_1(state: StateSchema):
    random_int = random.randint(0, 100)
    print(["🧠节点执行", "node_1", random_int])
    return {"name_list": [f"node_1:{random_int}"]}

  def node_2(state: StateSchema):
    random_int = random.randint(100, 200)
    print(["🧠节点执行", "node_2", random_int])
    is_approved = interrupt({
      "message": "需要主管审批"
    })
    result = "✅通过" if is_approved == 'Y' else "❌拒绝"
    return {"name_list": [f"node_2:{random_int}，" + result]}

  def node_3(state: StateSchema):
    random_int = random.randint(200, 300)
    print(["🧠节点执行", "node_3", random_int])
    return {"name_list": [f"node_3:{random_int}"]}

  builder.add_node(node_1)
  builder.add_node(node_2)
  builder.add_node(node_3)

  builder.add_edge(START, 'node_1')
  builder.add_edge("node_1", 'node_2')
  builder.add_edge("node_2", 'node_3')
  builder.add_edge("node_3", END)

  return builder.compile(checkpointer=checkpointer)
