from typing import List, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.model.ProjectModel import ProjectService
from app.model.RelProjUserModel import RelProjUserService
from app.utils.PageQueryParams import PageQueryParams
from app.utils.db_utils import async_session


@tool(
  name_or_callable="tool_query_projects",
  description="查询参与的项目信息"
)
async def tool_query_projects(config: RunnableConfig) -> List[Any]:
  user_id = config.get('configurable').get('user_id')

  async with async_session() as session:
    query_cls_list, has_next, total = await RelProjUserService.query_list(session=session, query_param=PageQueryParams(all=True, filters={"user_id": user_id}))
    proj_id_list = [item.proj_id for item in query_cls_list]
    proj_list, has_next, total = await ProjectService.query_list(session=session, query_param=PageQueryParams(all=True, filters={"id": proj_id_list}))

  return [
    "已经查询完毕",
    {
      "component": "ProjectList",
      "props": {"projIdList": [item.id for item in proj_list]},
    }
  ]
