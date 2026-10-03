import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(16), index=True)
    resource_type: Mapped[str] = mapped_column(String(120), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)

    price: Mapped[float] = mapped_column(Numeric(18, 6))
    unit: Mapped[str] = mapped_column(String(32), default="")
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)