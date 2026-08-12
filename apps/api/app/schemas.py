from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    app_env: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
