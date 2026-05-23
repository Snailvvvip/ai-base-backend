import json
from decimal import Decimal
from typing import Annotated, List

from langchain_core.tools import tool

from app.model.ProjectModel import ProjectService, ProjectModel
from app.model.ReimburseModel import ReimburseService, ReimburseModel
from app.model.ReimburseOtherModel import ReimburseOtherModel
from app.model.ReimburseTravelModel import ReimburseTravelModel
from app.utils.PageQueryParams import PageQueryParams
from app.utils.db_utils import async_session


@tool(
  name_or_callable="tool_project_analysis",
  description="做项目成本分析报告"
)
async def tool_project_analysis(project_name: Annotated[str, "项目名称"]) -> str:
  async with async_session() as session:
    project_cls: ProjectModel = await ProjectService.query_item(
      session=session,
      row_dict={"name": project_name}
    )
    if not project_cls:
      return f"找不到名为「{project_name}」的项目"

    query_cls_list, has_next, total = await ReimburseService.query_list(session=session, query_param=PageQueryParams(all=True, filters={"proj_id": project_cls.id}))

  reimburse_list: List[ReimburseModel] = [item for item in query_cls_list if item.approve is not None and item.approve.status == 'approved']

  member_amount = {}  # 人员成本分析
  member_cost_description_list = {}  # 人员费用描述

  reimburse_travel_list: List[ReimburseTravelModel] = []
  reimburse_other_list: List[ReimburseOtherModel] = []

  for reimburse_cls in reimburse_list:
    reimburse_travel_list.extend(reimburse_cls.travel_list)
    reimburse_other_list.extend(reimburse_cls.other_list)

    if not member_amount.get(reimburse_cls.user.full_name, None):
      member_amount[reimburse_cls.user.full_name] = Decimal(0)
    if not member_cost_description_list.get(reimburse_cls.user.full_name, None):
      member_cost_description_list[reimburse_cls.user.full_name] = []

    member_amount[reimburse_cls.user.full_name] += reimburse_cls.amount
    for item in reimburse_cls.travel_list:
      member_cost_description_list[reimburse_cls.user.full_name].append(f"""
  费用描述：{item.title}，差旅费用——{item.type}，{item.amount}元，{item.depart_time}——{item.arrive_time}，{item.depart_city}——{item.arrive_city}
  """)
    for item in reimburse_cls.other_list:
      member_cost_description_list[reimburse_cls.user.full_name].append(f"""
  费用描述：{item.title}，其他费用——{item.type}，{item.amount}元
  """)

  cost_amount = {}  # 费用类型成本分析

  for item in reimburse_travel_list:
    if not cost_amount.get(item.type, None):
      cost_amount[item.type] = Decimal(0)
    cost_amount[item.type] += item.amount

  for item in reimburse_other_list:
    if not cost_amount.get(item.type, None):
      cost_amount[item.type] = Decimal(0)
    cost_amount[item.type] += item.amount

  member_description = '\n'.join([f"{user_full_name}:{user_spent}" for user_full_name, user_spent in member_amount.items()])
  cost_description = '\n'.join([f"{cost_type}:{cost_amount}" for cost_type, cost_amount in cost_amount.items()])
  member_cost_description = '\n'.join([f"{user_full_name}产生的费用：{''.join(user_cost_description)}" for user_full_name, user_cost_description in member_cost_description_list.items()])

  description = f"""
  项目预算：{project_cls.budget}
  项目花费金额：{project_cls.spent}
  项目预算余额：{project_cls.balance}

  项目成员成本分析：
  {member_description}

  费用类型成本分析：
  {cost_description}

  人员费用清单：

  {member_cost_description}
      """

  member_amount = {k: str(v) for k, v in member_amount.items()}
  cost_amount = {k: str(v) for k, v in cost_amount.items()}

  return json.dumps([
    description,
    {
      "component": "ProjectCostAnalysis",
      "props": {
        "member_amount": member_amount,
        "cost_amount": cost_amount,
        "spent": str(project_cls.spent),
        "balance": str(project_cls.balance),
      }
    }
  ], ensure_ascii=False)
