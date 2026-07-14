# Defines what one "Service" record looks like in the database -
# basically the columns of a table, described as a Python class.
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)  # unique number per row
    name: Mapped[str] = mapped_column(String(100))  # e.g. "Payment Service"
    slug: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. "payment-service"
    health_check_url: Mapped[str] = mapped_column(String(255))  # where to check its health
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # last known state
