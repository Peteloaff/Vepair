"""Singleton row access for app.models.SiteSettings -- see that model's docstring."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SiteSettings

SETTINGS_ROW_ID = 1


def get_site_settings(db: Session) -> SiteSettings:
    """The migration seeds the id=1 row, but this falls back to creating it on read so a
    database that skipped that seed (e.g. a fresh local dev DB built from a stale snapshot)
    still works instead of 500ing."""
    settings_row = db.scalar(select(SiteSettings).where(SiteSettings.id == SETTINGS_ROW_ID))
    if settings_row is None:
        settings_row = SiteSettings(id=SETTINGS_ROW_ID)
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row
