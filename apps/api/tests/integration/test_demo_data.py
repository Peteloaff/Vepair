"""Admin "demo data": fake organizations/coaches/singers for exploring the admin and coach
views. Driven through the real endpoints."""

from app.demo_data import DEMO_EMAIL_DOMAIN
from app.models import User


def _make_admin(db_session, email: str, *, admin_role: str | None = None) -> None:
    user = db_session.query(User).filter_by(email=email).one()
    user.is_admin = True
    user.admin_role = admin_role
    db_session.commit()


def _demo_orgs(client, headers) -> dict:
    orgs = client.get("/api/v1/admin/organizations", headers=headers).json()
    return {o["name"]: o for o in orgs if o["coach_email"].endswith(DEMO_EMAIL_DOMAIN)}


def test_demo_data_creates_four_organizations_with_realistic_usage(
    client, signed_up_user, db_session
) -> None:
    admin_user, headers = signed_up_user
    _make_admin(db_session, admin_user["email"])

    created = client.post("/api/v1/admin/demo-data", headers=headers)
    assert created.status_code == 200, created.text
    assert created.json()["created"] is True
    assert created.json()["organizations"] == 4

    orgs = _demo_orgs(client, headers)
    assert set(orgs) == {
        "Harbor Voice Studio",
        "Sunrise Singers Collective",
        "Blue Note Academy",
        "Riverside Choir Co.",
    }
    # Sunrise is over its 50-invite quota, Blue Note's Coach Pro has been revoked.
    assert orgs["Sunrise Singers Collective"]["invites_used_this_period"] > 50
    assert orgs["Blue Note Academy"]["is_coach_pro_active"] is False
    assert orgs["Harbor Voice Studio"]["is_coach_pro_active"] is True


def test_demo_data_is_idempotent_and_removable_without_touching_other_accounts(
    client, signed_up_user, signed_up_coach, db_session
) -> None:
    admin_user, headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    real_coach, _coach_headers = signed_up_coach

    client.post("/api/v1/admin/demo-data", headers=headers)
    again = client.post("/api/v1/admin/demo-data", headers=headers)
    assert again.json()["created"] is False

    status = client.get("/api/v1/admin/demo-data", headers=headers).json()
    assert status["exists"] is True

    removed = client.post("/api/v1/admin/demo-data/remove", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["removed_organizations"] == 4
    assert client.get("/api/v1/admin/demo-data", headers=headers).json()["exists"] is False
    assert _demo_orgs(client, headers) == {}

    # Everything that wasn't demo data is still there.
    assert db_session.query(User).filter_by(email=real_coach["email"]).one_or_none() is not None
    assert db_session.query(User).filter_by(email=admin_user["email"]).one_or_none() is not None


def test_demo_accounts_cannot_log_in(client, signed_up_user, db_session) -> None:
    admin_user, headers = signed_up_user
    _make_admin(db_session, admin_user["email"])
    client.post("/api/v1/admin/demo-data", headers=headers)
    demo_email = (
        db_session.query(User).filter(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}")).first().email
    )
    resp = client.post("/api/v1/auth/login", json={"email": demo_email, "password": "anything123"})
    # Rejected outright (the reserved .invalid domain isn't a valid login email), and there is no
    # password on these accounts in any case.
    assert resp.status_code in (401, 422)

    # They do show up in the admin user list, where they can be recognized by their email.
    listed = client.get("/api/v1/admin/users", headers=headers, params={"query": DEMO_EMAIL_DOMAIN})
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) >= 19


def test_support_admin_cannot_create_or_remove_demo_data(
    client, signed_up_user, db_session
) -> None:
    admin_user, headers = signed_up_user
    _make_admin(db_session, admin_user["email"], admin_role="support")
    assert client.post("/api/v1/admin/demo-data", headers=headers).status_code == 403
    assert client.post("/api/v1/admin/demo-data/remove", headers=headers).status_code == 403
    # Checking whether demo data exists is read-only.
    assert client.get("/api/v1/admin/demo-data", headers=headers).status_code == 200
