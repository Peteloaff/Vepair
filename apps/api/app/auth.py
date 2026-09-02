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


def create_access_token(user_id: uuid.UUID, *, impersonated_by: uuid.UUID | None = None) -> str:
    """`impersonated_by` (app/routers/admin.py's impersonate endpoint) mints a token that
    authenticates as `user_id` but is tagged as an impersonation token -- see
    verify_access_token and get_current_user below for what that changes: read-only
    enforcement, and every request in the window is attributable to the admin who started it
    even though it authenticates as the target user. Same expiry as a normal access token
    (settings.access_token_expire_minutes, already 15 minutes) -- no separate, longer-lived
    impersonation token type."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "impersonation" if impersonated_by is not None else "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if impersonated_by is not None:
        payload["impersonated_by"] = str(impersonated_by)
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_access_token(token: str) -> tuple[uuid.UUID, uuid.UUID | None]:
    """Returns (user id, impersonated_by) encoded in a valid access or impersonation token, or
    raises HTTPException(401). impersonated_by is None for a normal access token."""
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

    token_type = payload.get("type")
    if token_type not in ("access", "impersonation"):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Not an access token."},
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_token", "message": "Access token missing subject."},
        ) from None

    impersonated_by = None
    if token_type == "impersonation":
        try:
            impersonated_by = uuid.UUID(payload["impersonated_by"])
        except (KeyError, ValueError):
            raise HTTPException(
                status_code=401,
                detail={"code": "invalid_token", "message": "Impersonation token malformed."},
            ) from None

    return user_id, impersonated_by


IMPERSONATION_READ_ONLY = HTTPException(
    status_code=403,
    detail={
        "code": "impersonation_read_only",
        "message": "Impersonated sessions can only view data, never change it.",
    },
)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "missing_token", "message": "Missing bearer token."},
        )
    token = auth_header.removeprefix("Bearer ").strip()
    user_id, impersonated_by = verify_access_token(token)

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

    if impersonated_by is not None:
        # The single enforcement point for "impersonation is read-only" -- every authenticated
        # endpoint in this app resolves the caller through get_current_user (directly, or
        # transitively via get_current_admin/get_current_coach/require_coach_access), so gating
        # here covers the whole app's write surface at once rather than requiring each router
        # to check for an impersonation token itself. A blunt instrument, not a perfect one: a
        # GET that has a side effect (e.g. coach.py's list_messages_with_singer marking
        # messages read) still fires -- HTTP-method-based enforcement approximates "read-only,"
        # it doesn't formally prove it.
        request.state.impersonated_by = impersonated_by
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            raise IMPERSONATION_READ_ONLY

    return user
