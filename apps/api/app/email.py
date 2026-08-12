"""Pluggable email sending. No real provider is wired up yet (Stage 1 has no email
service dependency) — the dev backend logs the message so password reset can be tested
end-to-end. Replace `send_email` with a real provider (SES, SendGrid, Postmark, ...) before
any real user relies on password reset.
"""

import logging

logger = logging.getLogger("vepair.email")


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    logger.info("Password reset requested for %s — token: %s", to_email, reset_token)
