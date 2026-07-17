# Helpers for password hashing and JWT tokens - the actual "how do we prove
# who you are" logic, kept separate from the request-handling code.
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv

load_dotenv()  # reads the .env file and makes its values available below

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 30

password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_hasher.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def create_access_token(user_id: int, organization_id: int, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "sub": str(user_id),
        "org_id": organization_id,
        "role": role,
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import RefreshToken, User

# Tells FastAPI's /docs page to show a simple "paste your token" box for the
# Authorize button - we're just checking a bearer token, not implementing
# the full OAuth2 password-grant handshake.
bearer_scheme = HTTPBearer()


class CurrentUser:
    """Everything an endpoint needs to know about who's making the request -
    the user themselves, plus which organization and role apply right now."""

    def __init__(self, user: User, organization_id: int, role: str):
        self.user = user
        self.organization_id = organization_id
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload["sub"])
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return CurrentUser(user=user, organization_id=payload["org_id"], role=payload["role"])


async def issue_refresh_token(session: AsyncSession, user_id: int) -> str:
    raw_token = secrets.token_urlsafe(48)  # long, unguessable random "receipt"
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    session.add(RefreshToken(user_id=user_id, token=raw_token, expires_at=expires_at))
    return raw_token


async def use_refresh_token(session: AsyncSession, raw_token: str) -> RefreshToken:
    """Looks up a refresh token and makes sure it's still valid (not revoked, not expired)."""
    result = await session.execute(select(RefreshToken).where(RefreshToken.token == raw_token))
    refresh_token = result.scalar_one_or_none()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if refresh_token is None or refresh_token.revoked or refresh_token.expires_at < now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return refresh_token
