"""Meeting request/response schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class MeetingBase(BaseModel):
    """Base meeting schema with common fields."""
    user_name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    user_email: EmailStr = Field(..., description="Email address of the user")
    meeting_time: datetime = Field(..., description="Requested meeting date and time in ISO 8601 format")
    meeting_duration: int = Field(30, ge=5, le=480, description="Meeting duration in minutes")
    company_name: Optional[str] = Field(None, max_length=255, description="Caller's company name")
    job_opportunity: Optional[str] = Field(None, description="Job opportunity details")
    recruiter_name: Optional[str] = Field(None, max_length=255, description="Caller's name")


class MeetingCreate(MeetingBase):
    """Schema for creating a new meeting request (webhook payload)."""
    pass


class MeetingUpdate(BaseModel):
    """Schema for updating a meeting request."""
    is_active: Optional[bool] = Field(None, description="Activate/deactivate meeting request")


class MeetingResponse(MeetingBase):
    """Schema for meeting response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    """Schema for paginated meeting list response."""
    items: List[MeetingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MeetingExport(BaseModel):
    """Schema for meeting export (JSON/CSV)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_name: str
    user_email: str
    meeting_time: datetime
    meeting_duration: int
    company_name: Optional[str] = None
    job_opportunity: Optional[str] = None
    recruiter_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime