from datetime import datetime, date
from pydantic import BaseModel


class ProjectKeywordOut(BaseModel):
    id: int
    keyword: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    color: str | None = None
    hourly_rate: float | None = None
    active_from: date | None = None
    active_to: date | None = None
    keywords: list[str] = []
    


class ProjectOut(BaseModel):
    id: int
    name: str
    color: str | None = None
    active_from: date | None = None
    active_to: date | None = None
    is_active: bool
    keywords: list[ProjectKeywordOut] = []

    class Config:
        from_attributes = True


class ActivityLogOut(BaseModel):
    id: int
    app_name: str | None
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    matched_keyword: str | None
    project_id: int | None

    class Config:
        from_attributes = True