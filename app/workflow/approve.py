import datetime
import json
from typing import List
from typing import TypedDict, Union

import httpx
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

from app.config.env import env
from app.model.ApproveModel import ApproveService
from app.model.UserModel import UserService, UserServiceModel
from app.utils.db_utils import AsyncSessionDep
from app.utils.postgres_checkpointer import AsyncPostgresSaverDep


# 创建审批工作流
def create_approve_graph(
  checkpointer: AsyncPostgresSaverDep,
  session: AsyncSessionDep,
):
  builder = StateGraph(ApproveGraphSchema)

  async def node_first(state: ApproveGraphSchema):
    supervisor_user = await aget_supervisor_user(user_id=state.get('input_user_id'), session=session)

    print('\n\n', ":::::::::::node_first start::::::::::::", '\n\n')
    print(supervisor_user)
    print('\n\n', ":::::::::::node_first end::::::::::::", '\n\n')

    if not supervisor_user:
      # 审批通过
      return Command(goto="node_accept", update={})
    else:
      # 更新update_approve，指派申请人的上级主管审批
      return Command(
        goto="node_update_approve",
        update={
          "update_approve": {
            "log_content": f"「{supervisor_user.full_name}」处理审批",
            "approve_dict": {
              "user_id": supervisor_user.id,  # 审批人为上级主管
              "status": "approving",  # 审批状态为处理中
            },
          }
        }
      )

  # 节点用来更新审批单信息，实际上就是指派给哪个用户审批
  async def node_update_approve(state: ApproveGraphSchema):

    update_approve = state.get('update_approve')

    print('\n\n', ":::::::::::node_update_approve start::::::::::::", '\n\n')
    print(update_approve)
    print('\n\n', ":::::::::::node_update_approve end::::::::::::", '\n\n')

    await update_approve_cls(
      approve_id=state.get('input_approve_id'),
      session=session,
      log_content=update_approve.get('log_content'),
      approve_dict=update_approve.get('approve_dict'),
    )
    return Command(goto="node_supervisor_approve", update={})

  async def node_supervisor_approve(state: ApproveGraphSchema):

    # 上一个节点已经指派给用户审批了，这里直接触发中断，等待审批回执
    approve_result = interrupt({})

    if approve_result.get('flag'):
      # 审批回执标识为通过

      # 当前审批人的id
      user_id = approve_result.get('user_id')
      # 审批单id
      approve_id = state.get('input_approve_id')

      # 下一个准备要审批的上级主管用户
      supervisor_user = await aget_supervisor_user(user_id=user_id, session=session)

      user_cls: UserServiceModel = await UserService.query_item(session=session, row_dict={"id": user_id})

      print('\n\n', ":::::::::::node_supervisor_approve start::::::::::::", '\n\n')
      print(supervisor_user.full_name if supervisor_user else '无上级主管', user_id, approve_id)
      print('\n\n', ":::::::::::node_supervisor_approve end::::::::::::", '\n\n')

      # 已经没有上级主管了，结束审批流程
      if not supervisor_user:
        # 审批通过
        return Command(goto="node_accept", update={})
      else:
        async with httpx.AsyncClient() as client:
          response = await client.post(
            url=env.dify_approve_workflow_url,
            headers={
              "Authorization": f"Bearer {env.dify_approve_workflow_key}"
            },
            json={
              "inputs": {
                "approve_pos_level": user_cls.pos.pos_level,
                "amount": str(state.get('input_amount'))
              },
              "user": f"{user_cls.username} - {user_cls.full_name}"
            },

          )
          result = response.json()
          is_need_supervisor_approve = result.get('data').get('outputs').get('flag')

          print('\n\n', ":::::::::::httpx.AsyncClient start::::::::::::", '\n\n')
          print(result, is_need_supervisor_approve == "Y", is_need_supervisor_approve)
          print('\n\n', ":::::::::::httpx.AsyncClient end::::::::::::", '\n\n')

          if is_need_supervisor_approve == "Y":
            # 审批通过
            return Command(goto="node_accept", update={})

        # 还有上级主管，继续触发下一个上级主管审批
        return Command(
          update={"update_approve": {
            "log_content": f"「{supervisor_user.full_name}」处理审批",
            "approve_dict": {
              "user_id": supervisor_user.id,  # 审批人为上级主管
              "status": "approving",  # 审批状态为处理中
            },
          }},
          goto="node_update_approve",
        )
    else:
      return Command(goto="node_reject", update={"reject_reason": approve_result.get("reason")})

  async def node_accept(state: ApproveGraphSchema):
    await update_approve_cls(
      approve_id=state.get('input_approve_id'),
      session=session,
      log_content="审批已经通过",
      # 不再需要审批人
      # 审批状态为通过
      approve_dict={"user_id": "", "status": "approved"},
    )
    return {"approve_flag": True}

  async def node_reject(state: ApproveGraphSchema):
    # 审批驳回
    await update_approve_cls(
      approve_id=state.get('input_approve_id'),
      session=session,
      log_content=state.get('reject_reason'),
      # 不再需要审批人
      # 审批状态为驳回
      approve_dict={"user_id": "", "status": "rejected"},
    )
    return {"approve_flag": False}

  builder.add_node(node_first)
  builder.add_node(node_update_approve)
  builder.add_node(node_supervisor_approve)
  builder.add_node(node_accept)
  builder.add_node(node_reject)

  builder.add_edge(START, 'node_first')

  graph = builder.compile(checkpointer=checkpointer)

  return graph


async def update_approve_cls(
  approve_id: str,
  session: AsyncSessionDep,
  log_content: str,
  approve_dict: dict,
):
  # 查询审批单信息，准备更新审批单中的日志信息
  approve_cls = await ApproveService.query_item(session=session, row_dict={"id": approve_id})

  # 更新审批日志
  approve_logs: List[ApproveLog] = json.loads(approve_cls.logs or '[]')
  approve_logs.append({"content": log_content, "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

  # 更新审批单信息，包括审批人以及审批日志，此时审批状态为驳回
  approve_cls = await ApproveService.item_update(session=session, row_dict={
    "id": approve_id,
    "logs": json.dumps(approve_logs, ensure_ascii=False),
    **approve_dict,
  })
  return approve_cls


# 找到上级主管用户信息
async def aget_supervisor_user(user_id: str, session: AsyncSessionDep) -> Union[UserServiceModel, None]:
  # 目标用户信息
  user_cls: UserServiceModel = await UserService.query_item(session=session, row_dict={"id": user_id})
  # 目标用户的上级职位编码
  parent_code = user_cls.pos.parent_code
  # 根据上级职位编码查询上级用户信息
  return await UserService.query_item(session=session, row_dict={"pos_code": parent_code})


# 审批回执数据类型
class ApproveResult(TypedDict):
  # 审批标识，是审批通过还是审批驳回
  flag: bool
  # 审批驳回原因
  reason: str
  # 审批人id
  user_id: str


# 审批日志数据类型
class ApproveLog(TypedDict):
  content: str
  datetime: str


class NodeUpdateApproveSchema(TypedDict):
  log_content: str
  approve_dict: dict


# 审批流程的输入参数类型
class ApproveGraphSchema(TypedDict):
  input_user_id: str
  input_approve_id: str
  input_amount: str

  # 更新审批信息数据，用来执行节点：node_update_approve（入参），实际就是指派哪个用户来审批
  update_approve: NodeUpdateApproveSchema
  # 最后的审批结果标识，审批通过还是驳回
  approve_flag: bool
  # 驳回原因
  reject_reason: str
