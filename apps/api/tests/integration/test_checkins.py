import uuid


def _second_user_headers(client) -> dict:
    email = f"test_{uuid.uuid4().hex[:12]}@example.com"
    signup = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": "correcthorse123"}
    )
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


def test_create_checkin(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"checkin_date": "2026-01-01", "voice_quality": 7, "fatigue": 3, "sleep_hours": 7.5},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["checkin_date"] == "2026-01-01"
    assert body["voice_quality"] == 7
    assert body["notes"] is None


def test_create_checkin_allows_skipping_every_optional_field(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/checkins", headers=headers, json={"checkin_date": "2026-01-02"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["voice_quality"] is None
    assert body["fatigue"] is None


def test_create_checkin_requires_a_date(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post("/api/v1/checkins", headers=headers, json={"voice_quality": 5})
    assert resp.status_code == 422


def test_duplicate_checkin_date_is_rejected(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    payload = {"checkin_date": "2026-01-03", "voice_quality": 5}
    first = client.post("/api/v1/checkins", headers=headers, json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/checkins", headers=headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "checkin_already_exists"


def test_edit_checkin(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    created = client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"checkin_date": "2026-01-04", "voice_quality": 4},
    ).json()

    patched = client.patch(
        f"/api/v1/checkins/{created['id']}",
        headers=headers,
        json={"voice_quality": 9, "notes": "felt great after warmup"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["voice_quality"] == 9
    assert body["notes"] == "felt great after warmup"
    # checkin_date is untouched by a partial update
    assert body["checkin_date"] == "2026-01-04"


def test_retrieve_history(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    dates = ["2026-02-01", "2026-02-02", "2026-02-03"]
    for d in dates:
        resp = client.post(
            "/api/v1/checkins", headers=headers, json={"checkin_date": d, "voice_quality": 6}
        )
        assert resp.status_code == 201

    history = client.get("/api/v1/checkins", headers=headers)
    assert history.status_code == 200
    returned_dates = [row["checkin_date"] for row in history.json()]
    # Newest first.
    assert returned_dates == sorted(dates, reverse=True)


def test_retrieve_history_date_range_filter(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    for d in ["2026-03-01", "2026-03-02", "2026-03-03"]:
        client.post("/api/v1/checkins", headers=headers, json={"checkin_date": d})

    filtered = client.get(
        "/api/v1/checkins",
        headers=headers,
        params={"from_date": "2026-03-02", "to_date": "2026-03-02"},
    )
    assert filtered.status_code == 200
    assert [row["checkin_date"] for row in filtered.json()] == ["2026-03-02"]


def test_validation_rejects_out_of_range_scores(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"checkin_date": "2026-04-01", "voice_quality": 11},
    )
    assert resp.status_code == 422


def test_validation_rejects_negative_sleep_hours(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.post(
        "/api/v1/checkins",
        headers=headers,
        json={"checkin_date": "2026-04-02", "sleep_hours": -1},
    )
    assert resp.status_code == 422


def test_checkins_require_authentication(client) -> None:
    resp = client.get("/api/v1/checkins")
    assert resp.status_code == 401


def test_user_cannot_read_another_users_checkin(client, signed_up_user) -> None:
    _user_a, headers_a = signed_up_user

    created = client.post(
        "/api/v1/checkins",
        headers=headers_a,
        json={"checkin_date": "2026-05-01", "voice_quality": 5},
    ).json()

    # A second, independent user.
    headers_b = _second_user_headers(client)

    resp = client.get(f"/api/v1/checkins/{created['id']}", headers=headers_b)
    assert resp.status_code == 404

    resp = client.patch(
        f"/api/v1/checkins/{created['id']}", headers=headers_b, json={"voice_quality": 1}
    )
    assert resp.status_code == 404


def test_user_cannot_see_another_users_checkin_in_history(client, signed_up_user) -> None:
    _user_a, headers_a = signed_up_user
    client.post(
        "/api/v1/checkins", headers=headers_a, json={"checkin_date": "2026-06-01"}
    )

    headers_b = _second_user_headers(client)

    history_b = client.get("/api/v1/checkins", headers=headers_b)
    assert history_b.status_code == 200
    assert history_b.json() == []
