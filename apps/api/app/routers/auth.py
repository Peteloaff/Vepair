from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user
from app.config import get_settings
from app.database import get_db
from app.email import send_password_reset_email
from app.models import AuthCredential, PasswordResetToken, RefreshToken, User
from app.schemas_auth import (
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()

INVALID_CREDENTIALS = HTTPException(
    status_code=401,
    detail={"code": "invalid_credentials", "message": "Incorrect email or password."},
)


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    access_token = create_access_token(user.id)

    raw_refresh, refresh_hash = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = User(email=payload.email.lower())
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "email_taken", "message": "An account with this email already exists."},
        ) from None

    db.add(AuthCredential(user_id=user.id, password_hash=hash_password(payload.password)))
    db.commit()
    db.refresh(user)

    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise INVALID_CREDENTIALS

    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id))
    if credential is None or not verify_password(payload.password, credential.password_hash):
        raise INVALID_CREDENTIALS

    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_hash = hash_opaque_token(payload.refresh_token)
    token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    invalid = HTTPException(
        status_code=401,
        detail={"code": "invalid_refresh_token", "message": "Refresh token is invalid or expired."},
    )
    if token_row is None or token_row.revoked_at is not None:
        raise invalid
    if token_row.expires_at < datetime.now(UTC):
        raise invalid

    user = db.get(User, token_row.user_id)
    if user is None:
        raise invalid

    # Rotate: revoke the used refresh token and issue a fresh one.
    token_row.revoked_at = datetime.now(UTC)
    db.commit()

    return _issue_tokens(db, user)


@router.post("/logout", status_code=204)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    token_hash = hash_opaque_token(payload.refresh_token)
    token_row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(UTC)
        db.commit()


@router.post("/password-reset/request", status_code=202)
def request_password_reset(
    payload: PasswordResetRequestSchema, db: Session = Depends(get_db)
) -> None:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is not None:
        raw_token, token_hash = generate_opaque_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.password_reset_token_expire_minutes),
            )
        )
        db.commit()
        send_password_reset_email(user.email, raw_token)
    # Always 202, whether or not the email exists — avoids leaking account existence.


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(
    payload: PasswordResetConfirmSchema, db: Session = Depends(get_db)
) -> None:
    token_hash = hash_opaque_token(payload.token)
    token_row = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )

    invalid = HTTPException(
        status_code=400,
        detail={
            "code": "invalid_reset_token",
            "message": "Reset token is invalid, expired, or already used.",
        },
    )
    if token_row is None or token_row.used_at is not None:
        raise invalid
    if token_row.expires_at < datetime.now(UTC):
        raise invalid

    credential = db.scalar(
        select(AuthCredential).where(AuthCredential.user_id == token_row.user_id)
    )
    if credential is None:
        raise invalid

    credential.password_hash = hash_password(payload.new_password)
    token_row.used_at = datetime.now(UTC)

    # Reset also revokes all existing sessions for this user.
    active_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == token_row.user_id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    for t in active_tokens:
        t.revoked_at = datetime.now(UTC)

    db.commit()


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
