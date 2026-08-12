def test_profile_missing_before_onboarding(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/profile", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "profile_not_found"


def test_profile_upsert_creates_then_updates(client, signed_up_user) -> None:
    _user, headers = signed_up_user

    created = client.put(
        "/api/v1/profile",
        headers=headers,
        json={"is_singer": True, "musical_style": "rock/metal", "goals": "recover range"},
    )
    assert created.status_code == 200
    assert created.json()["is_singer"] is True

    updated = client.put(
        "/api/v1/profile",
        headers=headers,
        json={"is_singer": True, "practice_frequency": "daily"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["practice_frequency"] == "daily"
    # Fields omitted from the second PUT reset to null — PUT is a full replace, not a patch.
    assert body["musical_style"] is None


def test_profile_all_fields_are_skippable(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.put("/api/v1/profile", headers=headers, json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_singer"] is None
    assert body["goals"] is None


def test_profile_requires_authentication(client) -> None:
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 401


def test_profile_has_no_medical_diagnosis_fields(client, signed_up_user) -> None:
    """Guards MEDICAL_SAFETY.md: onboarding must never collect a diagnosis."""
    _user, headers = signed_up_user
    resp = client.put("/api/v1/profile", headers=headers, json={"is_singer": True})
    fields = set(resp.json().keys())
    banned_substrings = ["diagnos", "nodule", "pathology", "disorder"]
    for field in fields:
        for banned in banned_substrings:
            assert banned not in field.lower()
