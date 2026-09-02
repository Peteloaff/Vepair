import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from vepair_audio_engine.measurements import (
    SUSTAINED_PHONATION_SAMPLE_TYPES,
    InsufficientAudioError,
    InvalidAudioError,
    analyze_wav_bytes,
)

from app.audio_quality import InvalidWavError, analyze_wav, compute_recording_quality_score
from app.auth import get_current_user
from app.baseline import analyze_and_update_baselines, anomaly_message
from app.database import get_db
from app.models import AcousticMeasurement, DeviceMetadata, Recording, User, VoiceSession
from app.schemas_baseline import AnomalyOut
from app.schemas_recording import (
    SAMPLE_TYPES,
    DeviceMetadataIn,
    RecordingOut,
    VoiceSessionOut,
    VoiceSessionWithRecordingsOut,
)
from app.storage import get_storage, recording_key

logger = logging.getLogger("vepair.recordings")

router = APIRouter(prefix="/api/v1", tags=["recordings"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB — generous for a few minutes of 16-bit mono WAV


def _get_owned_session(db: Session, current_user: User, session_id: uuid.UUID) -> VoiceSession:
    session = db.scalar(
        select(VoiceSession).where(
            VoiceSession.id == session_id, VoiceSession.user_id == current_user.id
        )
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "voice_session_not_found", "message": "Voice session not found."},
        )
    return session


def _find_or_create_device(
    db: Session, current_user: User, device: DeviceMetadataIn | None
) -> DeviceMetadata | None:
    if device is None or not any(device.model_dump().values()):
        return None

    existing = db.scalar(
        select(DeviceMetadata).where(
            DeviceMetadata.user_id == current_user.id,
            DeviceMetadata.device_type == device.device_type,
            DeviceMetadata.microphone_name == device.microphone_name,
            DeviceMetadata.os_info == device.os_info,
            DeviceMetadata.app_version == device.app_version,
        )
    )
    if existing is not None:
        return existing

    created = DeviceMetadata(user_id=current_user.id, **device.model_dump())
    db.add(created)
    db.flush()
    return created


@router.post("/voice-sessions", response_model=VoiceSessionOut, status_code=201)
def create_voice_session(
    device: DeviceMetadataIn | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceSession:
    device_row = _find_or_create_device(db, current_user, device)
    session = VoiceSession(
        user_id=current_user.id,
        device_metadata_id=device_row.id if device_row else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/voice-sessions", response_model=list[VoiceSessionWithRecordingsOut])
def list_voice_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[VoiceSessionWithRecordingsOut]:
    """Now includes each session's recordings (previously recording-less VoiceSessionOut) --
    added for the /recordings page (data-minimization round: per-recording deletion needs
    somewhere to list what exists). VoiceSessionOut fields are a strict subset, so this is a
    backward-compatible response-shape change, not a breaking one."""
    stmt = (
        select(VoiceSession)
        .where(VoiceSession.user_id == current_user.id)
        .order_by(VoiceSession.started_at.desc())
    )
    sessions = db.scalars(stmt).all()
    return [
        VoiceSessionWithRecordingsOut(
            id=s.id,
            started_at=s.started_at,
            completed_at=s.completed_at,
            notes=s.notes,
            device_metadata_id=s.device_metadata_id,
            recordings=[RecordingOut.model_validate(r) for r in s.recordings],
        )
        for s in sessions
    ]


@router.get("/voice-sessions/{session_id}", response_model=VoiceSessionWithRecordingsOut)
def get_voice_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceSession:
    return _get_owned_session(db, current_user, session_id)


@router.patch("/voice-sessions/{session_id}/complete", response_model=VoiceSessionOut)
def complete_voice_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceSession:
    session = _get_owned_session(db, current_user, session_id)
    session.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)
    return session


@router.post(
    "/voice-sessions/{session_id}/recordings", response_model=RecordingOut, status_code=201
)
async def upload_recording(
    session_id: uuid.UUID,
    sample_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordingOut:
    if sample_type not in SAMPLE_TYPES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_sample_type",
                "message": f"sample_type must be one of {SAMPLE_TYPES}.",
            },
        )

    voice_session = _get_owned_session(db, current_user, session_id)

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "file_too_large", "message": "Recording exceeds the 50MB limit."},
        )

    try:
        report = analyze_wav(data)
    except InvalidWavError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_audio", "message": str(exc)},
        ) from None

    quality_score = compute_recording_quality_score(report)
    quality_flags = {**report.as_dict(), "quality_score": quality_score.as_dict()}

    recording = Recording(
        voice_session_id=voice_session.id,
        sample_type=sample_type,
        file_path="",  # set below once we know the recording's own id
        duration_seconds=report.duration_seconds,
        sample_rate=report.sample_rate,
        channels=report.channels,
        quality_flags=quality_flags,
    )
    db.add(recording)
    db.flush()  # assigns recording.id without committing yet

    key = recording_key(current_user.id, recording.id)
    get_storage().save(key, data)
    recording.file_path = key

    # Acoustic analysis (Stage 3) runs on a best-effort basis: a recording that's too short
    # or otherwise unanalyzable (per packages/audio-engine, a stricter bar than Stage 2's own
    # too_short flag in some cases) simply gets no AcousticMeasurement row rather than
    # blocking the upload — the recording itself is still saved and visible either way.
    anomalies: list[AnomalyOut] = []
    try:
        measurements = analyze_wav_bytes(data, sample_type)
        db.add(AcousticMeasurement(recording_id=recording.id, **measurements.as_dict()))
        db.flush()

        # Baseline comparison (Stage 4) only makes sense for the same sustained-phonation
        # types the baseline itself is built from — comparing a glide's swept F0 against a
        # sustained-vowel baseline would not be a fair or meaningful comparison.
        if sample_type in SUSTAINED_PHONATION_SAMPLE_TYPES:
            results = analyze_and_update_baselines(
                db, current_user.id, recording.id, measurements.as_dict()
            )
            anomalies = [
                AnomalyOut(
                    metric_name=r.metric_name,
                    current_value=r.current_value,
                    baseline_median=r.baseline_median,
                    modified_z_score=r.modified_z_score,
                    message=anomaly_message(r),
                )
                for r in results
            ]
    except (InvalidAudioError, InsufficientAudioError) as exc:
        logger.info("Skipping acoustic analysis for recording %s: %s", recording.id, exc)

    db.commit()
    db.refresh(recording)
    result = RecordingOut.model_validate(recording)
    result.anomalies = anomalies
    return result


