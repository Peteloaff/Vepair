import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ApiToken, User
from app.schemas_api_token import ApiTokenCreate, ApiTokenCreateOut, ApiTokenOut
from app.security import generate_opaque_token

router = APIRouter(prefix="/api/v1/api-tokens", tags=["api-tokens"])


@router.post("", response_model=ApiTokenCreateOut, status_code=201)
def create_api_token(
    payload: ApiTokenCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiTokenCreateOut:
    """The raw token is returned exactly once, here -- it's never stored (only its hash) and
    never retrievable again, same as a GitHub personal access token. See app/api_token_auth.py
    for how it's later verified against `/api/public/v1/*`."""
    raw_token, token_hash = generate_opaque_token()
    token = ApiToken(
        user_id=current_user.id,
        name=payload.name,
        token_hash=token_hash,
        scopes=payload.scopes,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return ApiTokenCreateOut(
        id=token.id,
        name=token.name,
        scopes=token.scopes,
        token=raw_token,
        created_at=token.created_at,
    )


@router.get("", response_model=list[ApiTokenOut])
def list_api_tokens(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ApiToken]:
    return list(
        db.scalars(
            select(ApiToken)
            .where(ApiToken.user_id == current_user.id)
            .order_by(ApiToken.created_at.desc())
        ).all()
    )


@router.delete("/{token_id}", status_code=204)
def revoke_api_token(
    token_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    token = db.scalar(
        select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == current_user.id)
    )
    if token is None:
        raise HTTPException(
            status_code=404, detail={"code": "token_not_found", "message": "Token not found."}
        )
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        db.commit()
