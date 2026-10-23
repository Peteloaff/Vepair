"""Fake organizations, coaches and singers for exploring the admin and coach views.

Everything created here uses an email at DEMO_EMAIL_DOMAIN (a reserved ".invalid" domain, so it
can never receive mail or collide with a real account), has no password (nobody can log in as a
demo account), and sends no email. remove_demo_data() deletes it all again by that domain.
"""

import random
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.account_deletion import delete_user_and_storage
from app.models import (
    CoachAccess,
    CoachAccessCategoryGrant,
    CoachInvite,
    CoachMessage,
    CoachNote,
    CoachProfile,
    DailyCheckIn,
    ExerciseSession,
    Organization,
    User,
    UserProfile,
)
from app.recovery_score import compute_and_store_recovery_score

DEMO_EMAIL_DOMAIN = "demo.vepair.invalid"
CHECKIN_DAYS = 10

ALL_CATEGORIES = ["recovery_trends", "vocal_range", "exercise_history", "recordings"]

# (org name, coach name, Coach Pro state, period started N days ago, extra pending invites,
#  singers as (name, shared categories, mood))
DEMO_ORGS = [
    (
        "Harbor Voice Studio",
        "Alex Morgan",
        "active",
        40,
        2,
        [
            ("Maya Okafor", ALL_CATEGORIES, "moderate"),
            ("Daniel Reyes", ["recovery_trends", "exercise_history"], "good"),
            ("Priya Nair", ALL_CATEGORIES[:3], "rough"),
            ("Tom Ellery", ["vocal_range", "exercise_history"], "good"),
            ("Chloe Barnes", ALL_CATEGORIES, "good"),
            ("Jonas Weber", ["recovery_trends"], "moderate"),
        ],
    ),
    (
        "Sunrise Singers Collective",
        "Priya Raman",
        "active",
        200,
        47,
        [
            ("Ava Lindgren", ALL_CATEGORIES, "good"),
            ("Marcus Bell", ["recovery_trends", "exercise_history"], "moderate"),
            ("Sofia Alvarez", ALL_CATEGORIES[:3], "good"),
            ("Ethan Cho", ["exercise_history"], "rough"),
            ("Nina Petrova", ALL_CATEGORIES, "good"),
        ],
    ),
    (
        "Blue Note Academy",
        "Jordan Ellis",
        "revoked",
        400,
        1,
        [
            ("Leo Fontaine", ALL_CATEGORIES, "moderate"),
            ("Hannah Kim", ["recovery_trends", "vocal_range"], "good"),
            ("Omar Haddad", ["exercise_history"], "moderate"),
        ],
    ),
    (
        "Riverside Choir Co.",
        "Sam Okoye",
        "active",
        2,
        0,
        [("Grace Turner", ALL_CATEGORIES, "good")],
    ),
]

# Extra coaches on a demo organization's team, as (name, org_role). They have no Vrotégés of
# their own -- each coach's Vrotégés are private to that coach -- so the roster stays the
# organization's lead coach's.
DEMO_TEAMMATES = {
    "Harbor Voice Studio": [("Jamie Cole", "member"), ("Rowan Pike", "admin")],
    "Sunrise Singers Collective": [("Dana Whitfield", "member")],
}

MOODS = {
    "good": dict(voice_quality=(7, 9), fatigue=(2, 4), throat_discomfort=(0, 1), sleep=(7, 8.5)),
    "moderate": dict(
        voice_quality=(5, 7), fatigue=(4, 6), throat_discomfort=(1, 3), sleep=(6, 7.5)
    ),
    "rough": dict(voice_quality=(3, 5), fatigue=(6, 8), throat_discomfort=(3, 6), sleep=(5, 6.5)),
}

NOTES = [
    "Steady tone this week. Keep the straw shallow and stop if anything feels pressed.",
    "Nice progress on breath support. Let's revisit range next session.",
    "Lighter load this week while the voice recovers.",
]
MESSAGES = [
    "Straw work felt easier today, but my range felt smaller.",
    "Should I still do the warm up before rehearsal tonight?",
]


def _email(local: str) -> str:
    return f"{local}@{DEMO_EMAIL_DOMAIN}"


def demo_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))).all())


def demo_status(db: Session) -> dict:
    users = demo_users(db)
    coaches = db.execute(
        select(CoachProfile.user_id, CoachProfile.organization_id).where(
            CoachProfile.user_id.in_([u.id for u in users])
        )
    ).all()
    return {
        "exists": bool(users),
        # Distinct organizations: several demo coaches can share one.
        "organizations": len({organization_id for _, organization_id in coaches}),
        "singers": len(users) - len(coaches),
    }


def _add_activity(db: Session, user: User, mood: str, rng: random.Random, today: date) -> None:
    profile = MOODS[mood]
    for days_ago in range(CHECKIN_DAYS, -1, -1):
        day = today - timedelta(days=days_ago)
        # A couple of skipped days so the charts show real-looking gaps.
        if rng.random() < 0.15 and days_ago not in (0, 1):
            continue
        db.add(
            DailyCheckIn(
                user_id=user.id,
                checkin_date=day,
                voice_quality=rng.randint(*profile["voice_quality"]),
                fatigue=rng.randint(*profile["fatigue"]),
                throat_discomfort=rng.randint(*profile["throat_discomfort"]),
                sleep_hours=round(rng.uniform(*profile["sleep"]), 1),
            )
        )
    db.flush()
    for days_ago in range(CHECKIN_DAYS, -1, -1):
        try:
            compute_and_store_recovery_score(db, user.id, today - timedelta(days=days_ago))
        except Exception:  # a day with no check-in just has no score
            db.rollback()
            return
    now = datetime.now(UTC)
    session_days = {"good": 8, "moderate": 5, "rough": 2}[mood]
    for i in range(session_days):
        done = now - timedelta(days=i, hours=rng.randint(0, 5))
        db.add(
            ExerciseSession(
                user_id=user.id,
                routine_length_minutes=10 if i % 3 else None,
                session_type="adaptive" if i % 3 else "warm_up",
                started_at=done - timedelta(minutes=10),
                completed_at=done,
            )
        )


