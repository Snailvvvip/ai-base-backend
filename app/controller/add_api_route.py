import json

from app.tools.tool_project_analysis import tool_project_analysis
from fastapi import FastAPI
from fastapi import Query
from starlette.requests import Request

from app.tools.tool_project_report import tool_project_report
from app.tools.tool_retrieve_documents import tool_retrieve_documents


def add_api_route(app: FastAPI):
  # 用于dify自定义插件授权认证接口
  @app.post('/api/me')
  @app.post('/api/account')
  async def api_account(
    request: Request
  ):
    print("request.state", request.state)
    return request.state.user

  # 项目成本分析报告
  @app.get('/api/project/analysis')
  async def project_analysis(project_name=Query(..., description="项目名称")):
    tool_result_string = await tool_project_analysis.ainvoke({"project_name": project_name})
    try:
      tool_result_data = json.loads(tool_result_string)
      result = tool_result_data[0]
    except:
      result = tool_result_string
    return {
      "result": result
    }

  # 项目日报总结
  @app.get('/api/project/report')
  async def project_analysis(
    project_name=Query(..., description="项目名称"),
    start_time=Query(default=None, description="开始时间(可选参数)格式为YYYY-MM-DD"),
    end_time=Query(default=None, description="结束时间(可选参数)格式为YYYY-MM-DD"),
  ):
    tool_result_string = await tool_project_report.ainvoke({
      "project_name": project_name,
      "start_time": start_time,
      "end_time": end_time,
    })
    try:
      tool_result_data = json.loads(tool_result_string)
      result = tool_result_data[0]
    except:
      result = tool_result_string
    return {
      "result": result
    }

  # 检索企业内部文档工具
  @app.get('/api/document/retrieve')
  async def document_retrieve(question=Query(..., description="用户的问题")):
    return {
      "result": await tool_retrieve_documents.ainvoke({"question": question})
    }
