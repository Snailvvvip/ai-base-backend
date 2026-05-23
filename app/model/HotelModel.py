from decimal import Decimal
from typing import Optional

from pydantic import computed_field, PrivateAttr
from sqlmodel import Field, Relationship

from app.model.BasicModel import BasicModel
from app.model.UserModel import UserServiceModel
from app.utils.create_module_service import create_model_service


class HotelModel(BasicModel, table=True):
  __tablename__ = "pl_hotel"

  title: str = Field(default=None, description="酒店房间名称")
  description: str = Field(default=None, description="酒店房间描述")
  origin_price: Decimal = Field(default=None, description="原价")
  discount_price: Decimal = Field(default=None, description="目标价")
  picture: str = Field(default=None, description="房间预览照片")
  sales: int = Field(default=None, description="销量")


HotelService = create_model_service(HotelModel)
