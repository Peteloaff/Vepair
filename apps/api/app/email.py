"""Pluggable email sending, mirroring app/storage.py's backend-dispatch pattern.

EMAIL_BACKEND=log (default): logs the message server-side instead of sending — the original
Stage 1 behavior, still what the test suite and local dev use unless explicitly overridden.

EMAIL_BACKEND=graph: sends real mail via Microsoft Graph (Microsoft 365 / Office 365), using
OAuth2 client-credentials against an Azure app registration with the Mail.Send application
permission — deliberately not raw SMTP with a mailbox password, since Microsoft has been
retiring Basic Auth for SMTP AUTH and a client-credentials app registration is the durable,
Microsoft-recommended path for an app sending as a fixed mailbox (e.g. noreply@vepair.com).
"""

import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger("vepair.email")
settings = get_settings()

_GRAPH_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_GRAPH_SEND_MAIL_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
_GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Module-level cache: a single client-credentials token is valid for ~1 hour and is the same
# for every send regardless of recipient, so fetching a fresh one per email would be wasteful.
_cached_token: str | None = None
_cached_token_expires_at: float = 0.0


class EmailSendError(Exception):
    pass


def _get_graph_access_token() -> str:
    global _cached_token, _cached_token_expires_at

    if _cached_token is not None and time.monotonic() < _cached_token_expires_at:
        return _cached_token

    resp = httpx.post(
        _GRAPH_TOKEN_URL.format(tenant_id=settings.ms_graph_tenant_id),
        data={
            "client_id": settings.ms_graph_client_id,
            "client_secret": settings.ms_graph_client_secret,
            "scope": _GRAPH_SCOPE,
            "grant_type": "client_credentials",
        },
        timeout=10.0,
    )
    if resp.status_code != 200:
        raise EmailSendError(f"Graph token request failed: {resp.status_code} {resp.text}")

    body = resp.json()
    _cached_token = body["access_token"]
    # Refresh a minute early rather than exactly at expiry.
    _cached_token_expires_at = time.monotonic() + max(body.get("expires_in", 3600) - 60, 0)
    return _cached_token


def _send_via_graph(to_email: str, subject: str, html_body: str) -> None:
    token = _get_graph_access_token()

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": False,
    }
    resp = httpx.post(
        _GRAPH_SEND_MAIL_URL.format(sender=settings.email_from_address),
        json=message,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    if resp.status_code != 202:
        raise EmailSendError(f"Graph sendMail failed: {resp.status_code} {resp.text}")


def _send(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    if settings.email_backend == "graph":
        try:
            _send_via_graph(to_email, subject, html_body)
        except (httpx.HTTPError, EmailSendError) as exc:
            # Never let an email provider outage break the calling request (e.g. password-reset
            # request must still return its generic 202) — log loudly and move on.
            logger.error("Failed to send email to %s: %s", to_email, exc)
    else:
        logger.info("[email:log] to=%s subject=%r\n%s", to_email, subject, text_body)


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{settings.frontend_base_url}/reset-password?token={reset_token}"
    subject = "Reset your VepAIr password"
    text_body = (
        f"We received a request to reset your VepAIr password.\n\n"
        f"Reset it here: {reset_url}\n\n"
        f"This link expires in {settings.password_reset_token_expire_minutes} minutes. "
        f"If you didn't request this, you can safely ignore this email."
    )
    html_body = (
        f'<p>We received a request to reset your VepAIr password.</p>'
        f'<p><a href="{reset_url}">Reset your password</a></p>'
        f"<p>This link expires in {settings.password_reset_token_expire_minutes} minutes. "
        f"If you didn't request this, you can safely ignore this email.</p>"
    )
    _send(to_email, subject, html_body, text_body)


def send_checkin_reminder_email(to_email: str) -> None:
    """The only reminder type in v1 -- see app/reminders.py's send_daily_checkin_reminders,
    the sole caller. Only ever sent to a user with explicit notifications consent granted."""
    checkin_url = f"{settings.frontend_base_url}/"
    subject = "How's your voice today?"
    text_body = (
        "You haven't logged a check-in yet today. A quick check-in helps VepAIr keep your "
        "recovery score and daily routine tuned to how you're actually doing.\n\n"
        f"Check in here: {checkin_url}\n\n"
        "You're getting this because you opted into practice reminders -- turn them off any "
        "time from your Profile page."
    )
    html_body = (
        "<p>You haven't logged a check-in yet today. A quick check-in helps VepAIr keep your "
        "recovery score and daily routine tuned to how you're actually doing.</p>"
        f'<p><a href="{checkin_url}">Check in now</a></p>'
        "<p>You're getting this because you opted into practice reminders — turn them off any "
        "time from your Profile page.</p>"
    )
    _send(to_email, subject, html_body, text_body)


def send_new_message_email(to_email: str, from_label: str) -> None:
    """Sent synchronously at message-creation time (app/routers/coach.py's send_message,
    app/routers/coach_access.py's send_message_to_coach) -- a discrete event, not a daily
    batch, so it doesn't go through app/reminders.py. Only ever sent to a recipient with
    explicit notifications consent granted; a failure here must never fail the message send
    itself (see _send's own try/except)."""
    inbox_url = f"{settings.frontend_base_url}/"
    subject = f"New message from {from_label}"
    text_body = (
        f"{from_label} sent you a new message on VepAIr.\n\n"
        f"Read it here: {inbox_url}\n\n"
        "You're getting this because you opted into notifications -- turn them off any time "
        "from your Profile page."
    )
    html_body = (
        f"<p>{from_label} sent you a new message on VepAIr.</p>"
        f'<p><a href="{inbox_url}">Read it now</a></p>'
        "<p>You're getting this because you opted into notifications — turn them off any time "
        "from your Profile page.</p>"
    )
    _send(to_email, subject, html_body, text_body)
