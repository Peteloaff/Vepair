from datetime import datetime

from pydantic import BaseModel

# Kept in sync with the consent_type comment on app.models.ConsentRecord and PRIVACY.md
# section 3 — a whitelist, not free text, so a typo can't silently create an untracked
# consent purpose no code actually checks.
VALID_CONSENT_TYPES = {
    "product_analytics",
    "model_training",
    "coach_sharing",
    "notifications",
}


class ConsentIn(BaseModel):
    granted: bool


class ConsentOut(BaseModel):
    consent_type: str
    # None means this user has never made a choice for this purpose yet — distinct from an
    # explicit False, which is a real decision that must be respected the same as True.
    granted: bool | None
    granted_at: datetime | None

    model_config = {"from_attributes": True}
