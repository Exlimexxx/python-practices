"""Pydantic-схемы приложения."""
from .movie import (
    GenreStat,
    MovieCreate,
    MovieListResponse,
    MovieResponse,
    MovieStats,
    MovieUpdate,
)

__all__ = [
    "GenreStat",
    "MovieCreate",
    "MovieListResponse",
    "MovieResponse",
    "MovieStats",
    "MovieUpdate",
]
