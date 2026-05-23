from datetime import datetime, date
from decimal import Decimal

from sqlmodel import Field

from app.model.BasicModel import BasicModel
from app.utils.create_module_service import create_model_service


class InvoiceModel(BasicModel, table=True):
  __tablename__ = "pl_invoice"

  fpdm: str = Field(..., title="发票代码")
  fphm: str | None = Field(default=None, title="发票号码（全电发票可不填）")
  kprq: date = Field(..., title="开票日期(yyyyMMdd,如20181128)")
  jym: str | None = Field(default=None, title="校验码后六位(专用发票可空,其他发票必须)")
  je: Decimal | None = Field(default=None, title="金额(专用发票必须,其他发票可空)")
  path: str = Field(..., title="发票文件路径")
  remarks: str | None = Field(default=None, title="备注信息")
  status: str | None = Field(default=None, title="发票状态：未验证(unverified)，已通过(success),未通过(failed)")


InvoiceService = create_model_service(InvoiceModel)
