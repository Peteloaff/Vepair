"""Backend Admin (post-Stage-12). Mirrors app/coach_auth.py's get_current_coach exactly, but
the "is this an admin" check is a flag on User itself rather than a separate profile table --
there's no equivalent of CoachProfile for admins, since an admin isn't a distinct account type
with its own data, just an authenticated account with elevated privileges.

Bootstrapping the first admin has no self-serve or API path, ever -- see TECHNICAL_GUIDE.md for
the one-time manual `UPDATE users SET is_admin = true WHERE email = '<founder email>'`.
"""

from fastapi import Depends, HTTPException

from app.auth import get_current_user
from app.models import User

NOT_AN_ADMIN = HTTPException(
    status_code=403,
    detail={"code": "not_an_admin", "message": "This account does not have admin access."},
)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise NOT_AN_ADMIN
    return current_user


FULL_ADMIN_REQUIRED = HTTPException(
    status_code=403,
    detail={
        "code": "full_admin_required",
        "message": "This action requires full admin access.",
    },
)


def require_full_admin(admin: User = Depends(get_current_admin)) -> User:
    """The higher of two admin tiers (see User.admin_role's docstring). A null admin_role
    reads as "full" -- the pre-existing meaning of is_admin=True, before this tier split
    existed -- so only an explicit admin_role == "support" is ever turned away here."""
    if admin.admin_role == "support":
        raise FULL_ADMIN_REQUIRED
    return admin
