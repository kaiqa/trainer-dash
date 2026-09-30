"""Trainings REST API for dashboard."""
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload

from app.database import get_async_db
from app.models.training import Training
from app.schemas.training import (
    TrainingResponse,
    TrainingListResponse,
    TrainingUpdate,
    TrainingStatusUpdate,
    TrainingExport,
    TrainingStatus,
)
from app.services.websocket import websocket_manager

router = APIRouter(prefix="/api/trainings", tags=["trainings"])


@router.get(
    "",
    response_model=TrainingListResponse,
    summary="List all training sessions",
    description="Get paginated list of training sessions with optional filtering.",
)
async def list_trainings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in user name, type, body type"),
    status: Optional[str] = Query(None, description="Filter by status (planned/done/skipped)"),
    body_type: Optional[str] = Query(None, description="Filter by body type"),
    user_name: Optional[str] = Query(None, description="Filter by user name"),
    date_from: Optional[date] = Query(None, description="Filter from date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter to date (inclusive)"),
    sort: Optional[str] = Query("created_at:desc", description="Sort field:direction (e.g., created_at:desc, training_date:asc)"),
    db: AsyncSession = Depends(get_async_db),
) -> TrainingListResponse:
    """List all training sessions with pagination and filtering."""
    # Build query
    query = select(Training)
    count_query = select(func.count(Training.id))

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Training.user_name.ilike(search_term),
                Training.type.ilike(search_term),
                Training.body_type.ilike(search_term),
            )
        )
        count_query = count_query.where(
            or_(
                Training.user_name.ilike(search_term),
                Training.type.ilike(search_term),
                Training.body_type.ilike(search_term),
            )
        )

    if status:
        query = query.where(Training.status == status)
        count_query = count_query.where(Training.status == status)

    if body_type:
        query = query.where(Training.body_type == body_type)
        count_query = count_query.where(Training.body_type == body_type)

    if user_name:
        query = query.where(Training.user_name == user_name)
        count_query = count_query.where(Training.user_name == user_name)

    if date_from:
        query = query.where(Training.training_date >= date_from)
        count_query = count_query.where(Training.training_date >= date_from)

    if date_to:
        query = query.where(Training.training_date <= date_to)
        count_query = count_query.where(Training.training_date <= date_to)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting
    if sort:
        try:
            sort_field, sort_direction = sort.split(":")
            if sort_field == "created_at":
                order_col = Training.created_at
            elif sort_field == "training_date":
                order_col = Training.training_date
            elif sort_field == "user_name":
                order_col = Training.user_name
            elif sort_field == "type":
                order_col = Training.type
            elif sort_field == "body_type":
                order_col = Training.body_type
            elif sort_field == "status":
                order_col = Training.status
            elif sort_field == "sets":
                order_col = Training.sets
            elif sort_field == "repetitions":
                order_col = Training.repetitions
            elif sort_field == "time_spent_minutes":
                order_col = Training.time_spent_minutes
            elif sort_field == "weight":
                order_col = Training.weight
            elif sort_field == "training_time":
                order_col = Training.training_time
            else:
                order_col = Training.created_at

            if sort_direction.lower() == "asc":
                query = query.order_by(order_col.asc())
            else:
                query = query.order_by(order_col.desc())
        except ValueError:
            query = query.order_by(Training.created_at.desc())
    else:
        query = query.order_by(Training.created_at.desc())

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    trainings = result.scalars().all()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size

    return TrainingListResponse(
        items=[TrainingResponse.model_validate(t) for t in trainings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{training_id}",
    response_model=TrainingResponse,
    summary="Get single training session",
    description="Get detailed information about a specific training session.",
)
async def get_training(
    training_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> TrainingResponse:
    """Get a single training session by ID."""
    result = await db.execute(
        select(Training).where(Training.id == training_id)
    )
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training with id {training_id} not found",
        )

    return TrainingResponse.model_validate(training)


@router.patch(
    "/{training_id}",
    response_model=TrainingResponse,
    summary="Update training session",
    description="Update a training session.",
)
async def update_training(
    training_id: int,
    training_update: TrainingUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> TrainingResponse:
    """Update a training session."""
    result = await db.execute(
        select(Training).where(Training.id == training_id)
    )
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training with id {training_id} not found",
        )

    # Update fields
    update_data = training_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(training, field, value)

    await db.commit()
    await db.refresh(training)

    # Broadcast update
    training_response = TrainingResponse.model_validate(training)
    await websocket_manager.broadcast({
        "type": "training_updated",
        "data": training_response.model_dump(mode="json"),
    })

    return training_response


@router.patch(
    "/{training_id}/status",
    response_model=TrainingResponse,
    summary="Update training session status",
    description="Update only the status of a training session (planned/done/skipped).",
)
async def update_training_status(
    training_id: int,
    status_update: TrainingStatusUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> TrainingResponse:
    """Update a training session status."""
    result = await db.execute(
        select(Training).where(Training.id == training_id)
    )
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training with id {training_id} not found",
        )

    training.status = status_update.status

    await db.commit()
    await db.refresh(training)

    # Broadcast update
    training_response = TrainingResponse.model_validate(training)
    await websocket_manager.broadcast({
        "type": "training_updated",
        "data": training_response.model_dump(mode="json"),
    })

    return training_response


@router.delete(
    "/{training_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete training session",
    description="Permanently delete a training session.",
)
async def delete_training(
    training_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """Delete a training session."""
    result = await db.execute(
        select(Training).where(Training.id == training_id)
    )
    training = result.scalar_one_or_none()

    if not training:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training with id {training_id} not found",
        )

    await db.delete(training)
    await db.commit()

    # Broadcast deletion
    await websocket_manager.broadcast({
        "type": "training_deleted",
        "data": {"id": training_id},
    })

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/export/all",
    response_model=List[TrainingExport],
    summary="Export all trainings as JSON",
    description="Download all training sessions as JSON array.",
)
async def export_trainings_json(
    db: AsyncSession = Depends(get_async_db),
) -> List[TrainingExport]:
    """Export all trainings as JSON."""
    result = await db.execute(
        select(Training).order_by(Training.created_at.desc())
    )
    trainings = result.scalars().all()

    return [TrainingExport.model_validate(t) for t in trainings]


