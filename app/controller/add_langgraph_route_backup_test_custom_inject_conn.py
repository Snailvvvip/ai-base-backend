import random
from contextlib import asynccontextmanager
from operator import add
from typing import TypedDict, Annotated, List

from fastapi import FastAPI, Depends
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.utils.postgres_checkpointer import AsyncPostgresSaverDep


class CustomConnection:
  def __init__(self):
    print("开始自定义连接")

  def close(self):
    print("关闭自定义连接")


@asynccontextmanager
async def open_custom_connection():
  ctx_connection = CustomConnection()
  yield ctx_connection
  ctx_connection.close()


async def get_async_ctx_conn():
  async with open_custom_connection() as conn:
    yield conn


CustomConnDep = Annotated[CustomConnection, Depends(get_async_ctx_conn)]


def add_langgraph_route(app: FastAPI):
  @app.get("/langgraph/invoke")
  async def langgraph_invoke(thread_id: str, checkpointer: AsyncPostgresSaverDep, cst_conn: CustomConnDep):
    print("start", cst_conn)
    print("checkpointer", checkpointer)
    graph = create_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    graph_state = await graph.ainvoke({"name_list": [f"initial:{thread_id}"]}, config=config)
    print("end")
    return graph_state

  @app.get("/langgraph/get_state")
  async def langgraph_get_state(thread_id: str, checkpointer: AsyncPostgresSaverDep):
    graph = create_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    graph_state = await graph.aget_state(config)
    return graph_state.values

  @app.get("/langgraph/get_state_snapshot")
  async def langgraph_get_state_snapshot(thread_id: str, checkpointer: AsyncPostgresSaverDep):
    graph = create_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    graph_state = await graph.aget_state(config)
    return graph_state


def create_graph(checkpointer: AsyncPostgresSaver):
  class StateSchema(TypedDict):
    name_list: Annotated[List[str], add]

  builder = StateGraph(StateSchema)

  def node_1(state):
    random_int = random.randint(0, 100)
    print(["🧠节点执行", "node_1", random_int])
    return {"name_list": [f"node_1:{random_int}"]}

  def node_2(state):
    random_int = random.randint(100, 200)
    print(["🧠节点执行", "node_2", random_int])
    return {"name_list": [f"node_2:{random_int}"]}

  def node_3(state):
    random_int = random.randint(300, 400)
    print(["🧠节点执行", "node_3", random_int])
    return {"name_list": [f"node_3:{random_int}"]}

  builder.add_node(node_1)
  builder.add_node(node_2)
  builder.add_node(node_3)

  builder.add_edge(START, 'node_1')
  builder.add_edge('node_1', 'node_2')
  builder.add_edge('node_2', 'node_3')
  builder.add_edge('node_3', END)

  graph = builder.compile(checkpointer=checkpointer)

  return graph
