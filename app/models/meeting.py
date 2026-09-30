"""Meeting request model."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Boolean, func, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Meeting(Base):
    """Meeting request from Dograh AI webhook."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meeting_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    meeting_duration: Mapped[int] = mapped_column(Integer, default=30, nullable=False)  # Duration in minutes
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_opportunity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recruiter_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_meetings_active_created", "is_active", "created_at"),
        Index("ix_meetings_email_active", "user_email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Meeting(id={self.id}, user='{self.user_name}', email='{self.user_email}')>"