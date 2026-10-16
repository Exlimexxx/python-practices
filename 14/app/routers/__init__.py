"""HTTP-слой приложения (routers)."""
from .movies import router as movies_router

__all__ = ["movies_router"]
