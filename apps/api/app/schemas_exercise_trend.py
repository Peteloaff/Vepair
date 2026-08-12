import uuid

from pydantic import BaseModel


class ExerciseTrendOut(BaseModel):
    exercise_id: uuid.UUID
    exercise_name: str
    metric_name: str
    direction: str
    recent_median: float | None
    prior_median: float | None
    attempt_count: int
