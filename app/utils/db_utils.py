from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config.env import env

DATABASE_URL = f"mysql+asyncmy://{env.db_username}:{env.db_password}@{env.db_host}:{env.db_port}/{env.db_database}?charset=utf8mb4"

# 建议直接使用这个函数，不要嵌套 create_engine(AsyncAdaptedQueuePool)
async_engine = create_async_engine(
  DATABASE_URL,
  # 连接池保持的连接数
  pool_size=5,
  # 允许超过pool_size的最大连接数
  max_overflow=10,
  # 获取连接的超时时间(秒)
  pool_timeout=30,
  # 连接回收时间(秒)
  pool_recycle=60,  # 针对 Docker NAT 环境优化
  # 启用连接有效性检测
  pool_pre_ping=True,  # 解决 Lost connection 的核心
  # 启用SQL语句日志输出，便于开发调试
  echo=True,
  # 启用SQLAlchemy 2.0风格的未来模式API
  future=True,
)

# 使用这个 Session 工厂
async_session = sessionmaker(
  async_engine,
  class_=AsyncSession,
  expire_on_commit=False
)


# 作用：用于在接口中注入得到会话实例对象session，在接口执行完毕之后，自动执行close动作关闭会话
async def get_async_session() -> AsyncSession:
  async with async_session() as session:
    yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


# 用于启动服务的时候检查数据库连接是否正常
async def check_database_connection():
  """检查数据库连接是否正常"""
  try:
    async with async_engine.begin() as conn:
      print("Connecting Mysql...")
      await conn.execute(text("select 1"))
      # 打印连接成功信息及连接URL
      print("✅ MySql connection successful：", DATABASE_URL)
  except Exception as e:
    # 打印连接失败信息及错误详情
    print(f"❌ Database connection failed: {e}")
    # 重新抛出异常，让上层处理
    raise e

  return async_engine
