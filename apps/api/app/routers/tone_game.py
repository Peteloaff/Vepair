from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import ToneGameAttempt, ToneGameSession, User
from app.schemas_tone_game import ToneGameSessionCreate, ToneGameSessionOut

router = APIRouter(prefix="/api/v1", tags=["tone-game"])


@router.post("/tone-game/sessions", response_model=ToneGameSessionOut, status_code=201)
def create_tone_game_session(
    payload: ToneGameSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToneGameSession:
    session = ToneGameSession(
        user_id=current_user.id,
        total_score=sum(a.score for a in payload.attempts),
    )
    db.add(session)
    db.flush()

    for attempt in payload.attempts:
        db.add(
            ToneGameAttempt(
                session_id=session.id,
                order_index=attempt.order_index,
                target_note=attempt.target_note,
                target_hz=attempt.target_hz,
                detected_hz=attempt.detected_hz,
                semitones_off=attempt.semitones_off,
                grade=attempt.grade,
                hold_fraction=attempt.hold_fraction,
                reaction_ms=attempt.reaction_ms,
                score=attempt.score,
            )
        )
    db.commit()
    db.refresh(session)
    return session


@router.get("/tone-game/sessions", response_model=list[ToneGameSessionOut])
def list_tone_game_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ToneGameSession]:
    stmt = (
        select(ToneGameSession)
        .where(ToneGameSession.user_id == current_user.id)
        .options(selectinload(ToneGameSession.attempts))
        .order_by(ToneGameSession.played_at.desc())
    )
    return list(db.scalars(stmt).all())
