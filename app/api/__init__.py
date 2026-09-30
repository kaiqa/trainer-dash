"""API package."""
from app.api.webhook import router as webhook_router
from app.api.meetings import router as meetings_router
from app.api.settings import router as settings_router
from app.api.training_webhook import router as training_webhook_router
from app.api.trainings import router as trainings_router

__all__ = ["webhook_router", "meetings_router", "settings_router", "training_webhook_router", "trainings_router"]