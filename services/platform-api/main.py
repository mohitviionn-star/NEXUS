from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Incident, Service, User
from datetime import datetime
from auth import hash_password, verify_password, create_access_token, get_current_user




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


# Register a new service in the database. Requires being logged in.
@app.post("/api/v1/services", response_model=ServiceOut)
async def create_service(
    payload: ServiceIn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
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


# List every service that's been registered. Requires being logged in.
@app.get("/api/v1/services", response_model=list[ServiceOut])
async def list_services(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Service))
    return result.scalars().all()
    

# Shape for showing an incident back to whoever asks.
class IncidentOut(BaseModel):
    id: int
    service_id: int
    severity: str
    status: str
    opened_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


# List every incident, newest first. Requires being logged in.
@app.get("/api/v1/incidents", response_model=list[IncidentOut])
async def list_incidents(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Incident).order_by(Incident.opened_at.desc()))
    return result.scalars().all()



class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/api/v1/auth/register", status_code=201)
async def register(payload: RegisterIn, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(user)
    await session.commit()
    return {"message": "Registered successfully"}


@app.post("/api/v1/auth/login", response_model=TokenOut)
async def login(payload: LoginIn, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Same error either way - don't reveal whether the email exists.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token)
