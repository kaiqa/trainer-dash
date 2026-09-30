"""Webhook endpoint for receiving training sessions from Dogbrah AI."""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date, time
from typing import Optional

from app.database import get_async_db
from app.models.training import Training
from app.schemas.training import TrainingResponse, TrainingStatus
from app.services.websocket import websocket_manager

router = APIRouter(prefix="/webhook", tags=["webhook"])


class DogbrahTrainingPayload(BaseModel):
    """Schema for Dogbrah AI training webhook payload.

    Expected format:
    {
      "user_name": "kai",
      "time_spend_minutes": 30,
      "date": "29.09.2026",
      "time": "10:00",
      "type": "squads",
      "sets": "3",
      "repetitions": "12",
      "weight": "77",
      "body_type": "legs",
      "injuries": "no",
      "pain": "yes",
      "pain_source": "knees",
      "rating": "7",
      "session_notes": "it was a hard training and my knees did hurt a little but nothing mayor give a rating 7 out of ten stars"
    }

    For cardio activities (cycling, running, etc.), sets and repetitions can be omitted or set to "0".
    """
    model_config = ConfigDict(extra="allow")  # Allow extra fields

    user_name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    time_spend_minutes: int = Field(..., description="Time spent in minutes")
    date: str = Field(..., description="Training date in DD.MM.YYYY format")
    time: str = Field(..., description="Training time in HH:MM format")
    type: str = Field(..., description="Training type (e.g., squats, bench_press)")
    sets: Optional[str] = Field(None, description="Number of sets (optional, 0 for cardio)")
    repetitions: Optional[str] = Field(None, description="Number of repetitions per set (optional, 0 for cardio)")
    weight: Optional[str] = Field(None, description="Weight in kg")
    body_type: str = Field(..., description="Body type trained (e.g., legs, chest, back)")
    injuries: str = Field(..., description="Whether user has injuries (yes/no)")
    pain: str = Field(..., description="Whether user experienced pain (yes/no)")
    pain_source: Optional[str] = Field(None, description="Source of pain if any")
    rating: Optional[str] = Field(None, description="Training rating 1-10")
    session_notes: Optional[str] = Field(None, description="Session notes")


@router.post(
    "/record-training",
    response_model=TrainingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive training session from Dogbrah AI",
    description="""
    Webhook endpoint for Dogbrah AI to send training session data.

    **Dogbrah AI format:**
    - user_name: Full name of the user
    - time_spend_minutes: Time spent in minutes
    - date: Training date in DD.MM.YYYY format (e.g., 29.09.2026)
    - time: Training time in HH:MM format (e.g., 10:00)
    - type: Training type (e.g., squats, bench_press)
    - sets: Number of sets
    - repetitions: Number of repetitions per set
    - weight: Weight in kg (optional)
    - body_type: Body type trained (e.g., legs, chest, back)
    - injuries: Whether user has injuries (yes/no)
    - pain: Whether user experienced pain (yes/no)
    - pain_source: Source of pain if any (optional)
    - rating: Training rating 1-10 (optional)
    - session_notes: Session notes (optional)

    **Response:** `201 Created` with training session object
    """,
)
async def receive_training_session(
    payload: DogbrahTrainingPayload = Body(...),
    db: AsyncSession = Depends(get_async_db),
) -> TrainingResponse:
    """
    Receive a training session from Dogbrah AI and store it in the database.

    Broadcasts the new training session to all connected WebSocket clients for real-time updates.
    """
    # Parse date (DD.MM.YYYY format)
    try:
        training_date = datetime.strptime(payload.date, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format. Expected DD.MM.YYYY, got: {payload.date}"
        )

    # Parse time (HH:MM format)
    try:
        training_time = datetime.strptime(payload.time, "%H:%M").time()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid time format. Expected HH:MM, got: {payload.time}"
        )

    # Parse numeric fields (default to 0 for cardio activities)
    try:
        sets = int(payload.sets) if payload.sets else 0
        repetitions = int(payload.repetitions) if payload.repetitions else 0
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sets and repetitions must be valid integers"
        )

    # Parse weight if provided
    weight = None
    if payload.weight:
        try:
            weight = float(payload.weight)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid weight format: {payload.weight}"
            )

    # Parse rating if provided
    rating = None
    if payload.rating:
        try:
            rating = int(payload.rating)
            if rating < 1 or rating > 10:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Rating must be between 1 and 10"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid rating format: {payload.rating}"
            )

    # Validate injuries and pain fields
    if payload.injuries not in ("yes", "no"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="injuries must be 'yes' or 'no'"
        )

    if payload.pain not in ("yes", "no"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pain must be 'yes' or 'no'"
        )

    # If pain is yes, pain_source should be provided
    if payload.pain == "yes" and not payload.pain_source:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pain_source is required when pain is 'yes'"
        )

    # Create training record
    training = Training(
        user_name=payload.user_name,
        time_spent_minutes=payload.time_spend_minutes,
        training_date=training_date,
        training_time=training_time,
        type=payload.type,
        sets=sets,
        repetitions=repetitions,
        weight=weight,
        body_type=payload.body_type,
        injuries=payload.injuries,
        pain=payload.pain,
        pain_source=payload.pain_source,
        rating=rating,
        session_notes=payload.session_notes,
        status=TrainingStatus.PLANNED,
    )

    db.add(training)
    await db.commit()
    await db.refresh(training)

    # Broadcast to WebSocket clients
    training_response = TrainingResponse.model_validate(training)
    await websocket_manager.broadcast({
        "type": "training_created",
        "data": training_response.model_dump(mode="json"),
    })

    return training_response


@router.get(
    "/health",
    summary="Webhook health check",
    description="Health check endpoint for the webhook receiver.",
)
async def webhook_health() -> dict:
    """Health check for webhook endpoint."""
    return {"status": "healthy", "service": "webhook"}