@router.get("/recordings/{recording_id}/audio")
def get_recording_audio(
    recording_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    recording = db.scalar(
        select(Recording)
        .join(VoiceSession)
        .where(Recording.id == recording_id, VoiceSession.user_id == current_user.id)
    )
    if recording is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "recording_not_found", "message": "Recording not found."},
        )
    if recording.file_path is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "audio_purged",
                "message": (
                    "This recording's audio was automatically removed under VepAIr's data "
                    "retention policy. Its measurements are still available."
                ),
            },
        )

    audio_bytes = get_storage().read(recording.file_path)
    return Response(content=audio_bytes, media_type="audio/wav")


@router.delete("/recordings/{recording_id}", status_code=204)
def delete_recording(
    recording_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """User-initiated, full removal -- deliberately not the retention job's "keep the
    measurement" posture (see app/data_retention.py's module docstring): this is the user
    explicitly saying "get rid of this," not a passive policy default, so the whole row goes,
    AcousticMeasurement included (cascades via its ondelete="CASCADE"). Removing this recording
    doesn't retroactively recompute an already-stored Baseline/RecoveryScore row -- it only
    affects computations going forward."""
    recording = db.scalar(
        select(Recording)
        .join(VoiceSession)
        .where(Recording.id == recording_id, VoiceSession.user_id == current_user.id)
    )
    if recording is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "recording_not_found", "message": "Recording not found."},
        )
    if recording.file_path is not None:
        try:
            get_storage().delete(recording.file_path)
        except Exception:
            logger.error(
                "Failed to delete recording file on user-initiated delete: recording_id=%s "
                "file_path=%s",
                recording.id,
                recording.file_path,
                exc_info=True,
            )
    db.delete(recording)
    db.commit()
