"""Organization reporting for admins: per-coach activity and practice, as counts only.

Two kinds of number, with different privacy treatment:

- A coach's own work -- invites sent, notes written, messages sent, assignments sent. These
  describe the coach, not any Vrotégé's voice, so an admin always sees them.
- Vrotégé practice -- completed sessions and how many Vrotégés practiced. These come from a
  Vrotégé's exercise history, so they only count Vrotégés who have shared that category with
  the coach, and a coach's figures stay hidden until at least MIN_GROUP_SIZE of their Vrotégés
  share it (with fewer, a count would effectively describe one identifiable person).

No names, emails or individual results leave this module. It doesn't commit anything."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CoachAccess,
    CoachAccessCategoryGrant,
    CoachAssignment,
    CoachInvite,
    CoachMessage,
    CoachNote,
    CoachProfile,
    ExerciseSession,
    Organization,
    User,
)
from app.schemas_team import CoachReportRow, OrgReportOut, OrgReportTotals

MIN_GROUP_SIZE = 3
PERIODS = (7, 30, 90)


def _counts(db: Session, stmt) -> dict:
    return dict(db.execute(stmt).all())


def build_report(db: Session, organization: Organization, days: int) -> OrgReportOut:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        select(CoachProfile, User)
        .join(User, User.id == CoachProfile.user_id)
        .where(CoachProfile.organization_id == organization.id, CoachProfile.removed_at.is_(None))
        .order_by(CoachProfile.created_at, CoachProfile.id)
    ).all()
    coach_ids = [c.id for c, _ in rows]

    connected = _counts(
        db,
        select(CoachAccess.coach_id, func.count())
        .where(CoachAccess.coach_id.in_(coach_ids), CoachAccess.status == "active")
        .group_by(CoachAccess.coach_id),
    )
    invites = _counts(
        db,
        select(CoachInvite.coach_id, func.count())
        .where(CoachInvite.coach_id.in_(coach_ids), CoachInvite.created_at >= since)
        .group_by(CoachInvite.coach_id),
    )
    notes = _counts(
        db,
        select(CoachNote.coach_id, func.count())
        .where(
            CoachNote.coach_id.in_(coach_ids),
            CoachNote.created_at >= since,
            CoachNote.deleted_at.is_(None),
        )
        .group_by(CoachNote.coach_id),
    )
    messages = _counts(
        db,
        select(CoachAccess.coach_id, func.count())
        .select_from(CoachMessage)
        .join(CoachAccess, CoachAccess.id == CoachMessage.coach_access_id)
        .where(
            CoachAccess.coach_id.in_(coach_ids),
            CoachMessage.sender == "coach",
            CoachMessage.created_at >= since,
        )
        .group_by(CoachAccess.coach_id),
    )
    assignments = _counts(
        db,
        select(CoachAssignment.coach_id, func.count())
        .where(CoachAssignment.coach_id.in_(coach_ids), CoachAssignment.created_at >= since)
        .group_by(CoachAssignment.coach_id),
    )

    # Active connections whose Vrotégé shares exercise history with that coach.
    sharing_pairs = db.execute(
        select(CoachAccess.coach_id, CoachAccess.singer_user_id)
        .join(CoachAccessCategoryGrant, CoachAccessCategoryGrant.coach_access_id == CoachAccess.id)
        .where(
            CoachAccess.coach_id.in_(coach_ids),
            CoachAccess.status == "active",
            CoachAccessCategoryGrant.category == "exercise_history",
            CoachAccessCategoryGrant.granted.is_(True),
        )
    ).all()
    sharing: dict = {}
    for coach_id, singer_id in sharing_pairs:
        sharing.setdefault(coach_id, set()).add(singer_id)

    visible_singers = {s for ids in sharing.values() if len(ids) >= MIN_GROUP_SIZE for s in ids}
    sessions_by_singer = _counts(
        db,
        select(ExerciseSession.user_id, func.count())
        .where(
            ExerciseSession.user_id.in_(visible_singers),
            ExerciseSession.completed_at.isnot(None),
            ExerciseSession.completed_at >= since,
        )
        .group_by(ExerciseSession.user_id),
    )

    out: list[CoachReportRow] = []
    for coach, user in rows:
        singers = sharing.get(coach.id, set())
        shown = len(singers) >= MIN_GROUP_SIZE
        out.append(
            CoachReportRow(
                coach_id=coach.id,
                display_name=coach.display_name,
                org_role=coach.org_role,
                is_active=user.is_active,
                connected_vroteges=connected.get(coach.id, 0),
                invites_sent=invites.get(coach.id, 0),
                notes_written=notes.get(coach.id, 0),
                messages_sent=messages.get(coach.id, 0),
                assignments_sent=assignments.get(coach.id, 0),
                sharing_vroteges=len(singers),
                practice_sessions=(
                    sum(sessions_by_singer.get(s, 0) for s in singers) if shown else None
                ),
                practicing_vroteges=(
                    sum(1 for s in singers if sessions_by_singer.get(s, 0)) if shown else None
                ),
            )
        )

    return OrgReportOut(
        period_days=days,
        since=since,
        min_group_size=MIN_GROUP_SIZE,
        coaches=out,
        totals=OrgReportTotals(
            connected_vroteges=sum(r.connected_vroteges for r in out),
            invites_sent=sum(r.invites_sent for r in out),
            notes_written=sum(r.notes_written for r in out),
            messages_sent=sum(r.messages_sent for r in out),
            assignments_sent=sum(r.assignments_sent for r in out),
            practice_sessions=sum(r.practice_sessions or 0 for r in out),
            practicing_vroteges=sum(r.practicing_vroteges or 0 for r in out),
        ),
    )
