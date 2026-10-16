from __future__ import annotations
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.storage import HotelStore


class GuestIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=120)
    phone: str = ""


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Guests Service", version="1.0.0")
    store = HotelStore("guests", db_path or os.getenv("GUESTS_DB_PATH", "data/guests.db"))
    app.state.store = store

    @app.get("/health")
    def health(): return {"status": "healthy", "service": "guests"}

    @app.get("/guests")
    def list_guests(): return store.list()

    @app.get("/guests/{guest_id}")
    def get_guest(guest_id: int):
        item = store.get(guest_id)
        if item is None: raise HTTPException(404, "Гость не найден")
        return item

    @app.post("/guests", status_code=201)
    def create_guest(payload: GuestIn):
        try: return store.create(payload.model_dump())
        except sqlite3.IntegrityError as exc: raise HTTPException(409, "Email уже зарегистрирован") from exc

    @app.put("/guests/{guest_id}")
    def update_guest(guest_id: int, payload: GuestIn):
        try: item = store.update(guest_id, payload.model_dump())
        except sqlite3.IntegrityError as exc: raise HTTPException(409, "Email уже зарегистрирован") from exc
        if item is None: raise HTTPException(404, "Гость не найден")
        return item

    @app.delete("/guests/{guest_id}", status_code=204)
    def delete_guest(guest_id: int):
        if not store.delete(guest_id): raise HTTPException(404, "Гость не найден")
        return None

    return app

app = create_app()
