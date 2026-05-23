import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile
from sqlmodel import Field

from app.config.env import env
from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service
from app.utils.db_utils import AsyncSessionDep
from app.utils.next_id import next_id
from app.utils.path_join import path_join


class FileModel(BasicModel, table=True):
  __tablename__ = "pl_upload"

  name: Optional[str] = Field(default=None, description='文件名称')
  path: Optional[str] = Field(default=None, description='文件路径')
  head_id: Optional[str] = Field(default=None, description='父对象id')
  attr1: Optional[str] = Field(default=None, description='扩展属性1')
  attr2: Optional[str] = Field(default=None, description='扩展属性2')
  attr3: Optional[str] = Field(default=None, description='扩展属性3')
  content: Optional[str] = Field(default=None, description='扩展属性内容文本')


FileService = create_model_service(Cls=FileModel)


# 文件保存服务
class FileSaveService:
  # 将文件保存到服务本地目录
  # 并且往附件表中插入对应的文件记录
  @staticmethod
  async def saveFile(
    session: AsyncSessionDep,
    file: UploadFile,
    filename: str,
    id: str = None,
    file_record: dict = None,
  ):
    if not id:
      id = await next_id()

    datetime_string = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_id = f"{datetime_string}_{id}"

    # 文件的保存路径，用来将文件写入到磁盘
    # save_path=/www/wwwroot/web/web/upload_file/时间+随机ID
    save_path = path_join(env.file_save_path, file_id).replace('\\', '/')
    print("save_path", save_path)

    # 文件的访问路径，用来生成文件的访问路径，然后存到附件表中的path字段中
    # public_path=/web/upload_file/时间+随机ID
    public_path = path_join(env.file_public_path, file_id).replace('\\', '/')
    print("public_path", public_path)

    # parents=True 表示创建所有不存在的父目录
    # exist_ok=True 表示如果目录已存在不抛出异常
    Path(save_path).mkdir(parents=True, exist_ok=True)

    file_save_path = path_join(save_path, filename)  # 文件的保存路径
    file_public_path = path_join(public_path, filename)  # 文件的访问路径

    # with open(file_save_path, 'wb') as f:
    #   f.write(await file.read())

    async with aiofiles.open(file_save_path, 'wb') as f:
      await f.write(await file.read())
      await f.flush()  # 确保数据写入磁盘

    file_dict = {
      "id": id,
      "name": filename,
      "path": file_public_path,
      **file_record,
    }
    file_cls = await FileService.item_insert(session=session, row_dict=file_dict)
    return {"result": file_cls.model_dump()}
