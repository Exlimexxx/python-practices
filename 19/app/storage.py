"""Изолированные SQLite-хранилища для отдельных сервисов гостиницы."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class HotelStore:
    def __init__(self, kind: str, db_path: str | Path) -> None:
        if kind not in {"rooms", "guests", "bookings"}:
            raise ValueError("Неизвестный тип хранилища")
        self.kind = kind
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        if kind == "rooms":
            self.connection.execute("""CREATE TABLE IF NOT EXISTS rooms(
                id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL, capacity INTEGER NOT NULL CHECK(capacity>0),
                price_per_night REAL NOT NULL CHECK(price_per_night>=0), active INTEGER NOT NULL DEFAULT 1)""")
        elif kind == "guests":
            self.connection.execute("""CREATE TABLE IF NOT EXISTS guests(
                id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE, phone TEXT NOT NULL DEFAULT '')""")
        else:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS bookings(
                id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER NOT NULL,
                guest_id INTEGER NOT NULL, check_in TEXT NOT NULL, check_out TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'confirmed', price_total REAL NOT NULL CHECK(price_total>=0))""")
        self.connection.commit()

    def list(self) -> list[dict[str, Any]]:
        table = self.kind
        return [dict(row) for row in self.connection.execute(f"SELECT * FROM {table} ORDER BY id")]

    def get(self, item_id: int) -> dict[str, Any] | None:
        row = self.connection.execute(f"SELECT * FROM {self.kind} WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        if self.kind == "rooms":
            fields = ("number", "category", "capacity", "price_per_night", "active")
            values = (data["number"], data["category"], data["capacity"], data["price_per_night"], int(data.get("active", True)))
        elif self.kind == "guests":
            fields = ("full_name", "email", "phone")
            values = (data["full_name"], data["email"], data.get("phone", ""))
        else:
            fields = ("room_id", "guest_id", "check_in", "check_out", "status", "price_total")
            values = (data["room_id"], data["guest_id"], data["check_in"], data["check_out"], data.get("status", "confirmed"), data["price_total"])
        placeholders = ",".join("?" for _ in fields)
        cursor = self.connection.execute(
            f"INSERT INTO {self.kind} ({','.join(fields)}) VALUES ({placeholders})", values
        )
        self.connection.commit()
        return self.get(int(cursor.lastrowid))  # type: ignore[return-value]

    def update(self, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        fields = set(data)
        allowed = {
            "rooms": {"number", "category", "capacity", "price_per_night", "active"},
            "guests": {"full_name", "email", "phone"},
            "bookings": {"room_id", "guest_id", "check_in", "check_out", "status", "price_total"},
        }[self.kind]
        if not fields or not fields.issubset(allowed):
            raise ValueError("Некорректные поля для изменения")
        keys = sorted(fields)
        values = [int(data[k]) if k == "active" else data[k] for k in keys]
        cursor = self.connection.execute(
            f"UPDATE {self.kind} SET {','.join(f'{key}=?' for key in keys)} WHERE id=?",
            [*values, item_id],
        )
        self.connection.commit()
        return self.get(item_id) if cursor.rowcount else None

    def delete(self, item_id: int) -> bool:
        cursor = self.connection.execute(f"DELETE FROM {self.kind} WHERE id=?", (item_id,))
        self.connection.commit()
        return cursor.rowcount == 1

    def overlaps(self, room_id: int, check_in: str, check_out: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM bookings WHERE room_id=? AND status='confirmed' "
            "AND check_in < ? AND check_out > ? LIMIT 1",
            (room_id, check_out, check_in),
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self.connection.close()
