"""Data minimization: app/data_retention.py's two purge policies (tested directly against
db_session) and POST /api/v1/system/purge-stale-data (tested through the real API).

Assertions are scoped to each test's own rows -- see test_reminders.py's module docstring for
why: the shared local dev database this suite runs against can carry real leftover data from
manual/browser verification earlier in development, and a batch job that scans "every stale
row" will see those too.
"""

from datetime import UTC, date, datetime, timedelta

from app.data_retention import purge_stale_checkin_notes, purge_stale_recordings
from app.models import DailyCheckIn, Recording, User, UserProfile, VoiceSession

OLD = datetime.now(UTC) - timedelta(days=200)
OLD_DATE = date.today() - timedelta(days=200)


def _make_recording(
    db_session, email: str, *, created_at, file_path: str | None = "some/key"
) -> Recording:
    user = User(email=email)
    db_session.add(user)
    db_session.flush()
    db_session.add(UserProfile(user_id=user.id))
    session = VoiceSession(user_id=user.id)
    db_session.add(session)
    db_session.flush()
    recording = Recording(
        voice_session_id=session.id,
        sample_type="sustained_ah",
        file_path=file_path,
    )
    db_session.add(recording)
    db_session.commit()
    # created_at has a server_default -- overwrite it directly after the insert to simulate age.
    db_session.execute(
        Recording.__table__.update()
        .where(Recording.id == recording.id)
        .values(created_at=created_at)
    )
    db_session.commit()
    db_session.refresh(recording)
    return recording


def test_purge_stale_recordings_removes_old_audio_but_keeps_the_row(db_session) -> None:
    stale = _make_recording(db_session, "retention-stale@example.com", created_at=OLD)

    purged = purge_stale_recordings(db_session, older_than_days=90)

    assert purged >= 1
    db_session.refresh(stale)
    assert stale.file_path is None
    assert stale.audio_purged_at is not None


def test_purge_stale_recordings_leaves_recent_audio_alone(db_session) -> None:
    recent = _make_recording(
        db_session, "retention-recent@example.com", created_at=datetime.now(UTC)
    )

    purge_stale_recordings(db_session, older_than_days=90)

    db_session.refresh(recent)
    assert recent.file_path == "some/key"
    assert recent.audio_purged_at is None


def test_purge_stale_recordings_skips_already_purged_rows(db_session) -> None:
    already_purged = _make_recording(
        db_session, "retention-already-purged@example.com", created_at=OLD, file_path=None
    )

    # Should not error, and should not count a row that had nothing left to purge.
    purge_stale_recordings(db_session, older_than_days=90)

    db_session.refresh(already_purged)
    assert already_purged.file_path is None


def test_purge_stale_checkin_notes_clears_sensitive_fields_but_keeps_quantitative_ones(
    db_session,
) -> None:
    user = User(email="retention-checkin@example.com")
    db_session.add(user)
    db_session.flush()
    checkin = DailyCheckIn(
        user_id=user.id,
        checkin_date=OLD_DATE,
        voice_quality=7,
        fatigue=3,
        illness_symptoms="a cold",
        reflux_symptoms="some heartburn",
        notes="felt off today",
    )
    db_session.add(checkin)
    db_session.commit()

    purged = purge_stale_checkin_notes(db_session, older_than_days=30)

    assert purged >= 1
    db_session.refresh(checkin)
    assert checkin.illness_symptoms is None
    assert checkin.reflux_symptoms is None
    assert checkin.notes is None
    # Quantitative fields are untouched -- trend history stays whole.
    assert checkin.voice_quality == 7
    assert checkin.fatigue == 3


def test_purge_stale_checkin_notes_leaves_recent_checkins_alone(db_session) -> None:
    user = User(email="retention-recent-checkin@example.com")
    db_session.add(user)
    db_session.flush()
    checkin = DailyCheckIn(
        user_id=user.id,
        checkin_date=date.today(),
        illness_symptoms="today's cold",
    )
    db_session.add(checkin)
    db_session.commit()

    purge_stale_checkin_notes(db_session, older_than_days=30)

    db_session.refresh(checkin)
    assert checkin.illness_symptoms == "today's cold"


def test_purge_stale_data_endpoint_requires_correct_secret(client) -> None:
    resp = client.post("/api/v1/system/purge-stale-data")
    assert resp.status_code == 403


def test_purge_stale_data_endpoint_succeeds_with_correct_secret(
    client, db_session, monkeypatch
) -> None:
    from app.routers import system as system_router

    monkeypatch.setattr(system_router.settings, "internal_job_secret", "test-secret")

    resp = client.post(
        "/api/v1/system/purge-stale-data", headers={"X-Internal-Job-Secret": "test-secret"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "recordings_purged" in body
    assert "checkin_notes_purged" in body
