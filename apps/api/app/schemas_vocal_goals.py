from pydantic import BaseModel, field_validator

from app.vocal_range import note_name_to_midi


def _validate_note(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        note_name_to_midi(value)
    except ValueError:
        raise ValueError(f"Not a valid note name: {value!r}") from None
    return value


class VocalGoalIn(BaseModel):
    target_low_note: str | None = None
    target_avg_note: str | None = None
    target_high_note: str | None = None

    _validate_low = field_validator("target_low_note")(_validate_note)
    _validate_avg = field_validator("target_avg_note")(_validate_note)
    _validate_high = field_validator("target_high_note")(_validate_note)


class VocalGoalOut(BaseModel):
    target_low_note: str | None
    target_avg_note: str | None
    target_high_note: str | None
    source: str
