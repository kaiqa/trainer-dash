"""Tests for training webhook endpoint."""
import pytest
from httpx import AsyncClient
from datetime import datetime, date, time


def training_data_to_json(data: dict) -> dict:
    """Convert training data dict to JSON-serializable format."""
    return data.copy()


class TestTrainingWebhookEndpoint:
    """Tests for POST /webhook/record-training endpoint."""

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_valid_training_request(self, async_client: AsyncClient, sample_training_data):
        """Test receiving a valid training request in Dogbrah format."""
        response = await async_client.post(
            "/webhook/record-training",
            json=training_data_to_json(sample_training_data),
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == sample_training_data["user_name"]
        assert data["time_spent_minutes"] == sample_training_data["time_spend_minutes"]
        assert data["type"] == sample_training_data["type"]
        assert data["sets"] == int(sample_training_data["sets"])
        assert data["repetitions"] == int(sample_training_data["repetitions"])
        assert data["weight"] == float(sample_training_data["weight"])
        assert data["body_type"] == sample_training_data["body_type"]
        assert data["injuries"] == sample_training_data["injuries"]
        assert data["pain"] == sample_training_data["pain"]
        assert data["pain_source"] == sample_training_data["pain_source"]
        assert data["rating"] == int(sample_training_data["rating"])
        assert data["session_notes"] == sample_training_data["session_notes"]
        assert data["status"] == "planned"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        # Check date and time parsing
        expected_date = datetime.strptime(sample_training_data["date"], "%d.%m.%Y").date()
        expected_time = datetime.strptime(sample_training_data["time"], "%H:%M").time()
        assert data["training_date"] == expected_date.isoformat()
        assert data["training_time"] == expected_time.isoformat()

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_minimal_training_request(self, async_client: AsyncClient):
        """Test receiving a minimal training request."""
        minimal_data = {
            "user_name": "John Doe",
            "time_spend_minutes": 30,
            "date": "29.09.2026",
            "time": "10:00",
            "type": "squats",
            "sets": "3",
            "repetitions": "12",
            "body_type": "legs",
            "injuries": "no",
            "pain": "no",
        }

        response = await async_client.post(
            "/webhook/record-training",
            json=minimal_data,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_name"] == "John Doe"
        assert data["time_spent_minutes"] == 30
        assert data["type"] == "squats"
        assert data["sets"] == 3
        assert data["repetitions"] == 12
        assert data["body_type"] == "legs"
        assert data["injuries"] == "no"
        assert data["pain"] == "no"
        assert data["weight"] is None
        assert data["pain_source"] is None
        assert data["rating"] is None
        assert data["session_notes"] is None

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_receive_training_with_pain_and_source(self, async_client: AsyncClient):
        """Test receiving training with pain and pain source."""
        data = {
            "user_name": "Jane Smith",
            "time_spend_minutes": 45,
            "date": "29.09.2026",
            "time": "10:00",
            "type": "deadlift",
            "sets": "4",
            "repetitions": "8",
            "weight": "100",
            "body_type": "back",
            "injuries": "no",
            "pain": "yes",
            "pain_source": "lower_back",
            "rating": "8",
        }

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["pain"] == "yes"
        assert result["pain_source"] == "lower_back"
        assert result["rating"] == 8

    # --- Validation Tests ---

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_date_format(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with invalid date format."""
        data = training_data_to_json(sample_training_data)
        data["date"] = "2026-09-29"  # Wrong format

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_time_format(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with invalid time format."""
        data = training_data_to_json(sample_training_data)
        data["time"] = "10:00:00"  # Wrong format

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_missing_required_fields(self, async_client: AsyncClient):
        """Test rejecting request with missing required fields."""
        incomplete_data = {
            "user_name": "John Doe",
            # Missing required fields
        }

        response = await async_client.post(
            "/webhook/record-training",
            json=incomplete_data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_empty_user_name(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with empty user name."""
        data = training_data_to_json(sample_training_data)
        data["user_name"] = ""

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_injuries_value(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with invalid injuries value."""
        data = training_data_to_json(sample_training_data)
        data["injuries"] = "maybe"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_pain_value(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with invalid pain value."""
        data = training_data_to_json(sample_training_data)
        data["pain"] = "maybe"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_pain_yes_without_source(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with pain='yes' but no pain_source."""
        data = training_data_to_json(sample_training_data)
        data["pain"] = "yes"
        data["pain_source"] = None

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_sets_format(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with non-integer sets."""
        data = training_data_to_json(sample_training_data)
        data["sets"] = "not-a-number"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_repetitions_format(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with non-integer repetitions."""
        data = training_data_to_json(sample_training_data)
        data["repetitions"] = "not-a-number"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_weight_format(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with non-numeric weight."""
        data = training_data_to_json(sample_training_data)
        data["weight"] = "not-a-number"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_invalid_rating_format(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with non-integer rating."""
        data = training_data_to_json(sample_training_data)
        data["rating"] = "not-a-number"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_rating_out_of_range(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with rating out of 1-10 range."""
        data = training_data_to_json(sample_training_data)
        data["rating"] = "15"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_reject_rating_below_minimum(self, async_client: AsyncClient, sample_training_data):
        """Test rejecting request with rating below 1."""
        data = training_data_to_json(sample_training_data)
        data["rating"] = "0"

        response = await async_client.post(
            "/webhook/record-training",
            json=data,
        )

        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_multiple_requests_create_separate_records(
        self, async_client: AsyncClient, sample_training_data
    ):
        """Test that multiple requests create separate records."""
        # First request
        response1 = await async_client.post(
            "/webhook/record-training",
            json=training_data_to_json(sample_training_data),
        )
        assert response1.status_code == 201
        id1 = response1.json()["id"]

        # Second request with different user_name
        data = training_data_to_json(sample_training_data)
        data["user_name"] = "Jane Smith"

        response2 = await async_client.post(
            "/webhook/record-training",
            json=data,
        )
        assert response2.status_code == 201
        id2 = response2.json()["id"]

        assert id1 != id2

    @pytest.mark.training
    @pytest.mark.webhook
    @pytest.mark.asyncio
    async def test_webhook_health_check(self, async_client: AsyncClient):
        """Test webhook health check endpoint."""
        response = await async_client.get("/webhook/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "webhook"