"""Pytest configuration and fixtures."""
import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from app.config import Settings, get_settings
from app.database import Base, get_async_db
from app.main import app
from app.models.meeting import Meeting
from app.models.setting import Setting
from app.models.training import Training
from app.schemas.meeting import MeetingCreate
from app.schemas.training import TrainingCreate
from app.services.websocket import WebSocketManager

fake = Faker()


# Override settings for testing
class TestSettings(Settings):
    app_env: str = "test"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./test.db"
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 5687
    webhook_path: str = "/webhook/req-meeting"
    training_webhook_path: str = "/webhook/record-training"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    """Test settings instance."""
    return TestSettings()


@pytest.fixture(scope="function")
def sync_engine():
    """Create synchronous test engine with SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Create synchronous test session."""
    SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create asynchronous test engine with SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create asynchronous test session."""
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(scope="function")
def override_get_db(sync_session):
    """Override database dependency for sync tests."""
    def _get_db():
        try:
            yield sync_session
        finally:
            pass

    app.dependency_overrides[get_async_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def override_get_async_db(async_session):
    """Override database dependency for async tests."""
    async def _get_db():
        yield async_session

    app.dependency_overrides[get_async_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client(override_get_async_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def websocket_manager() -> WebSocketManager:
    """Create WebSocket manager instance."""
    return WebSocketManager()


@pytest.fixture(scope="function")
def sample_meeting_data() -> dict[str, Any]:
    """Generate sample meeting data."""
    return {
        "user_name": fake.name(),
        "user_email": fake.email(),
        "meeting_time": fake.future_datetime(end_date="+30d"),
        "company_name": fake.company(),
        "job_opportunity": fake.job(),
        "recruiter_name": fake.name(),
    }


@pytest.fixture(scope="function")
async def sample_meeting(async_session, sample_meeting_data) -> Meeting:
    """Create a sample meeting in the database."""
    meeting = Meeting(**sample_meeting_data, is_active=True)
    async_session.add(meeting)
    await async_session.commit()
    await async_session.refresh(meeting)
    return meeting


@pytest.fixture(scope="function")
async def multiple_meetings(async_session) -> list[Meeting]:
    """Create multiple sample meetings."""
    meetings = []
    for i in range(5):
        data = {
            "user_name": fake.name(),
            "user_email": fake.email(),
            "meeting_time": fake.future_datetime(end_date="+30d"),
            "company_name": fake.company() if i % 2 == 0 else None,
            "job_opportunity": fake.job() if i % 3 == 0 else None,
            "recruiter_name": fake.name() if i % 2 == 0 else None,
            "is_active": i % 2 == 0,
        }
        meeting = Meeting(**data)
        async_session.add(meeting)
        meetings.append(meeting)
    await async_session.commit()
    for m in meetings:
        await async_session.refresh(m)
    return meetings


@pytest.fixture(scope="function")
async def sample_settings(async_session) -> list[Setting]:
    """Create sample settings."""
    settings_data = [
        {"key": "webhook_host", "value": "0.0.0.0", "description": "IP address to bind webhook server"},
        {"key": "webhook_port", "value": "5687", "description": "Port for webhook server"},
        {"key": "webhook_path", "value": "/webhook/req-meeting", "description": "Webhook endpoint path for meetings"},
        {"key": "training_webhook_path", "value": "/webhook/record-training", "description": "Webhook endpoint path for training sessions"},
    ]
    settings = [Setting(**data) for data in settings_data]
    async_session.add_all(settings)
    await async_session.commit()
    for s in settings:
        await async_session.refresh(s)
    return settings


@pytest.fixture(scope="function")
def mock_websocket() -> AsyncMock:
    """Create mock WebSocket for testing."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture(scope="function")
