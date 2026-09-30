"""Meetings REST API for dashboard."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_async_db
from app.models.meeting import Meeting
from app.schemas.meeting import (
    MeetingResponse,
    MeetingListResponse,
    MeetingUpdate,
    MeetingExport,
)
from app.services.websocket import websocket_manager

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.get(
    "",
    response_model=MeetingListResponse,
    summary="List all meeting requests",
    description="Get paginated list of meeting requests with optional filtering.",
)
async def list_meetings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in name, email, company"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_async_db),
) -> MeetingListResponse:
    """List all meeting requests with pagination and filtering."""
    # Build query
    query = select(Meeting)
    count_query = select(func.count(Meeting.id))

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Meeting.user_name.ilike(search_term),
                Meeting.user_email.ilike(search_term),
                Meeting.company_name.ilike(search_term),
                Meeting.recruiter_name.ilike(search_term),
            )
        )
        count_query = count_query.where(
            or_(
                Meeting.user_name.ilike(search_term),
                Meeting.user_email.ilike(search_term),
                Meeting.company_name.ilike(search_term),
                Meeting.recruiter_name.ilike(search_term),
            )
        )

    if is_active is not None:
        query = query.where(Meeting.is_active == is_active)
        count_query = count_query.where(Meeting.is_active == is_active)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Meeting.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    meetings = result.scalars().all()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size

    return MeetingListResponse(
        items=[MeetingResponse.model_validate(m) for m in meetings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="Get single meeting request",
    description="Get detailed information about a specific meeting request.",
)
async def get_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> MeetingResponse:
    """Get a single meeting request by ID."""
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with id {meeting_id} not found",
        )

    return MeetingResponse.model_validate(meeting)


@router.patch(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="Update meeting request",
    description="Update a meeting request (e.g., activate/deactivate).",
)
async def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> MeetingResponse:
    """Update a meeting request."""
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with id {meeting_id} not found",
        )

    # Update fields
    update_data = meeting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meeting, field, value)

    await db.commit()
    await db.refresh(meeting)

    # Broadcast update
    meeting_response = MeetingResponse.model_validate(meeting)
    await websocket_manager.broadcast({
        "type": "meeting_updated",
        "data": meeting_response.model_dump(mode="json"),
    })

    return meeting_response


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete meeting request",
    description="Permanently delete a meeting request.",
)
async def delete_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """Delete a meeting request."""
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with id {meeting_id} not found",
        )

    await db.delete(meeting)
    await db.commit()

    # Broadcast deletion
    await websocket_manager.broadcast({
        "type": "meeting_deleted",
        "data": {"id": meeting_id},
    })

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/export/all",
    response_model=list[MeetingExport],
    summary="Export all meetings as JSON",
    description="Download all meeting requests as JSON array.",
)
async def export_meetings_json(
    db: AsyncSession = Depends(get_async_db),
) -> list[MeetingExport]:
    """Export all meetings as JSON."""
    result = await db.execute(
        select(Meeting).order_by(Meeting.created_at.desc())
    )
    meetings = result.scalars().all()

    return [MeetingExport.model_validate(m) for m in meetings]


@router.get(
    "/export/csv",
    summary="Export all meetings as CSV",
    description="Download all meeting requests as CSV file.",
)
async def export_meetings_csv(
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """Export all meetings as CSV."""
    import csv
    import io

    result = await db.execute(
        select(Meeting).order_by(Meeting.created_at.desc())
    )
    meetings = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "User Name", "User Email", "Meeting Time", "Duration (min)",
        "Company Name", "Job Opportunity", "Recruiter Name",
        "Active", "Created At", "Updated At"
    ])

    # Data rows
    for meeting in meetings:
        writer.writerow([
            meeting.id,
            meeting.user_name,
            meeting.user_email,
            meeting.meeting_time.isoformat() if meeting.meeting_time else "",
            meeting.meeting_duration,
            meeting.company_name or "",
            meeting.job_opportunity or "",
            meeting.recruiter_name or "",
            "Yes" if meeting.is_active else "No",
            meeting.created_at.isoformat() if meeting.created_at else "",
            meeting.updated_at.isoformat() if meeting.updated_at else "",
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=meetings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )