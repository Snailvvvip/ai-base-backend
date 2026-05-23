from app.tools.tool_add import tool_add
from app.tools.tool_book_hotel import tool_book_hotel
from app.tools.tool_get_datetime import tool_get_datetime
from app.tools.tool_multiple import tool_multiply
from app.tools.tool_project_analysis import tool_project_analysis
from app.tools.tool_project_report import tool_project_report
from app.tools.tool_query_direct_subordinates import tool_query_direct_subordinates
from app.tools.tool_query_projects import tool_query_projects
from app.tools.tool_retrieve_documents import tool_retrieve_documents

tool_list = [
  tool_book_hotel,
  tool_get_datetime,
  tool_add,
  tool_multiply,
  tool_query_direct_subordinates,
  tool_query_projects,
  tool_project_analysis,
  tool_project_report,
  tool_retrieve_documents,
]
