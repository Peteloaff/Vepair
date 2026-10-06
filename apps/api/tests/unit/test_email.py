from unittest.mock import MagicMock, patch

import app.email as email_module


class TestSendPasswordResetEmailLogBackend:
    def test_logs_the_reset_link_and_never_calls_httpx(self, monkeypatch, caplog) -> None:
        monkeypatch.setattr(email_module.settings, "email_backend", "log")
        monkeypatch.setattr(email_module.settings, "frontend_base_url", "https://vepair.com")
        with patch("httpx.post") as mock_post:
            with caplog.at_level("INFO", logger="vepair.email"):
                email_module.send_password_reset_email("singer@example.com", "abc123")
        mock_post.assert_not_called()
        assert "singer@example.com" in caplog.text
        assert "https://vepair.com/reset-password?token=abc123" in caplog.text


class TestSendPasswordResetEmailGraphBackend:
    def _mock_token_response(self) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"access_token": "fake-token", "expires_in": 3600}
        return resp

    def _mock_send_response(self, status_code: int = 202) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = ""
        return resp

    def _configure_settings(self, monkeypatch) -> None:
        monkeypatch.setattr(email_module.settings, "email_backend", "graph")
        monkeypatch.setattr(email_module.settings, "frontend_base_url", "https://vepair.com")
        monkeypatch.setattr(email_module.settings, "email_from_address", "noreply@vepair.com")
        monkeypatch.setattr(email_module.settings, "ms_graph_tenant_id", "tenant-id")
        monkeypatch.setattr(email_module.settings, "ms_graph_client_id", "client-id")
        monkeypatch.setattr(email_module.settings, "ms_graph_client_secret", "client-secret")
        # A cached token from a previous test must never leak into this one.
        monkeypatch.setattr(email_module, "_cached_token", None)
        monkeypatch.setattr(email_module, "_cached_token_expires_at", 0.0)

    def test_sends_via_graph_with_a_real_reset_link(self, monkeypatch) -> None:
        self._configure_settings(monkeypatch)
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = [self._mock_token_response(), self._mock_send_response()]
            email_module.send_password_reset_email("singer@example.com", "abc123")

        assert mock_post.call_count == 2
        token_call, send_call = mock_post.call_args_list
        assert token_call.args[0] == (
            "https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token"
        )
        assert send_call.args[0] == (
            "https://graph.microsoft.com/v1.0/users/noreply@vepair.com/sendMail"
        )
        sent_message = send_call.kwargs["json"]
        assert sent_message["message"]["toRecipients"][0]["emailAddress"]["address"] == (
            "singer@example.com"
        )
        assert (
            "https://vepair.com/reset-password?token=abc123"
            in (sent_message["message"]["body"]["content"])
        )
        assert send_call.kwargs["headers"]["Authorization"] == "Bearer fake-token"

    def test_token_is_cached_across_two_sends(self, monkeypatch) -> None:
        self._configure_settings(monkeypatch)
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = [
                self._mock_token_response(),
                self._mock_send_response(),
                self._mock_send_response(),
            ]
            email_module.send_password_reset_email("a@example.com", "tok1")
            email_module.send_password_reset_email("b@example.com", "tok2")

        # Only one token request across both sends -- the second send reuses the cached token.
        assert mock_post.call_count == 3

    def test_a_failed_send_is_logged_and_never_raises(self, monkeypatch, caplog) -> None:
        self._configure_settings(monkeypatch)
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = [
                self._mock_token_response(),
                self._mock_send_response(status_code=500),
            ]
            with caplog.at_level("ERROR", logger="vepair.email"):
                email_module.send_password_reset_email("singer@example.com", "abc123")
        assert "Failed to send email" in caplog.text

    def test_a_failed_token_request_is_logged_and_never_raises(self, monkeypatch, caplog) -> None:
        self._configure_settings(monkeypatch)
        bad_token_resp = MagicMock()
        bad_token_resp.status_code = 401
        bad_token_resp.text = "invalid_client"
        with patch("httpx.post", return_value=bad_token_resp):
            with caplog.at_level("ERROR", logger="vepair.email"):
                email_module.send_password_reset_email("singer@example.com", "abc123")
        assert "Failed to send email" in caplog.text


def test_coach_invite_email_for_a_new_person_links_to_signup_with_their_email(monkeypatch) -> None:
    from app import email as email_module

    captured = {}
    monkeypatch.setattr(
        email_module,
        "_send",
        lambda to, subject, html_body, text_body: captured.update(
            to=to, subject=subject, html=html_body, text=text_body
        ),
    )
    email_module.send_coach_invite_email(
        "new.person@example.com", "Alex <Coach>", "Harbor Studio", 'Hi "there"', has_account=False
    )
    assert captured["to"] == "new.person@example.com"
    assert "/signup?email=new.person%40example.com&invite=1" in captured["text"]
    assert "join VepAIr" in captured["subject"]
    # Coach-supplied text is escaped in the HTML body.
    assert "<Coach>" not in captured["html"]
    assert "&lt;Coach&gt;" in captured["html"]


def test_coach_invite_email_for_an_existing_user_links_to_coach_access(monkeypatch) -> None:
    from app import email as email_module

    captured = {}
    monkeypatch.setattr(
        email_module,
        "_send",
        lambda to, subject, html_body, text_body: captured.update(text=text_body),
    )
    email_module.send_coach_invite_email("a@example.com", "Alex", None, None, has_account=True)
    assert "/coach-access" in captured["text"]
    assert "signup" not in captured["text"]
