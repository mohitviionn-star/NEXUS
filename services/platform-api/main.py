from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Service

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Matches http://localhost:<any port>, so it keeps working no matter which
    # port Vite happens to pick for the dev server.
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "platform-api"}


# "Shapes" describing what a request/response looks like - FastAPI checks
# incoming data against these automatically and rejects anything malformed.
class ServiceIn(BaseModel):
    name: str
    slug: str
    health_check_url: str


class ServiceOut(ServiceIn):
    id: int
    status: str

    class Config:
        from_attributes = True  # allows building this straight from a Service row


# Register a new service in the database.
@app.post("/api/v1/services", response_model=ServiceOut)
async def create_service(payload: ServiceIn, session: AsyncSession = Depends(get_session)):
    service = Service(
        name=payload.name,
        slug=payload.slug,
        health_check_url=payload.health_check_url,
        status="unknown",
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)  # reload it so we get its new id
    return service


# List every service that's been registered.
@app.get("/api/v1/services", response_model=list[ServiceOut])
async def list_services(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Service))
    return result.scalars().all()