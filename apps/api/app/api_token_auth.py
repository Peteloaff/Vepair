"""Auth for the read-only public API (`/api/public/v1/*`) -- a separate, opt-in credential
system from the JWT-based session auth in app/auth.py. See app/models.py's ApiToken and
PRIVACY.md for the design rationale (personal access token, not OAuth2 -- see ROADMAP.md for
why a fuller delegated-access model was deliberately deferred)."""

import logging
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiToken, User
from app.security import hash_opaque_token
from app.site_settings import get_site_settings

logger = logging.getLogger("vepair.public_api")

RATE_LIMIT_PER_MINUTE = 60

# In-process, best-effort only -- resets on deploy and isn't shared across multiple Cloud Run
# instances. Acceptable at pilot scale (see PRIVACY.md); revisit with a shared store (Redis or
# similar) if usage ever justifies it. Keyed by token id, not user id, so one leaked/misbehaving
# token can't exhaust another token's budget on the same account.
_request_log: dict[uuid.UUID, list[float]] = defaultdict(list)


def _check_rate_limit(token_id: uuid.UUID) -> None:
    now = time.monotonic()
    window_start = now - 60
    recent = [t for t in _request_log[token_id] if t > window_start]
    if len(recent) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": f"Rate limit of {RATE_LIMIT_PER_MINUTE} requests/minute exceeded.",
            },
        )
    recent.append(now)
    _request_log[token_id] = recent


def get_api_token_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> tuple[User, ApiToken]:
    unauthorized = HTTPException(
        status_code=401,
        detail={"code": "invalid_api_token", "message": "Missing or invalid API token."},
    )
    if authorization is None or not authorization.startswith("Bearer "):
        raise unauthorized

    if not get_site_settings(db).public_api_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "public_api_disabled",
                "message": "The public API is not currently enabled.",
            },
        )

    raw_token = authorization.removeprefix("Bearer ")
    token_hash = hash_opaque_token(raw_token)
    token = db.scalar(select(ApiToken).where(ApiToken.token_hash == token_hash))
    if token is None or token.revoked_at is not None:
        raise unauthorized

    _check_rate_limit(token.id)

    user = db.get(User, token.user_id)
    if user is None:
        raise unauthorized

    token.last_used_at = datetime.now(UTC)
    db.commit()

    return user, token


def require_api_scope(scope: str):
    """Dependency factory -- 403s unless the authenticated token was granted this scope. Every
    successful call is logged (token id, user id, scope, not any response content) since this
    is the single largest data-egress surface in the app -- see PRIVACY.md."""

    def _check(
        request: Request,
        user_and_token: tuple[User, ApiToken] = Depends(get_api_token_user),
    ) -> User:
        user, token = user_and_token
        if scope not in token.scopes:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "scope_not_granted",
                    "message": f"This token was not granted the '{scope}' scope.",
                },
            )
        logger.info(
            "public_api_access token_id=%s user_id=%s scope=%s path=%s",
            token.id, user.id, scope, request.url.path,
        )
        return user

    return _check