@router.get(
    "/export/csv",
    summary="Export all trainings as CSV",
    description="Download all training sessions as CSV file.",
)
async def export_trainings_csv(
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    """Export all trainings as CSV."""
    import csv
    import io

    result = await db.execute(
        select(Training).order_by(Training.created_at.desc())
    )
    trainings = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "User Name", "Time Spent (min)", "Date", "Time",
        "Type", "Sets", "Repetitions", "Weight (kg)", "Body Type",
        "Injuries", "Pain", "Pain Source", "Rating", "Session Notes",
        "Status", "Created At", "Updated At"
    ])

    # Data rows
    for training in trainings:
        writer.writerow([
            training.id,
            training.user_name,
            training.time_spent_minutes,
            training.training_date.isoformat() if training.training_date else "",
            training.training_time.isoformat() if training.training_time else "",
            training.type,
            training.sets,
            training.repetitions,
            training.weight if training.weight is not None else "",
            training.body_type,
            training.injuries,
            training.pain,
            training.pain_source or "",
            training.rating if training.rating is not None else "",
            training.session_notes or "",
            training.status,
            training.created_at.isoformat() if training.created_at else "",
            training.updated_at.isoformat() if training.updated_at else "",
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=trainings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@router.get(
    "/stats/summary",
    summary="Get training statistics summary",
    description="Get summary statistics for training sessions.",
)
async def get_training_stats(
    user_name: Optional[str] = Query(None, description="Filter by user name"),
    date_from: Optional[date] = Query(None, description="Filter from date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter to date (inclusive)"),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Get training statistics summary."""
    # Build base query
    query = select(Training)
    if user_name:
        query = query.where(Training.user_name == user_name)
    if date_from:
        query = query.where(Training.training_date >= date_from)
    if date_to:
        query = query.where(Training.training_date <= date_to)

    # Total count
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    # Count by status
    status_counts = {}
    for s in [TrainingStatus.PLANNED, TrainingStatus.DONE, TrainingStatus.SKIPPED]:
        status_query = query.where(Training.status == s)
        result = await db.execute(select(func.count()).select_from(status_query.subquery()))
        status_counts[s] = result.scalar_one()

    # Total time spent
    time_query = query.with_only_columns(func.sum(Training.time_spent_minutes))
    time_result = await db.execute(time_query)
    total_time = time_result.scalar_one() or 0

    # Count by body type
    body_type_query = query.with_only_columns(
        Training.body_type, func.count(Training.id)
    ).group_by(Training.body_type)
    body_type_result = await db.execute(body_type_query)
    body_type_counts = {row[0]: row[1] for row in body_type_result.all()}

    # Count by type
    type_query = query.with_only_columns(
        Training.type, func.count(Training.id)
    ).group_by(Training.type)
    type_result = await db.execute(type_query)
    type_counts = {row[0]: row[1] for row in type_result.all()}

    # Average rating
    rating_query = query.where(Training.rating.isnot(None)).with_only_columns(func.avg(Training.rating))
    rating_result = await db.execute(rating_query)
    avg_rating = rating_result.scalar_one()

    return {
        "total_sessions": total,
        "status_counts": status_counts,
        "total_time_minutes": total_time,
        "body_type_counts": body_type_counts,
        "type_counts": type_counts,
        "average_rating": round(avg_rating, 1) if avg_rating else None,
    }