from datetime import date

from pydantic import BaseModel


class ConsistencyDayOut(BaseModel):
    for_date: date
    sessions_completed: int


class TrainingConsistencyOut(BaseModel):
    days: list[ConsistencyDayOut]
    current_streak_days: int
    longest_streak_days: int
    total_sessions_in_range: int
