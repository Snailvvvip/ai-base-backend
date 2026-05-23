import json
from typing import Annotated, List, Optional

from langchain_core.tools import tool
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.model.KnowledgeDoc import KnowledgeDocModel
from app.model.ProjectModel import ProjectModel, ProjectService
from app.model.RelProjUserModel import RelProjUserService, RelProjUserModel
from app.utils.PageQueryParams import PageQueryParams
from app.utils.db_utils import async_session, AsyncSessionDep


@tool(
  name_or_callable="tool_project_report",
  description="查询项目日报周报的工具，在调用这个工具之前要先调用获取时间工具"
)
async def tool_project_report(
  project_name: Annotated[str, "项目名称"],
  start_time: Annotated[Optional[str], "开始时间(可选参数)格式为YYYY-MM-DD"] = None,
  end_time: Annotated[Optional[str], "结束时间(可选参数)格式为YYYY-MM-DD"] = None
) -> str:
  async with async_session() as session:
    project_cls: ProjectModel = await ProjectService.query_item(
      session=session,
      row_dict={"name": project_name}
    )
    if not project_cls:
      return f"找不到名为「{project_name}」的项目"

    # 查询所有所属的项目成员
    query_result = await RelProjUserService.query_list(session=session, query_param=PageQueryParams(all=True, filters={"proj_id": project_cls.id}))
    rel_list: List[RelProjUserModel] = query_result[0]
    member_id_list: List[str] = [item.user_id for item in rel_list]

    # member_list = await UserService.query_list(session=session, query_param=PageQueryParams(all=True, filters={"id": member_id_list}))

    doc_list = await query_users_reports(session=session, user_id_list=member_id_list, start_time=start_time, end_time=end_time)

    user_reports = {}

    for doc in doc_list:
      user_full_name = doc.creator.full_name
      if user_full_name not in user_reports:
        user_reports[user_full_name] = []
      user_reports[user_full_name].append({
        "datetime": doc.created_at.strftime("%Y-%m-%d") if doc.created_at else None,
        "content": doc.content,
      })

  return json.dumps(user_reports, ensure_ascii=False)


async def query_users_reports(session: AsyncSessionDep, user_id_list: List[str], start_time: Optional[str], end_time: Optional[str]):
  filter_parent_codes = [f"report_{user_id}" for user_id in user_id_list]

  query = select(KnowledgeDocModel).options(selectinload(KnowledgeDocModel.creator_relationship))

  query = query.where(KnowledgeDocModel.parent_code.in_(filter_parent_codes))
  if start_time:
    query = query.where(KnowledgeDocModel.created_at >= (start_time + " 00:00:00"))
  if end_time:
    query = query.where(KnowledgeDocModel.created_at <= (end_time + " 23:59:59"))

  query = query.order_by(KnowledgeDocModel.created_at.desc())

  result = await session.execute(query)
  query_cls_list: List[KnowledgeDocModel] = result.scalars().all()

  return query_cls_list
