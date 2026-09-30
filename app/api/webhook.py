"""Webhook endpoint for receiving meeting requests from Dograh AI."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_async_db
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingResponse
from app.services.websocket import websocket_manager
from datetime import timezone

router = APIRouter(prefix="/webhook", tags=["webhook"])


class DograhWebhookPayload(BaseModel):
    """Schema for Dograh AI webhook payload.

    Accepts both Dograh format (recruiter_name, contact_email, meeting_date)
    and legacy format (user_name, user_email, meeting_time) for backwards compatibility.
    """
    model_config = ConfigDict(extra="allow")  # Allow extra fields

    # Dograh AI format (primary)
    recruiter_name: Optional[str] = Field(None, description="Recruiter/caller name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email address")
    meeting_date: Optional[datetime] = Field(None, description="Meeting date/time in ISO 8601")

    # Legacy format (backwards compatible)
    user_name: Optional[str] = Field(None, description="Full name of the user")
    user_email: Optional[EmailStr] = Field(None, description="Email address of the user")
    meeting_time: Optional[datetime] = Field(None, description="Meeting date/time in ISO 8601")

    # Optional fields in both formats
    company_name: Optional[str] = Field(None, description="Caller's company name")
    job_opportunity: Optional[str] = Field(None, description="Job opportunity details")
    meeting_duration: Optional[int] = Field(30, ge=5, le=480, description="Meeting duration in minutes (default 30, min 5, max 480)")


@router.post(
    "/req-meeting",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive meeting request from Dograh AI",
    description="""
    Webhook endpoint for Dograh AI to send meeting requests.

    **Dograh AI format (primary):**
    - recruiter_name: Caller/recruiter name
    - contact_email: Contact email address
    - meeting_date: Meeting date/time in ISO 8601 format (e.g., 2026-10-15T14:00:00Z)
    - meeting_duration: Meeting duration in minutes (optional, default 30, min 5, max 480)
    - company_name: Caller's company name (optional)
    - job_opportunity: Job opportunity details (optional)

    **Alternative format (backwards compatible):**
    - user_name: Full name of the user
    - user_email: Email address of the user
    - meeting_time: Requested meeting date and time in ISO 8601 format
    - meeting_duration: Meeting duration in minutes (optional, default 30, min 5, max 480)
    - company_name: Caller's company name (optional)
    - job_opportunity: Job opportunity details (optional)
    - recruiter_name: Caller's name (optional)

    **Overlap Detection:**
    The endpoint checks for overlapping meetings. A new meeting is rejected if its
    time range (meeting_time to meeting_time + meeting_duration) overlaps with any
    existing active meeting. Two meetings overlap if:
    - new_start < existing_end AND new_end > existing_start
    """,
)
async def receive_meeting_request(
    payload: DograhWebhookPayload = Body(...),
    request: Request = None,
    db: AsyncSession = Depends(get_async_db),
) -> MeetingResponse:
    """
    Receive a meeting request from Dograh AI and store it in the database.

    Handles Dograh AI's field naming (recruiter_name, contact_email, meeting_date)
    and maps to internal model fields (user_name, user_email, meeting_time).

    Broadcasts the new meeting to all connected WebSocket clients for real-time updates.
    """
    # Map fields: Dograh format takes priority, fallback to legacy format
    user_name = payload.user_name or payload.recruiter_name
    user_email = payload.user_email or payload.contact_email
    meeting_time = payload.meeting_time or payload.meeting_date
    meeting_duration = payload.meeting_duration or 30

    # Validate required fields after mapping
    if not user_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: user_name or recruiter_name"
        )
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: user_email or contact_email"
        )
    if not meeting_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: meeting_time or meeting_date"
        )

    # Normalize meeting_time to UTC and strip timezone for comparison with naive DB storage
    try:
        if meeting_time.tzinfo is not None:
            meeting_time_utc = meeting_time.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            meeting_time_utc = meeting_time
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid meeting time format: {str(e)}"
        )

    # Calculate meeting end time
    meeting_end_utc = meeting_time_utc + timedelta(minutes=meeting_duration)

    # Check for overlapping active meetings
    # Two meetings overlap if: new_start < existing_end AND new_end > existing_start
    # We calculate existing_end in Python for each meeting to avoid database-specific functions
    try:
        # First, get all active meetings that could potentially overlap
        # (meetings that start before the new meeting ends)
        potential_overlaps = await db.execute(
            select(Meeting).where(
                Meeting.is_active == True,
                Meeting.meeting_time < meeting_end_utc
            )
        )
        potential_meetings = potential_overlaps.scalars().all()

        # Check each for actual overlap
        existing_meeting = None
        for meeting in potential_meetings:
            existing_end = meeting.meeting_time + timedelta(minutes=meeting.meeting_duration)
            if existing_end > meeting_time_utc:
                existing_meeting = meeting
                break
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

    if existing_meeting:
        existing_end = existing_meeting.meeting_time + timedelta(minutes=existing_meeting.meeting_duration)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "time_slot_taken",
                "message": "The requested meeting time slot overlaps with an existing active meeting",
                "requested_slot": {
                    "start": meeting_time_utc.isoformat(),
                    "end": meeting_end_utc.isoformat(),
                    "duration_minutes": meeting_duration,
                },
                "existing_meeting": {
                    "id": existing_meeting.id,
                    "user_name": existing_meeting.user_name,
                    "user_email": existing_meeting.user_email,
                    "meeting_time": existing_meeting.meeting_time.isoformat() if existing_meeting.meeting_time else None,
                    "meeting_duration": existing_meeting.meeting_duration,
                    "meeting_end": existing_end.isoformat() if existing_end else None,
                    "company_name": existing_meeting.company_name,
                    "recruiter_name": existing_meeting.recruiter_name,
                }
            }
        )

    # Create meeting record (use normalized UTC time without timezone)
    meeting = Meeting(
        user_name=user_name,
        user_email=user_email,
        meeting_time=meeting_time_utc,
        meeting_duration=meeting_duration,
        company_name=payload.company_name,
        job_opportunity=payload.job_opportunity,
        recruiter_name=payload.recruiter_name,
        is_active=True,
    )

    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    # Broadcast to WebSocket clients
    meeting_response = MeetingResponse.model_validate(meeting)
    await websocket_manager.broadcast({
        "type": "meeting_created",
        "data": meeting_response.model_dump(mode="json"),
    })

    return meeting_response


@router.get(
    "/health",
    summary="Webhook health check",
    description="Health check endpoint for the webhook receiver.",
)
async def webhook_health() -> dict:
    """Health check for webhook endpoint."""
    return {"status": "healthy", "service": "webhook"}