import asyncio
import socket
import sys

import psutil

from app.config.env import env

# 在Windows平台上设置事件循环策略为WindowsSelectorEventLoopPolicy
if sys.platform == "win32":
  from asyncio import WindowsSelectorEventLoopPolicy

  asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


def run_uvicorn():
  import uvicorn

  # 获取环境变量中的端口号
  port = int(env.server_port)

  # 打印所有可用的访问地址
  print("\n服务已启动，以下是可用的访问地址：")
  print(f" - 本地访问: http://127.0.0.1:{port}")

  for ip in get_local_ips():
    print(f" - 网络访问: http://{ip}:{port}")

  print("\n")  # 空行美化输出

  """
uvicorn.run() 启动了一个异步事件循环来处理 HTTP 请求，
这个循环会一直运行直到服务器被手动停止（比如按下 Ctrl+C）。
因此，uvicorn.run() 之后的代码不会被执行，直到服务器关闭。
  """
  # 启动Uvicorn服务器
  uvicorn.run("app.main_app:app", host="0.0.0.0", port=port)

  # uvicorn.run之后的代码永远都不会执行
  # 使用FastAPI的 @app.on_event("startup")装饰器可以在服务器成功启动后执行代码
  print('App is running...(Never Callable)')


def get_local_ips():
  ips = []
  try:
    for interface, addrs in psutil.net_if_addrs().items():
      for addr in addrs:
        if addr.family == socket.AF_INET and addr.address != '127.0.0.1':
          ips.append(addr.address)
  except Exception as e:
    print(f"获取 IP 地址时出错: {e}")
  return ips
