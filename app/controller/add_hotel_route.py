import uuid

from fastapi import FastAPI
from langchain_core.runnables import RunnableConfig
from langgraph.constants import START
from langgraph.graph import StateGraph
from pydantic import BaseModel

from app.model.ApproveModel import ApproveModel, ApproveService
from app.model.HotelModel import HotelService, HotelModel
from app.model.OrderModel import OrderService
from app.model.ProjectModel import ProjectModel, ProjectService
from app.model.ReimburseModel import ReimburseService, ReimburseModel
from app.model.ReimburseOtherModel import ReimburseOtherService
from app.model.UserModel import UserServiceModel, UserService
from app.utils.db_utils import AsyncSessionDep, async_session
from app.utils.llm_approve_utils import get_llm_approve_result
from app.utils.postgres_checkpointer import AsyncPostgresSaverDep
from app.workflow.approve import create_approve_graph, ApproveGraphSchema


def add_hotel_route(app: FastAPI):
  @app.post('/book_hotel')
  async def book_hotel(
    body: BookHotelSchema,
    session: AsyncSessionDep,
    checkpointer: AsyncPostgresSaverDep,
  ):
    async with async_session() as session2:
      user_cls: UserServiceModel = await UserService.query_item(session2, row_dict={"id": body.user_id})
      hotel_cls: HotelModel = await HotelService.query_item(session2, row_dict={"id": body.hotel_id})
      project_cls: ProjectModel = await ProjectService.query_item(session2, row_dict={"id": body.proj_id})

    new_approve_id = str(uuid.uuid4())
    reimburse_id = str(uuid.uuid4())

    # 审批通过之后，要创建的报销单信息
    input_reimburse_dict = {
      "id": reimburse_id,
      "title": f"{user_cls.full_name} - 酒店预定",
      "remarks": f"酒店预定信息：{hotel_cls.title}, {hotel_cls.description}, {hotel_cls.discount_price}",
      "proj_id": body.proj_id,
      "amount": str(hotel_cls.discount_price),
      "project": project_cls.model_dump(),
      "approve_id": new_approve_id,
      "user_id": body.user_id,
    }
    input_reimburse_other_dict = {
      "title": f"{user_cls.full_name} - 酒店预定",
      "type": "酒店宾馆",
      "amount": str(hotel_cls.discount_price),
      "recipe_type": "电子普通发票",
      "reimburse_id": reimburse_id,
    }

    llm_response_dict = await get_llm_approve_result(session, {
      **input_reimburse_dict,
      "user": user_cls.model_dump(),
      "travel_list": [],
      "other_list": [input_reimburse_other_dict]
    })

    # 新建审批单信息
    new_approve_dict = {
      "id": new_approve_id,
      "title": f"{user_cls.full_name} - 酒店预定审批",
      "description": f"酒店预定信息：{hotel_cls.title}, {hotel_cls.description}, {hotel_cls.discount_price}",
      "status": "approving",
      "amount": hotel_cls.discount_price,
      "logs": "[]",
      "user_id": body.user_id,  # 先把审批人的id设置为申请人
      "apply_user_id": body.user_id,
      "proj_id": body.proj_id,
      "approve_from": "book_hotel",
      **llm_response_dict,
    }
    # 马上插入审批单信息
    insert_approve_cls: ApproveModel = await ApproveService.item_insert(session=session, row_dict=new_approve_dict)

    book_hotel_graph = create_book_hotel_graph(session=session, checkpointer=checkpointer)

    graph_state = await book_hotel_graph.ainvoke(
      {
        "input_user_id": body.user_id,
        "input_approve_id": insert_approve_cls.id,
        "input_amount": str(insert_approve_cls.amount),
        "input_reimburse_dict": input_reimburse_dict,
        "input_hotel_dict": hotel_cls.model_dump(),
        "input_reimburse_other_dict": input_reimburse_other_dict,
      },
      config={"configurable": {"thread_id": insert_approve_cls.id}}
    )

    return {"message": "已经提交审批单，审批通过之后将自动创建订单！请在“审批管理 / 我的申请”中查看审批单", "graph_state": graph_state}


class BookHotelSchema(BaseModel):
  hotel_id: str
  user_id: str
  proj_id: str


def create_book_hotel_graph(
  checkpointer: AsyncPostgresSaverDep,
  session: AsyncSessionDep,
):
  approve_graph = create_approve_graph(checkpointer, session)

  builder = StateGraph(BookHotelGraphSchema)

  async def node(state: BookHotelGraphSchema, config: RunnableConfig):
    print('\n\n', ":::::::::::node start::::::::::::", '\n\n')
    print(state)
    print('\n\n', ":::::::::::node end::::::::::::", '\n\n')

    graph_state = await approve_graph.ainvoke(state, config=config)
    approve_flag = graph_state.get('approve_flag')

    if approve_flag:
      # 酒店预定，先走审批流程，审批通过之后：
      # 1. 创建报销单
      # 2. 将审批单与报销单关联
      # 3. 创建订单

      # 新建报销单信息
      input_reimburse_dict = state.get('input_reimburse_dict')
      insert_reimburse_cls = await ReimburseService.item_insert(session=session, row_dict=input_reimburse_dict)

      # 新建报销单其他费用信息
      input_reimburse_other_dict = state.get('input_reimburse_other_dict')
      input_reimburse_other_dict['reimburse_id'] = insert_reimburse_cls.id
      await ReimburseOtherService.item_insert(session=session, row_dict=input_reimburse_other_dict)

      # 新建订单信息
      insert_order_dict = {
        "name": state.get('input_hotel_dict').get('title'),
        "price": state.get('input_hotel_dict').get('discount_price'),
        "user_id": insert_reimburse_cls.user_id,
        "reimburse_id": insert_reimburse_cls.id
      }
      await OrderService.item_insert(session=session, row_dict=insert_order_dict)

    return {}

  builder.add_node("node", node)
  builder.add_edge(START, "node")

  return builder.compile(checkpointer=checkpointer)


class BookHotelGraphSchema(ApproveGraphSchema):
  input_hotel_dict: dict
  input_reimburse_dict: dict
  input_reimburse_other_dict: dict
