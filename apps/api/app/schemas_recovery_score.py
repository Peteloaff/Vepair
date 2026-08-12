from datetime import date

from pydantic import BaseModel


class RecoveryScoreComponentOut(BaseModel):
    key: str
    label: str
    score: float | None
    weight: float
    included: bool


class RecoveryScoreFactorOut(BaseModel):
    direction: str  # "positive" | "negative"
    text: str


class RecoveryScoreOut(BaseModel):
    score_date: date
    score_value: int | None
    confidence_label: str
    status: str  # "green" | "yellow" | "red" | "unknown"
    status_label: str
    safety_message: str | None
    components: list[RecoveryScoreComponentOut]
    factors: list[RecoveryScoreFactorOut]


class ScoreHistoryPointOut(BaseModel):
    score_date: date
    score_value: int | None
    confidence_label: str | None
    status: str | None
