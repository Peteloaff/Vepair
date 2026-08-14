"""JWT access-token issuance/verification and the `get_current_user` dependency.

This module is the intended swap point for a future move to Supabase Auth: replace
`create_access_token` / `verify_access_token` with Supabase JWT issuance/verification
(Supabase also issues JWTs with a `sub` claim = user id), and `get_current_user` keeps
working unchanged since it only depends on `verify_access_token` returning a user id.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

settings = get_settings()

ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_access_token(token: str) -> uuid.UUID:
    """Returns the user id encoded in a valid access token, or raises HTTPException(401)."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"code": "token_expired", "message": "Access token has expired."},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Access token is invalid."},
        ) from None

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Not an access token."},
        )

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Access token missing subject."},
        ) from None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "missing_token", "message": "Missing bearer token."},
        )
    token = auth_header.removeprefix("Bearer ").strip()
    user_id = verify_access_token(token)

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "user_not_found", "message": "User for this token no longer exists."},
        )
    if user.is_active is False:
        raise HTTPException(
            status_code=401,
            detail={"code": "account_deactivated", "message": "This account has been deactivated."},
        )
    return user
