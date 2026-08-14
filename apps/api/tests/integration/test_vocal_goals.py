"""Goal Tones: AI-recommended low/avg/high targets derived from the singer's own vocal range
history, overridable at any time by a manual value that sticks until cleared."""

from tests.integration.test_vocal_range import upload_range_recording


def test_get_goals_with_no_range_data_is_all_none_ai_source(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.get("/api/v1/vocal-goals", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "target_low_note": None,
        "target_avg_note": None,
        "target_high_note": None,
        "source": "ai",
    }


def test_get_goals_ai_recommendation_derived_from_range_history(
    client, signed_up_user
) -> None:
    _user, headers = signed_up_user
    low = upload_range_recording(client, headers, "range_low", 110.0)  # A2
    high = upload_range_recording(client, headers, "range_high", 440.0)  # A4
    client.post(
        "/api/v1/vocal-range",
        headers=headers,
        json={"low_recording_id": low["id"], "high_recording_id": high["id"]},
    )

    resp = client.get("/api/v1/vocal-goals", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "ai"
    assert body["target_low_note"] == "A2"
    assert body["target_high_note"] == "A4"
    assert body["target_avg_note"] is not None


def test_put_goals_sets_manual_override(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.put(
        "/api/v1/vocal-goals",
        headers=headers,
        json={"target_low_note": "E2", "target_avg_note": "C3", "target_high_note": "G4"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "target_low_note": "E2",
        "target_avg_note": "C3",
        "target_high_note": "G4",
        "source": "manual",
    }

    get_resp = client.get("/api/v1/vocal-goals", headers=headers)
    assert get_resp.json()["source"] == "manual"
    assert get_resp.json()["target_high_note"] == "G4"


def test_put_goals_rejects_invalid_note_name(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    resp = client.put(
        "/api/v1/vocal-goals", headers=headers, json={"target_high_note": "not-a-note"}
    )
    assert resp.status_code == 422


def test_delete_goals_reverts_to_ai_recommendation(client, signed_up_user) -> None:
    _user, headers = signed_up_user
    client.put(
        "/api/v1/vocal-goals",
        headers=headers,
        json={"target_low_note": "E2", "target_avg_note": "C3", "target_high_note": "G4"},
    )

    delete_resp = client.delete("/api/v1/vocal-goals", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get("/api/v1/vocal-goals", headers=headers)
    assert get_resp.json()["source"] == "ai"
    assert get_resp.json()["target_high_note"] is None  # no range data recorded in this test


def test_vocal_goals_require_auth(client) -> None:
    assert client.get("/api/v1/vocal-goals").status_code == 401
    assert client.put("/api/v1/vocal-goals", json={}).status_code == 401
    assert client.delete("/api/v1/vocal-goals").status_code == 401
