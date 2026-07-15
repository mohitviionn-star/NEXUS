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
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0)

class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g. 200, 503, or empty if unreachable
    response_time_ms: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20))  # "healthy" or "unhealthy"
    checked_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    severity: Mapped[str] = mapped_column(String(20), default="high")
    status: Mapped[str] = mapped_column(String(20), default="open")  # "open" or "resolved"
    opened_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    event_type: Mapped[str] = mapped_column(String(30))  # "opened" or "resolved"
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