def sample_training_data() -> dict[str, Any]:
    """Generate sample training data in Dogbrah format."""
    pain = fake.random_element(["yes", "no"])
    # Ensure pain_source is provided when pain is "yes"
    pain_source = None
    if pain == "yes":
        pain_source = fake.random_element(["knees", "lower_back", "shoulders", "wrists"])
    else:
        pain_source = fake.random_element(["knees", "lower_back", "shoulders", "wrists", None])

    return {
        "user_name": fake.name(),
        "time_spend_minutes": fake.random_int(min=10, max=120),
        "date": fake.date_between(start_date="-30d", end_date="+30d").strftime("%d.%m.%Y"),
        "time": f"{fake.random_int(min=6, max=22):02d}:{fake.random_element([0, 15, 30, 45]):02d}",
        "type": fake.random_element(["squats", "bench_press", "deadlift", "pull_ups", "push_ups", "lunges"]),
        "sets": str(fake.random_int(min=1, max=10)),
        "repetitions": str(fake.random_int(min=5, max=20)),
        "weight": str(fake.random_int(min=20, max=150)),
        "body_type": fake.random_element(["legs", "chest", "back", "shoulders", "arms", "core"]),
        "injuries": fake.random_element(["yes", "no"]),
        "pain": pain,
        "pain_source": pain_source,
        "rating": str(fake.random_int(min=1, max=10)),
        "session_notes": fake.sentence(),
    }


@pytest.fixture(scope="function")
async def sample_training(async_session, sample_training_data) -> Training:
    """Create a sample training in the database."""
    from datetime import datetime

    # Parse date and time
    training_date = datetime.strptime(sample_training_data["date"], "%d.%m.%Y").date()
    training_time = datetime.strptime(sample_training_data["time"], "%H:%M").time()

    training = Training(
        user_name=sample_training_data["user_name"],
        time_spent_minutes=sample_training_data["time_spend_minutes"],
        training_date=training_date,
        training_time=training_time,
        type=sample_training_data["type"],
        sets=int(sample_training_data["sets"]),
        repetitions=int(sample_training_data["repetitions"]),
        weight=float(sample_training_data["weight"]) if sample_training_data["weight"] else None,
        body_type=sample_training_data["body_type"],
        injuries=sample_training_data["injuries"],
        pain=sample_training_data["pain"],
        pain_source=sample_training_data["pain_source"],
        rating=int(sample_training_data["rating"]) if sample_training_data["rating"] else None,
        session_notes=sample_training_data["session_notes"],
        status="planned",
    )
    async_session.add(training)
    await async_session.commit()
    await async_session.refresh(training)
    return training


@pytest.fixture(scope="function")
async def multiple_trainings(async_session) -> list[Training]:
    """Create multiple sample trainings."""
    trainings = []
    body_types = ["legs", "chest", "back", "shoulders", "arms", "core"]
    types = ["squats", "bench_press", "deadlift", "pull_ups", "push_ups", "lunges"]
    statuses = ["planned", "done", "skipped"]

    for i in range(5):
        training = Training(
            user_name=fake.name(),
            time_spent_minutes=fake.random_int(min=10, max=120),
            training_date=fake.date_between(start_date="-30d", end_date="+30d"),
            training_time=fake.time_object(),
            type=fake.random_element(types),
            sets=fake.random_int(min=1, max=10),
            repetitions=fake.random_int(min=5, max=20),
            weight=float(fake.random_int(min=20, max=150)),
            body_type=fake.random_element(body_types),
            injuries=fake.random_element(["yes", "no"]),
            pain=fake.random_element(["yes", "no"]),
            pain_source=fake.random_element(["knees", "lower_back", "shoulders", "wrists", None]),
            rating=fake.random_int(min=1, max=10),
            session_notes=fake.sentence() if i % 2 == 0 else None,
            status=fake.random_element(statuses),
        )
        async_session.add(training)
        trainings.append(training)
    await async_session.commit()
    for t in trainings:
        await async_session.refresh(t)
    return trainings


# Custom pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "webhook: Webhook endpoint tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "training: Training endpoint tests")