import asyncio
import os.path
from typing import List

from fastapi import FastAPI, UploadFile, Form

from app.config.env import env
from app.model.FileModel import FileSaveService
from app.utils.db_utils import AsyncSessionDep
from app.utils.path_join import path_join


def add_file_route(app: FastAPI):
  async def _save_file(
    session: AsyncSessionDep,
    file: UploadFile,
    body: dict,
  ):
    filename = file.filename
    return await FileSaveService.saveFile(
      session=session,
      file=file,
      filename=filename,
      id=body.get('id', None),
      file_record=body,
    )

  async def _save_file_list(
    session: AsyncSessionDep,
    file_list: List[UploadFile],
    body: dict,
  ):
    async_task_list = [asyncio.create_task(
      FileSaveService.saveFile(
        session=session,
        file=item,
        filename=item.filename,
        file_record=body,
      )
    ) for item in file_list]
    result_list = await asyncio.gather(*async_task_list)
    return {"result": result_list}

  async def _delete_file(row_dict: dict):
    file_public_path = row_dict.get('path')
    path_list: List[str] = file_public_path.split('/')
    original_name = path_list.pop()
    file_id = path_list.pop()
    save_file_path = path_join(env.file_save_path, file_id, original_name)

    # 删除文件
    try:
      os.remove(save_file_path)
    except FileNotFoundError:
      print("文件不存在:" + save_file_path)

    # 删除文件夹
    save_dir_path = path_join(env.file_save_path, file_id)
    try:
      os.rmdir(save_dir_path)
    except FileNotFoundError:
      print("文件夹不存在:" + save_dir_path)

    return {"result": True}

  @app.post('/save_file')
  async def save_file(
    file: UploadFile,
    session: AsyncSessionDep,
    head_id: str = Form(default=None, description="父对象id"),
    attr1: str = Form(default=None, description="扩展属性1"),
    attr2: str = Form(default=None, description="扩展属性2"),
    attr3: str = Form(default=None, description="扩展属性3")
  ):
    return await _save_file(session, file, {
      "head_id": head_id,
      "attr1": attr1,
      "attr2": attr2,
      "attr3": attr3
    })

  @app.post('/upload_file')
  async def save_file(
    file: UploadFile,
    session: AsyncSessionDep,
    head_id: str = Form(default=None, description="父对象id"),
    attr1: str = Form(default=None, description="扩展属性1"),
    attr2: str = Form(default=None, description="扩展属性2"),
    attr3: str = Form(default=None, description="扩展属性3")
  ):
    result = await _save_file(session, file, {
      "head_id": head_id,
      "attr1": attr1,
      "attr2": attr2,
      "attr3": attr3
    })
    if 'result' in result:
      print(f"upload_file:自动删除文件「{result['result']['path']}」")
      await _delete_file(result['result'])
    return result
