from fastapi import Query
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langserve import add_routes

from app.config.env import env
from app.controller.add_api_route import add_api_route
from app.controller.add_approve_route import add_approve_route
from app.controller.add_file_route import add_file_route
from app.controller.add_hotel_route import add_hotel_route
from app.controller.add_image_edit_route import add_image_edit_route
from app.controller.add_knowledge_route import add_knowledge_route
from app.controller.add_langgraph_approve_route import add_langgraph_approve_route
from app.controller.add_langgraph_chat_route import add_langgraph_chat_route
from app.controller.add_langgraph_route import add_langgraph_route
from app.controller.add_lg_approve_route import add_lg_approve_route
from app.controller.add_redis_route import add_redis_route
from app.controller.add_reimburse_route import add_reimburse_route
from app.controller.add_sqlmodel_route import add_sqlmodel_route
from app.controller.add_user_route import add_user_route
from app.controller.add_websocket_route import add_websocket_route
from app.controller.add_websocket_voice_generate_route import add_websocket_voice_generate_route
from app.controller.add_websocket_voice_recognise_route import add_websocket_voice_recognise_route
from app.controller.custom_chat_playground import add_custom_chat_playground_route
from app.controller.custom_stream_api import add_custom_stream_api_route
from app.controller.test_connection import add_test_connection_route
from app.controller.test_sqlmodel import add_test_sqlmodel_route
from app.controller.test_sync import add_test_sync_route
from app.controller.translate_controller import add_translate_route
from app.create_app import create_app
from app.general.add_general_route import add_general_route
from app.general_interceptors.add_general_interceptor_api_secret import add_general_interceptor_api_secret
from app.general_interceptors.add_general_interceptor_knowledge_doc import add_general_interceptor_knowledge_doc
from app.general_interceptors.add_general_interceptor_llm_user import add_general_interceptor_llm_user
from app.general_interceptors.add_general_interceptor_module import add_general_interceptor_module
from app.model.ApiSecretModel import ApiSecretService
from app.model.ApproveModel import ApproveService
from app.model.ConversationModel import ConversationService
from app.model.HotelModel import HotelService
from app.model.InvoiceModel import InvoiceService
from app.model.KnowledgeBase import KnowledgeBaseService
from app.model.KnowledgeDoc import KnowledgeDocService, KnowledgeDocServiceWithCreator
from app.model.LgApprove import LgApproveService
from app.model.LgChat import LgChatService
from app.model.LgMessage import LgMessageService
from app.model.LlmOrder import LlmOrderService
from app.model.LlmProduct import LlmProductService
from app.model.ModuleModel import ModuleService
from app.model.OrderModel import OrderService
from app.model.OrgModel import OrgService
from app.model.PosModel import PosService
from app.model.ProjectModel import ProjectService
from app.model.ReimburseModel import ReimburseService
from app.model.ReimburseOtherModel import ReimburseOtherService
from app.model.ReimburseTravelModel import ReimburseTravelService
from app.model.RelProjUserModel import RelProjUserService
from app.utils.ModelInputSchema import ModelInputSchema
from app.utils.add_async_route import add_async_route
from app.utils.llm_utils import create_llm
from app.utils.next_id import add_next_id_route

app = create_app()

add_translate_route(app)
add_custom_chat_playground_route(app)
add_test_sync_route(app)
add_custom_stream_api_route(app)
add_test_connection_route(app)
add_test_sqlmodel_route(app)
add_next_id_route(app)
add_sqlmodel_route(app)
add_user_route(app)
add_langgraph_route(app)
add_lg_approve_route(app)
add_langgraph_approve_route(app)
add_langgraph_chat_route(app)
add_approve_route(app)
add_reimburse_route(app)
add_hotel_route(app)
add_file_route(app)
add_knowledge_route(app)
add_api_route(app)
add_redis_route(app)
add_general_route(app)
add_websocket_route(app)
add_websocket_voice_recognise_route(app)
add_websocket_voice_generate_route(app)
add_image_edit_route(app)

@app.get("/get_env")
async def test():
  return env.model_dump_json()


@app.get("/test")
async def test():
  return {"msg": "hello"}


@app.get("/test_llm")
async def test_llm(user_content: str = Query(..., description="用户输入的文本内容，将传递给大语言模型处理")):
  return (create_llm() | StrOutputParser()).invoke([HumanMessage(content=user_content)])


add_routes(
  app=app,
  runnable=RunnableLambda(lambda x: x['messages']) | create_llm() | StrOutputParser(),
  input_type=ModelInputSchema,
  path="/doubao"
)

add_routes(
  app=app,
  runnable=RunnableLambda(lambda x: x['messages']) | create_llm("bailian-qwen-plus") | StrOutputParser(),
  input_type=ModelInputSchema,
  path="/bailian-qwen-plus"
)

add_routes(
  app=app,
  runnable=RunnableLambda(lambda x: x['messages']) | create_llm("bailian-qwen-turbo") | StrOutputParser(),
  input_type=ModelInputSchema,
  path="/qwen-turbo"
)

add_async_route(
  app=app,
  runnable=RunnableLambda(lambda x: x['messages']) | create_llm("bailian-qwen-turbo").with_types(input_type=ModelInputSchema),
  path="/qwen"
)

LlmOrderService.add_route(app=app, path="/llm_order")
LlmProductService.add_route(app=app, path="/llm_product")
LgApproveService.add_route(app=app, path="/lg_approve")
LgMessageService.add_route(app=app, path="/lg_message")
LgChatService.add_route(app=app, path="/lg_chat")
OrgService.add_route(app=app, path="/org")
PosService.add_route(app=app, path="/pos")
ProjectService.add_route(app=app, path="/project")
RelProjUserService.add_route(app=app, path="/rel_proj_user")
ReimburseService.add_route(app=app, path="/reimburse")
ReimburseTravelService.add_route(app=app, path="/reimburse_travel")
ReimburseOtherService.add_route(app=app, path="/reimburse_other")
ApproveService.add_route(app=app, path="/approve")
HotelService.add_route(app=app, path="/hotel")
OrderService.add_route(app=app, path="/order")
InvoiceService.add_route(app=app, path="/invoice")
ConversationService.add_route(app=app, path="/conversation")
KnowledgeBaseService.add_route(app=app, path="/knowledge_base")
KnowledgeDocService.add_route(app=app, path="/knowledge_doc")
KnowledgeDocServiceWithCreator.add_route(app=app, path="/knowledge_doc_with_creator")
ApiSecretService.add_route(app=app, path="/api_secret")
ModuleService.add_route(app=app, path="/module")

add_general_interceptor_llm_user()
add_general_interceptor_knowledge_doc()
add_general_interceptor_module()
add_general_interceptor_api_secret()
