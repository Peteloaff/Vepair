"""Append-only admin action logging -- see app.models.AdminAuditLog. Called by every
state-changing admin endpoint (never reads), committed in the same transaction as the action
it's logging so the two can never drift apart."""

import uuid

from sqlalchemy.orm import Session

from app.models import AdminAuditLog


def log_admin_action(
    db: Session,
    admin_user_id: uuid.UUID,
    action: str,
    target_user_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_user_id=target_user_id,
            details=details,
        )
    )
