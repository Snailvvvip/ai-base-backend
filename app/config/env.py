from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv


class Settings(BaseSettings):
  db_host: str = Field(..., env="DB_HOST")
  db_port: str = Field(..., env="DB_PORT")
  db_username: str = Field(..., env="DB_USERNAME")
  db_password: str = Field(..., env="DB_PASSWORD")
  db_database: str = Field(..., env="DB_DATABASE")

  pg_db_host: str = Field(..., env="PG_DB_HOST")
  pg_db_port: str = Field(..., env="PG_DB_PORT")
  pg_db_username: str = Field(..., env="PG_DB_USERNAME")
  pg_db_password: str = Field(..., env="PG_DB_PASSWORD")
  pg_db_database: str = Field(..., env="PG_DB_DATABASE")

  milvus_uri: str = Field(..., env="MILVUS_URI")
  milvus_username: str = Field(..., env="MILVUS_USERNAME")
  milvus_password: str = Field(..., env="MILVUS_PASSWORD")
  llama_index_database: str = Field(..., env="LLAMA_INDEX_DATABASE")
  llama_index_collection: str = Field(..., env="LLAMA_INDEX_COLLECTION")
  llama_index_dimension: str = Field(..., env="LLAMA_INDEX_DIMENSION")

  redis_host: str = Field(..., env="REDIS_HOST")
  redis_port: str = Field(..., env="REDIS_PORT")
  redis_password: str = Field(..., env="REDIS_PASSWORD")
  redis_db: str = Field(..., env="REDIS_DB")

  llm_key_local: str = Field(..., env="LLM_KEY_LOCAL")
  llm_key_huoshan: str = Field(..., env="LLM_KEY_HUOSHAN")
  llm_key_bailian: str = Field(..., env="LLM_KEY_BAILIAN")
  llm_key_deepseek: str = Field(..., env="LLM_KEY_DEEPSEEK")

  server_port: str = Field(..., env="SERVER_PORT")
  server_domain: str = Field(..., env="SERVER_DOMAIN")

  jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
  jwt_algorithm: str = Field(..., env="JWT_ALGORITHM")
  jwt_access_token_expire_seconds: int = Field(..., env="JWT_ACCESS_TOKEN_EXPIRE_SECONDS")
  jwt_refresh_token_expire_seconds: int = Field(..., env="JWT_REFRESH_TOKEN_EXPIRE_SECONDS")
  jwt_global_enable: bool = Field(..., env="JWT_GLOBAL_ENABLE")
  jwt_white_list: List[str] = Field(..., env="JWT_WHITE_LIST")

  file_save_path: str = Field(..., env='FILE_SAVE_PATH')
  file_public_path: str = Field(..., env='FILE_PUBLIC_PATH')
  default_update_by_fields: bool = Field(..., env='DEFAULT_UPDATE_BY_FIELDS')

  dify_approve_workflow_url: str = Field(..., env='DIFY_APPROVE_WORKFLOW_URL')
  dify_approve_workflow_key: str = Field(..., env='DIFY_APPROVE_WORKFLOW_KEY')

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"


load_dotenv(".env")  # 先加载 .env 文件
env = Settings()
