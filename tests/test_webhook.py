"""Tests for webhook endpoint."""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


def meeting_data_to_json(data: dict) -> dict:
    """Convert meeting data dict to JSON-serializable format."""
    result = data.copy()
    if "meeting_time" in result and isinstance(result["meeting_time"], datetime):
        result["meeting_time"] = result["meeting_time"].isoformat() + "Z"
    return result


def dograh_data_to_json(data: dict) -> dict:
    """Convert Dograh format data to JSON-serializable format."""
    result = data.copy()
    if "meeting_date" in result and isinstance(result["meeting_date"], datetime):
        result["meeting_date"] = result["meeting_date"].isoformat() + "Z"
    return result


class TestWebhookEndpoint:
    """Tests for POST /webhook/req-meeting endpoint."""

    # --- Legacy/n8n Format Tests ---

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_valid_legacy_meeting_request(self, async_client: AsyncClient, sample_meeting_data):
        """Test receiving a valid meeting request in legacy/n8n format."""
        response = await async_client.post(
            "/webhook/req-meeting",
            json=meeting_data_to_json(sample_meeting_data),
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == sample_meeting_data["user_name"]
        assert data["user_email"] == sample_meeting_data["user_email"]
        assert data["company_name"] == sample_meeting_data["company_name"]
        assert data["job_opportunity"] == sample_meeting_data["job_opportunity"]
        assert data["recruiter_name"] == sample_meeting_data["recruiter_name"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_minimal_legacy_meeting_request(self, async_client: AsyncClient):
        """Test receiving a minimal meeting request in legacy format."""
        minimal_data = {
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "meeting_time": "2026-10-15T14:00:00Z",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=minimal_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == "John Doe"
        assert data["user_email"] == "john@example.com"
        assert data["company_name"] is None
        assert data["job_opportunity"] is None
        assert data["recruiter_name"] is None

    # --- Dograh AI Format Tests ---

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_valid_dograh_meeting_request(self, async_client: AsyncClient):
        """Test receiving a valid meeting request in Dograh AI format."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
            "company_name": "Acme Corp",
            "job_opportunity": "Senior Engineer",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == "Jane Smith"
        assert data["user_email"] == "jane@dograh.ai"
        assert data["meeting_time"] == "2026-10-15T14:00:00"
        assert data["company_name"] == "Acme Corp"
        assert data["job_opportunity"] == "Senior Engineer"
        assert data["recruiter_name"] == "Jane Smith"
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_minimal_dograh_meeting_request(self, async_client: AsyncClient):
        """Test receiving a minimal Dograh meeting request."""
        minimal_data = {
            "recruiter_name": "John Doe",
            "contact_email": "john@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=minimal_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == "John Doe"
        assert data["user_email"] == "john@example.com"
        assert data["company_name"] is None
        assert data["job_opportunity"] is None
        assert data["recruiter_name"] == "John Doe"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_dograh_with_job_opportunity(self, async_client: AsyncClient):
        """Test Dograh format correctly stores job_opportunity."""
        dograh_data = {
            "recruiter_name": "Recruiter Name",
            "contact_email": "recruiter@test.com",
            "meeting_date": "2026-10-20T10:00:00Z",
            "company_name": "Test Company",
            "job_opportunity": "Software Developer Position",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["job_opportunity"] == "Software Developer Position"

    # --- Validation Tests (both formats) ---

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_email_legacy(self, async_client: AsyncClient, sample_meeting_data):
        """Test rejecting legacy request with invalid email."""
        data = meeting_data_to_json(sample_meeting_data)
        data["user_email"] = "not-an-email"

        response = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_email_dograh(self, async_client: AsyncClient):
        """Test rejecting Dograh request with invalid email."""
        data = {
            "recruiter_name": "John Doe",
            "contact_email": "not-an-email",
            "meeting_date": "2026-10-15T14:00:00Z",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_missing_required_fields(self, async_client: AsyncClient):
        """Test rejecting request with missing required fields."""
        incomplete_data = {
            "user_name": "John Doe",
            # Missing user_email and meeting_time
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=incomplete_data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_missing_required_fields_dograh(self, async_client: AsyncClient):
        """Test rejecting Dograh request with missing required fields."""
        incomplete_data = {
            "recruiter_name": "John Doe",
            # Missing contact_email and meeting_date
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=incomplete_data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_meeting_time_legacy(self, async_client: AsyncClient, sample_meeting_data):
        """Test rejecting legacy request with invalid meeting time format."""
        data = meeting_data_to_json(sample_meeting_data)
        data["meeting_time"] = "not-a-date"

        response = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_meeting_date_dograh(self, async_client: AsyncClient):
        """Test rejecting Dograh request with invalid meeting date format."""
        data = {
            "recruiter_name": "John Doe",
            "contact_email": "john@example.com",
            "meeting_date": "not-a-date",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_empty_user_name(self, async_client: AsyncClient, sample_meeting_data):
        """Test rejecting request with empty user name."""
        data = meeting_data_to_json(sample_meeting_data)
        data["user_name"] = ""
        data["recruiter_name"] = ""  # Also empty fallback

        response = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_empty_recruiter_name_dograh(self, async_client: AsyncClient):
        """Test rejecting Dograh request with empty recruiter name."""
        data = {
            "recruiter_name": "",
            "contact_email": "john@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_webhook_health_check(self, async_client: AsyncClient):
        """Test webhook health check endpoint."""
        response = await async_client.get("/webhook/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webhook"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_multiple_requests_create_separate_records(
        self, async_client: AsyncClient, sample_meeting_data
    ):
        """Test that multiple requests create separate records."""
        from datetime import timedelta

        # First request
        response1 = await async_client.post(
            "/webhook/req-meeting",
            json=meeting_data_to_json(sample_meeting_data),
        )
        assert response1.status_code == 201
        id1 = response1.json()["id"]

        # Second request with different email AND different meeting time (to avoid duplicate check)
        data = meeting_data_to_json(sample_meeting_data)
        data["user_email"] = "jane@example.com"
        # Add 1 hour to meeting time to avoid duplicate conflict
        original_time = data["meeting_time"]
        if isinstance(original_time, str) and original_time.endswith("Z"):
            from datetime import datetime
            dt = datetime.fromisoformat(original_time.replace("Z", "+00:00"))
            dt = dt + timedelta(hours=1)
            data["meeting_time"] = dt.isoformat().replace("+00:00", "Z")
        response2 = await async_client.post(
            "/webhook/req-meeting",
            json=data,
        )
        assert response2.status_code == 201
        id2 = response2.json()["id"]

        assert id1 != id2

    # --- Duplicate Meeting Date/Time Tests ---

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_duplicate_active_meeting_time(self, async_client: AsyncClient, sample_meeting_data):
        """Test rejecting a meeting request with the same time as an existing active meeting."""
        meeting_time = "2026-10-15T14:00:00Z"
        data1 = meeting_data_to_json(sample_meeting_data)
        data1["meeting_time"] = meeting_time
        data1["user_email"] = "first@example.com"

        # First request - should succeed
        response1 = await async_client.post(
            "/webhook/req-meeting",
            json=data1,
        )
        assert response1.status_code == 201
        first_meeting = response1.json()
        assert first_meeting["is_active"] is True

        # Second request with same meeting_time but different email - should fail
        data2 = meeting_data_to_json(sample_meeting_data)
        data2["meeting_time"] = meeting_time
        data2["user_email"] = "second@example.com"

        response2 = await async_client.post(
            "/webhook/req-meeting",
            json=data2,
        )
        assert response2.status_code == 409
        error_data = response2.json()

        assert error_data["detail"]["error"] == "time_slot_taken"
        assert "overlaps" in error_data["detail"]["message"]
        assert "existing_meeting" in error_data["detail"]
        existing = error_data["detail"]["existing_meeting"]
        assert existing["id"] == first_meeting["id"]
        assert existing["user_email"] == "first@example.com"
        assert existing["meeting_time"] == "2026-10-15T14:00:00"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_allow_same_time_after_deactivated(self, async_client: AsyncClient, sample_meeting_data, async_session):
        """Test allowing a meeting at same time after the previous one is deactivated."""
        from app.models.meeting import Meeting
        from sqlalchemy import select

        meeting_time = "2026-10-15T14:00:00Z"
        data1 = meeting_data_to_json(sample_meeting_data)
        data1["meeting_time"] = meeting_time
        data1["user_email"] = "first@example.com"

        # First request - should succeed
        response1 = await async_client.post(
            "/webhook/req-meeting",
            json=data1,
        )
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Deactivate the first meeting directly in DB
        result = await async_session.execute(select(Meeting).where(Meeting.id == first_meeting["id"]))
        meeting = result.scalar_one()
        meeting.is_active = False
        await async_session.commit()

        # Second request with same meeting_time - should now succeed
        data2 = meeting_data_to_json(sample_meeting_data)
        data2["meeting_time"] = meeting_time
        data2["user_email"] = "second@example.com"

        response2 = await async_client.post(
            "/webhook/req-meeting",
            json=data2,
        )
        assert response2.status_code == 201
        second_meeting = response2.json()
        assert second_meeting["id"] != first_meeting["id"]
        assert second_meeting["user_email"] == "second@example.com"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_duplicate_dograh_format(self, async_client: AsyncClient):
        """Test rejecting duplicate meeting time in Dograh AI format."""
        meeting_time = "2026-10-15T14:00:00Z"
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": meeting_time,
        }

        # First request - should succeed
        response1 = await async_client.post(
            "/webhook/req-meeting",
            json=data1,
        )
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second request in Dograh format with same time - should fail
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": meeting_time,
        }

        response2 = await async_client.post(
            "/webhook/req-meeting",
            json=data2,
        )
        assert response2.status_code == 409
        error_data = response2.json()

        assert error_data["detail"]["error"] == "time_slot_taken"
        existing = error_data["detail"]["existing_meeting"]
        assert existing["id"] == first_meeting["id"]
        assert existing["user_email"] == "first@example.com"

    # --- Meeting Duration Tests ---

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_meeting_with_duration(self, async_client: AsyncClient):
        """Test receiving a meeting request with custom duration."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 60,
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == "Jane Smith"
        assert data["meeting_duration"] == 60

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_default_duration_is_30_minutes(self, async_client: AsyncClient):
        """Test that default meeting duration is 30 minutes when not specified."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["meeting_duration"] == 30

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_duration_below_minimum(self, async_client: AsyncClient):
        """Test rejecting meeting with duration less than 5 minutes."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 3,  # Below minimum of 5
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_duration_above_maximum(self, async_client: AsyncClient):
        """Test rejecting meeting with duration more than 480 minutes (8 hours)."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 500,  # Above maximum of 480
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 422

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_accept_minimum_duration(self, async_client: AsyncClient):
        """Test accepting meeting with minimum duration (5 minutes)."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 5,
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meeting_duration"] == 5

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_accept_maximum_duration(self, async_client: AsyncClient):
        """Test accepting meeting with maximum duration (480 minutes)."""
        dograh_data = {
            "recruiter_name": "Jane Smith",
            "contact_email": "jane@dograh.ai",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 480,
        }

        response = await async_client.post(
            "/webhook/req-meeting",
            json=dograh_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meeting_duration"] == 480

    # --- Overlap Detection Tests ---

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_overlapping_meeting_same_start_time(self, async_client: AsyncClient):
        """Test rejecting meeting that starts at same time as existing (with different durations)."""
        # First meeting: 30 min at 14:00
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 30,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: same start, 60 min - should overlap
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 60,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 409
        error_data = response2.json()
        assert error_data["detail"]["error"] == "time_slot_taken"
        assert "overlaps" in error_data["detail"]["message"]

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_overlapping_meeting_starts_during_existing(self, async_client: AsyncClient):
        """Test rejecting meeting that starts during an existing meeting."""
        # First meeting: 60 min at 14:00 (ends at 15:00)
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 60,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: starts at 14:30 (during first meeting), 30 min
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:30:00Z",
            "meeting_duration": 30,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 409
        error_data = response2.json()
        assert error_data["detail"]["error"] == "time_slot_taken"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_overlapping_meeting_ends_during_existing(self, async_client: AsyncClient):
        """Test rejecting meeting that ends during an existing meeting."""
        # First meeting: 60 min at 14:00 (ends at 15:00)
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 60,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: starts at 13:30, 60 min (ends at 14:30 - during first meeting)
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T13:30:00Z",
            "meeting_duration": 60,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 409
        error_data = response2.json()
        assert error_data["detail"]["error"] == "time_slot_taken"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_overlapping_meeting_encompasses_existing(self, async_client: AsyncClient):
        """Test rejecting meeting that fully encompasses an existing meeting."""
        # First meeting: 30 min at 14:30
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:30:00Z",
            "meeting_duration": 30,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: 60 min at 14:00 (encompasses first meeting)
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 60,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 409
        error_data = response2.json()
        assert error_data["detail"]["error"] == "time_slot_taken"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_allow_adjacent_meetings_no_overlap(self, async_client: AsyncClient):
        """Test allowing meetings that are adjacent (end == start) without overlap."""
        # First meeting: 30 min at 14:00 (ends at 14:30)
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 30,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: starts exactly when first ends (14:30)
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:30:00Z",
            "meeting_duration": 30,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 201
        second_meeting = response2.json()
        assert second_meeting["id"] != first_meeting["id"]

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_allow_meeting_after_existing_ends(self, async_client: AsyncClient):
        """Test allowing meeting that starts after existing meeting ends."""
        # First meeting: 30 min at 14:00 (ends at 14:30)
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 30,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: starts 1 minute after first ends (14:31)
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:31:00Z",
            "meeting_duration": 30,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 201
        second_meeting = response2.json()
        assert second_meeting["id"] != first_meeting["id"]

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_allow_meeting_before_existing_starts(self, async_client: AsyncClient):
        """Test allowing meeting that ends before existing meeting starts."""
        # First meeting: 30 min at 14:30
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:30:00Z",
            "meeting_duration": 30,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: ends 1 minute before first starts (14:29)
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T13:59:00Z",
            "meeting_duration": 30,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 201
        second_meeting = response2.json()
        assert second_meeting["id"] != first_meeting["id"]

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_overlap_error_includes_requested_and_existing_slots(self, async_client: AsyncClient):
        """Test that overlap error response includes detailed slot information."""
        # First meeting: 60 min at 14:00
        data1 = {
            "recruiter_name": "First Recruiter",
            "contact_email": "first@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 60,
        }
        response1 = await async_client.post("/webhook/req-meeting", json=data1)
        assert response1.status_code == 201
        first_meeting = response1.json()

        # Second meeting: overlaps
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:30:00Z",
            "meeting_duration": 30,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 409
        error_data = response2.json()

        detail = error_data["detail"]
        assert detail["error"] == "time_slot_taken"
        assert "requested_slot" in detail
        assert "existing_meeting" in detail

        requested = detail["requested_slot"]
        assert requested["start"] == "2026-10-15T14:30:00"
        assert requested["end"] == "2026-10-15T15:00:00"
        assert requested["duration_minutes"] == 30

        existing = detail["existing_meeting"]
        assert existing["id"] == first_meeting["id"]
        assert existing["meeting_duration"] == 60
        assert existing["meeting_end"] == "2026-10-15T15:00:00"

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_overlap_check_only_considers_active_meetings(self, async_client: AsyncClient, async_session):
        """Test that overlap check ignores inactive meetings."""
        from app.models.meeting import Meeting
        from sqlalchemy import select

        # Create first meeting and deactivate it
        meeting = Meeting(
            user_name="First Recruiter",
            user_email="first@example.com",
            meeting_time=datetime.fromisoformat("2026-10-15T14:00:00"),
            meeting_duration=60,
            is_active=False,
        )
        async_session.add(meeting)
        await async_session.commit()
        await async_session.refresh(meeting)

        # New meeting at same time should succeed since first is inactive
        data2 = {
            "recruiter_name": "Second Recruiter",
            "contact_email": "second@example.com",
            "meeting_date": "2026-10-15T14:00:00Z",
            "meeting_duration": 30,
        }
        response2 = await async_client.post("/webhook/req-meeting", json=data2)
        assert response2.status_code == 201
        second_meeting = response2.json()
        assert second_meeting["id"] != meeting.id

    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_legacy_format_with_duration(self, async_client: AsyncClient):
        """Test legacy format also accepts meeting_duration."""
        data = {
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "meeting_time": "2026-10-15T14:00:00Z",
            "meeting_duration": 45,
        }

        response = await async_client.post("/webhook/req-meeting", json=data)

        assert response.status_code == 201
        result = response.json()
        assert result["meeting_duration"] == 45