def create_demo_data(db: Session) -> dict:
    if demo_users(db):
        return {**demo_status(db), "created": False}

    rng = random.Random(7)
    now = datetime.now(UTC)
    today = date.today()
    singer_count = 0
    invite_count = 0

    for org_index, (
        org_name,
        coach_name,
        state,
        started_days_ago,
        extra_pending,
        singers,
    ) in enumerate(DEMO_ORGS, start=1):
        organization = Organization(name=org_name)
        organization.coach_pro_period_start = now - timedelta(days=started_days_ago)
        if state == "active":
            organization.is_coach_pro_active = True
            organization.coach_pro_period_end = organization.coach_pro_period_start + timedelta(
                days=365
            )
        else:
            organization.is_coach_pro_active = False
            organization.coach_pro_period_end = now - timedelta(days=35)
        db.add(organization)
        db.flush()

        coach_user = User(email=_email(f"coach{org_index}-{coach_name.lower().replace(' ', '-')}"))
        db.add(coach_user)
        db.flush()
        coach = CoachProfile(
            user_id=coach_user.id, display_name=coach_name, organization_id=organization.id
        )
        db.add(coach)
        db.flush()

        for mate_name, mate_role in DEMO_TEAMMATES.get(org_name, []):
            mate = User(email=_email(f"team{org_index}-{mate_name.lower().replace(' ', '-')}"))
            db.add(mate)
            db.flush()
            db.add(
                CoachProfile(
                    user_id=mate.id,
                    display_name=mate_name,
                    organization_id=organization.id,
                    org_role=mate_role,
                )
            )

        for name, categories, mood in singers:
            user = User(email=_email(name.lower().replace(" ", ".")))
            db.add(user)
            db.flush()
            db.add(UserProfile(user_id=user.id))
            _add_activity(db, user, mood, rng, today)

            invite = CoachInvite(
                coach_id=coach.id,
                singer_user_id=user.id,
                singer_email=user.email,
                status="accepted",
                message=f"Welcome to {org_name}!",
                responded_at=now - timedelta(days=rng.randint(3, 30)),
            )
            db.add(invite)
            db.flush()
            access = CoachAccess(
                coach_id=coach.id,
                singer_user_id=user.id,
                invite_id=invite.id,
                status="active",
                granted_at=invite.responded_at,
            )
            db.add(access)
            db.flush()
            for category in ALL_CATEGORIES:
                db.add(
                    CoachAccessCategoryGrant(
                        coach_access_id=access.id,
                        category=category,
                        granted=category in categories,
                    )
                )
            if rng.random() < 0.7:
                db.add(
                    CoachNote(
                        coach_id=coach.id,
                        singer_user_id=user.id,
                        coach_access_id=access.id,
                        body=rng.choice(NOTES),
                    )
                )
            if rng.random() < 0.5:
                db.add(
                    CoachMessage(
                        coach_access_id=access.id, sender="singer", body=rng.choice(MESSAGES)
                    )
                )
            singer_count += 1
            invite_count += 1

        # Invites that haven't been accepted: they count toward the org's invite quota but never
        # become accounts. A declined one is added too, to show it does not count.
        for n in range(extra_pending):
            db.add(
                CoachInvite(
                    coach_id=coach.id,
                    singer_user_id=None,
                    singer_email=_email(f"pending-{org_index}-{n + 1}"),
                    status="pending",
                    created_at=now - timedelta(days=rng.randint(0, max(started_days_ago - 1, 1))),
                )
            )
            invite_count += 1
        db.add(
            CoachInvite(
                coach_id=coach.id,
                singer_user_id=None,
                singer_email=_email(f"declined-{org_index}"),
                status="declined",
                responded_at=now - timedelta(days=2),
            )
        )
        db.commit()

    return {**demo_status(db), "created": True, "invites": invite_count}


def remove_demo_data(db: Session) -> dict:
    users = demo_users(db)
    if not users:
        return {"removed_accounts": 0, "removed_organizations": 0}

    coach_by_user = {
        c.user_id: c
        for c in db.scalars(
            select(CoachProfile).where(CoachProfile.user_id.in_([u.id for u in users]))
        ).all()
    }
    # A set: several coaches can share one organization.
    organization_ids = {c.organization_id for c in coach_by_user.values()}
    singers = [u for u in users if u.id not in coach_by_user]
    coaches = [u for u in users if u.id in coach_by_user]

    for user in singers + coaches:
        delete_user_and_storage(db, user)
    removed_orgs = 0
    for organization_id in organization_ids:
        organization = db.get(Organization, organization_id)
        if organization is not None:
            db.delete(organization)
            removed_orgs += 1
    db.commit()
    return {"removed_accounts": len(users), "removed_organizations": removed_orgs}
