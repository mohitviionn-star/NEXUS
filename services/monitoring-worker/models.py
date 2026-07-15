# Same table shapes as platform-api's models.py - the worker reads/writes
# the same database tables, just from a separate program.
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    health_check_url: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="unknown")


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20))
    checked_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
