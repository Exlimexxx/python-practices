from __future__ import annotations
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.storage import HotelStore


class RoomIn(BaseModel):
    number: str = Field(min_length=1, max_length=12)
    category: str = Field(min_length=1, max_length=40)
    capacity: int = Field(ge=1, le=12)
    price_per_night: float = Field(ge=0)
    active: bool = True


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Rooms Service", version="1.0.0")
    store = HotelStore("rooms", db_path or os.getenv("ROOMS_DB_PATH", "data/rooms.db"))
    app.state.store = store

    @app.get("/health")
    def health(): return {"status": "healthy", "service": "rooms"}

    @app.get("/rooms")
    def list_rooms(): return store.list()

    @app.get("/rooms/{room_id}")
    def get_room(room_id: int):
        item = store.get(room_id)
        if item is None: raise HTTPException(404, "Номер не найден")
        return item

    @app.post("/rooms", status_code=201)
    def create_room(payload: RoomIn):
        try: return store.create(payload.model_dump())
        except sqlite3.IntegrityError as exc: raise HTTPException(409, "Номер уже существует") from exc

    @app.put("/rooms/{room_id}")
    def update_room(room_id: int, payload: RoomIn):
        try: item = store.update(room_id, payload.model_dump())
        except sqlite3.IntegrityError as exc: raise HTTPException(409, "Конфликт номера") from exc
        if item is None: raise HTTPException(404, "Номер не найден")
        return item

    @app.delete("/rooms/{room_id}", status_code=204)
    def delete_room(room_id: int):
        if not store.delete(room_id): raise HTTPException(404, "Номер не найден")
        return None

    return app

app = create_app()
