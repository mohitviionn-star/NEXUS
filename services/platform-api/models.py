# Defines what one "Service" record looks like in the database -
# basically the columns of a table, described as a Python class.
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)  # unique number per row
    name: Mapped[str] = mapped_column(String(100))  # e.g. "Payment Service"
    slug: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. "payment-service"
    health_check_url: Mapped[str] = mapped_column(String(255))  # where to check its health
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # last known state

class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g. 200, 503, or empty if unreachable
    response_time_ms: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20))  # "healthy" or "unhealthy"
    checked_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))