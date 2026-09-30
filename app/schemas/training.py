"""Training session schemas."""
from datetime import date, time, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TrainingStatus(str):
    """Training session status."""
    PLANNED = "planned"
    DONE = "done"
    SKIPPED = "skipped"


class TrainingBase(BaseModel):
    """Base training schema with common fields."""
    user_name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    time_spent_minutes: int = Field(..., ge=1, le=480, description="Time spent in minutes")
    training_date: date = Field(..., description="Training date")
    training_time: time = Field(..., description="Training time")
    type: str = Field(..., min_length=1, max_length=100, description="Training type (e.g., squats, bench_press)")
    sets: int = Field(..., ge=1, le=50, description="Number of sets")
    repetitions: int = Field(..., ge=1, le=100, description="Number of repetitions per set")
    weight: Optional[float] = Field(None, ge=0, le=500, description="Weight in kg")
    body_type: str = Field(..., min_length=1, max_length=100, description="Body type trained (e.g., legs, chest, back)")
    injuries: str = Field("no", pattern="^(yes|no)$", description="Whether user has injuries (yes/no)")
    pain: str = Field("no", pattern="^(yes|no)$", description="Whether user experienced pain (yes/no)")
    pain_source: Optional[str] = Field(None, max_length=255, description="Source of pain if any")
    rating: Optional[int] = Field(None, ge=1, le=10, description="Training rating 1-10")
    session_notes: Optional[str] = Field(None, description="Session notes")


class TrainingCreate(TrainingBase):
    """Schema for creating a new training session (webhook payload)."""
    pass


class TrainingUpdate(BaseModel):
    """Schema for updating a training session."""
    time_spent_minutes: Optional[int] = Field(None, ge=1, le=480)
    training_date: Optional[date] = None
    training_time: Optional[time] = None
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    sets: Optional[int] = Field(None, ge=1, le=50)
    repetitions: Optional[int] = Field(None, ge=1, le=100)
    weight: Optional[float] = Field(None, ge=0, le=500)
    body_type: Optional[str] = Field(None, min_length=1, max_length=100)
    injuries: Optional[str] = Field(None, pattern="^(yes|no)$")
    pain: Optional[str] = Field(None, pattern="^(yes|no)$")
    pain_source: Optional[str] = Field(None, max_length=255)
    rating: Optional[int] = Field(None, ge=1, le=10)
    session_notes: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(planned|done|skipped)$")


class TrainingStatusUpdate(BaseModel):
    """Schema for updating only the status of a training session."""
    status: str = Field(..., pattern="^(planned|done|skipped)$")


class TrainingResponse(TrainingBase):
    """Schema for training response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime
    updated_at: datetime


class TrainingListResponse(BaseModel):
    """Schema for paginated training list response."""
    items: List[TrainingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TrainingExport(BaseModel):
    """Schema for training export (JSON/CSV)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_name: str
    time_spent_minutes: int
    training_date: date
    training_time: time
    type: str
    sets: int
    repetitions: int
    weight: Optional[float] = None
    body_type: str
    injuries: str
    pain: str
    pain_source: Optional[str] = None
    rating: Optional[int] = None
    session_notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime