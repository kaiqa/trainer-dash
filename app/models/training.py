"""Training session model."""
from datetime import datetime, date, time
from typing import Optional
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, func, Index, Integer, Enum as SQLEnum, Date, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TrainingStatus(str, Enum):
    """Training session status."""
    PLANNED = "planned"
    DONE = "done"
    SKIPPED = "skipped"


class Training(Base):
    """Training session from Dogbrah AI webhook."""

    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    time_spent_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    training_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    training_time: Mapped[time] = mapped_column(Time, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., "squads", "bench_press"
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # weight in kg
    body_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., "legs", "chest", "back"
    injuries: Mapped[str] = mapped_column(String(10), nullable=False, default="no")  # "yes" or "no"
    pain: Mapped[str] = mapped_column(String(10), nullable=False, default="no")  # "yes" or "no"
    pain_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g., "knees"
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10
    session_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(TrainingStatus, values_callable=lambda x: [e.value for e in x]),
        default=TrainingStatus.PLANNED,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_trainings_status_created", "status", "created_at"),
        Index("ix_trainings_user_date", "user_name", "training_date"),
        Index("ix_trainings_body_type_date", "body_type", "training_date"),
    )

    def __repr__(self) -> str:
        return f"<Training(id={self.id}, user='{self.user_name}', type='{self.type}', date='{self.training_date}')>"