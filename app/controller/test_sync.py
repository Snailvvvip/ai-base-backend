import asyncio
import os
import time

from fastapi import FastAPI


def add_test_sync_route(app: FastAPI):
  @app.get("/test")
  async def test():
    print(f"Process {os.getpid()} handling /test")
    return {"message": "Hello World"}

  @app.get("/sync_delay")
  async def sync_delay(delay: int = 1):
    """同步延迟delay秒"""
    print(f"Process {os.getpid()} handling /sync_delay")
    time.sleep(delay)
    return {"hello": "world"}

  @app.get("/async_delay")
  async def async_delay(delay: int = 1):
    """异步延迟delay秒"""
    print(f"Process {os.getpid()} handling /async_delay")
    await asyncio.sleep(delay)
    return {"hello": "world 456789"}
