# Routers package
from .personas import router as personas_router
from .tasks import router as tasks_router

__all__ = ["personas_router", "tasks_router"]
