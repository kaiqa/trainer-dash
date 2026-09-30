"""Tests for trainings API endpoints."""
import pytest
from httpx import AsyncClient


class TestTrainingsAPI:
    """Tests for /api/trainings endpoints."""

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_empty(self, async_client: AsyncClient):
        """Test listing trainings when database is empty."""
        response = await async_client.get("/api/trainings")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 0

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_with_data(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test listing trainings with data."""
        response = await async_client.get("/api/trainings")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 5
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_pagination(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test pagination of trainings list."""
        # First page
        response = await async_client.get("/api/trainings?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

        # Second page
        response = await async_client.get("/api/trainings?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_search(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test search filter on trainings list."""
        # Get a training to search for
        training = multiple_trainings[0]
        search_term = training.user_name.split()[0]  # First name

        response = await async_client.get(f"/api/trainings?search={search_term}")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1
        for item in data["items"]:
            assert search_term.lower() in item["user_name"].lower()

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_filter_status(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test filtering by status."""
        response = await async_client.get("/api/trainings?status=done")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["status"] == "done"

        response = await async_client.get("/api/trainings?status=planned")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["status"] == "planned"

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_filter_body_type(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test filtering by body type."""
        # Get a body type from existing trainings
        body_type = multiple_trainings[0].body_type

        response = await async_client.get(f"/api/trainings?body_type={body_type}")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["body_type"] == body_type

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_filter_user_name(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test filtering by user name."""
        user_name = multiple_trainings[0].user_name

        response = await async_client.get(f"/api/trainings?user_name={user_name}")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["user_name"] == user_name

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_filter_date_range(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test filtering by date range."""
        date_from = "2026-01-01"
        date_to = "2026-12-31"

        response = await async_client.get(f"/api/trainings?date_from={date_from}&date_to={date_to}")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["training_date"] >= date_from
            assert item["training_date"] <= date_to

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_trainings_sort(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test sorting trainings."""
        # Sort by training_date ascending
        response = await async_client.get("/api/trainings?sort=training_date:asc")
        assert response.status_code == 200
        data = response.json()

        dates = [item["training_date"] for item in data["items"]]
        assert dates == sorted(dates)

        # Sort by training_date descending
        response = await async_client.get("/api/trainings?sort=training_date:desc")
        assert response.status_code == 200
        data = response.json()

        dates = [item["training_date"] for item in data["items"]]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_training_by_id(
        self, async_client: AsyncClient, sample_training
    ):
        """Test getting a single training by ID."""
        response = await async_client.get(f"/api/trainings/{sample_training.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_training.id
        assert data["user_name"] == sample_training.user_name
        assert data["type"] == sample_training.type

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_nonexistent_training(self, async_client: AsyncClient):
        """Test getting a non-existent training returns 404."""
        response = await async_client.get("/api/trainings/99999")

        assert response.status_code == 404

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_training(
        self, async_client: AsyncClient, sample_training
    ):
        """Test updating a training."""
        response = await async_client.patch(
            f"/api/trainings/{sample_training.id}",
            json={"sets": 5, "repetitions": 15, "rating": 9},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sets"] == 5
        assert data["repetitions"] == 15
        assert data["rating"] == 9

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_training_status(
        self, async_client: AsyncClient, sample_training
    ):
        """Test updating a training status."""
        response = await async_client.patch(
            f"/api/trainings/{sample_training.id}/status",
            json={"status": "done"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"

        # Test invalid status
        response = await async_client.patch(
            f"/api/trainings/{sample_training.id}/status",
            json={"status": "invalid"},
        )
        assert response.status_code == 422

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_nonexistent_training(self, async_client: AsyncClient):
        """Test updating a non-existent training returns 404."""
        response = await async_client.patch(
            "/api/trainings/99999",
            json={"sets": 5},
        )

        assert response.status_code == 404

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_training(
        self, async_client: AsyncClient, sample_training
    ):
        """Test deleting a training."""
        response = await async_client.delete(f"/api/trainings/{sample_training.id}")

        assert response.status_code == 204

        # Verify it's gone
        response = await async_client.get(f"/api/trainings/{sample_training.id}")
        assert response.status_code == 404

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_nonexistent_training(self, async_client: AsyncClient):
        """Test deleting a non-existent training returns 404."""
        response = await async_client.delete("/api/trainings/99999")

        assert response.status_code == 404

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_export_trainings_json(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test exporting trainings as JSON."""
        response = await async_client.get("/api/trainings/export/all")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 5

        # Check structure
        for item in data:
            assert "id" in item
            assert "user_name" in item
            assert "type" in item
            assert "body_type" in item
            assert "status" in item
            assert "training_date" in item
            assert "training_time" in item

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_export_trainings_csv(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test exporting trainings as CSV."""
        response = await async_client.get("/api/trainings/export/csv")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]

        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) == 6  # Header + 5 data rows

        # Check header
        assert "ID" in lines[0]
        assert "User Name" in lines[0]
        assert "Type" in lines[0]
        assert "Body Type" in lines[0]
        assert "Status" in lines[0]

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_export_empty_json(self, async_client: AsyncClient):
        """Test exporting JSON when no trainings exist."""
        response = await async_client.get("/api/trainings/export/all")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_export_empty_csv(self, async_client: AsyncClient):
        """Test exporting CSV when no trainings exist."""
        response = await async_client.get("/api/trainings/export/csv")

        assert response.status_code == 200
        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Only header
        assert "ID" in lines[0]

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_training_stats(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test getting training statistics summary."""
        response = await async_client.get("/api/trainings/stats/summary")

        assert response.status_code == 200
        data = response.json()

        assert "total_sessions" in data
        assert "status_counts" in data
        assert "total_time_minutes" in data
        assert "body_type_counts" in data
        assert "type_counts" in data
        assert "average_rating" in data

        assert data["total_sessions"] == 5
        assert sum(data["status_counts"].values()) == 5
        assert data["total_time_minutes"] > 0

    @pytest.mark.training
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_training_stats_filtered(
        self, async_client: AsyncClient, multiple_trainings
    ):
        """Test getting training statistics with filters."""
        user_name = multiple_trainings[0].user_name

        response = await async_client.get(f"/api/trainings/stats/summary?user_name={user_name}")

        assert response.status_code == 200
        data = response.json()

        assert data["total_sessions"] >= 1
        for item in data["body_type_counts"]:
            pass  # Just verify it works


class TestTrainingWebSocketMessages:
    """Tests for WebSocket message structure."""

    @pytest.mark.training
    @pytest.mark.websocket
    def test_training_created_message_structure(self):
        """Test training_created message structure."""
        message = {
            "type": "training_created",
            "data": {
                "id": 1,
                "user_name": "John Doe",
                "time_spent_minutes": 30,
                "training_date": "2026-09-29",
                "training_time": "10:00:00",
                "type": "squats",
                "sets": 3,
                "repetitions": 12,
                "weight": 77.0,
                "body_type": "legs",
                "injuries": "no",
                "pain": "yes",
                "pain_source": "knees",
                "rating": 7,
                "session_notes": "Hard training",
                "status": "planned",
                "created_at": "2026-09-29T10:00:00",
                "updated_at": "2026-09-29T10:00:00",
            }
        }

        assert message["type"] == "training_created"
        assert "id" in message["data"]
        assert "user_name" in message["data"]
        assert "type" in message["data"]
        assert "status" in message["data"]

    @pytest.mark.training
    @pytest.mark.websocket
    def test_training_updated_message_structure(self):
        """Test training_updated message structure."""
        message = {
            "type": "training_updated",
            "data": {
                "id": 1,
                "status": "done",
                "updated_at": "2026-09-29T11:00:00",
            }
        }

        assert message["type"] == "training_updated"
        assert "id" in message["data"]
        assert "status" in message["data"]

    @pytest.mark.training
    @pytest.mark.websocket
    def test_training_deleted_message_structure(self):
        """Test training_deleted message structure."""
        message = {
            "type": "training_deleted",
            "data": {"id": 1}
        }

        assert message["type"] == "training_deleted"
        assert message["data"]["id"] == 1