"""REST API (JSON) — Blueprint api.

Ресурсы: /api/rooms, /api/guests, /api/bookings. Все ответы — JSON,
HTTP-коды соответствуют результату операции.
"""
from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, jsonify, request

from app.dependencies import get_services
from app.exceptions import HotelError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__, url_prefix="/api")


def _body(default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Читает JSON-тело запроса и проверяет, что это объект."""
    data = request.get_json(silent=True)
    if data is None:
        if request.data:
            raise ValidationError("Тело запроса должно быть корректным JSON-объектом")
        return default or {}
    if not isinstance(data, dict):
        raise ValidationError("JSON верхнего уровня должен быть объектом")
    return data


def _query_filters() -> dict[str, Any]:
    """Собирает общие query-параметры поиска/сортировки."""
    def _int(name: str) -> int | None:
        raw = request.args.get(name)
        if raw is None or not raw.strip():
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _bool(name: str) -> bool | None:
        raw = request.args.get(name)
        if raw is None or raw == "":
            return None
        return raw.lower() in {"1", "true", "on", "yes"}

    return {
        "search": request.args.get("search") or None,
        "sort": (request.args.get("sort") or "").strip() or None,
        "order": (request.args.get("order") or "asc").strip(),
        "_int": _int,
        "_bool": _bool,
    }


# ------------------------------ Служебное ------------------------------


@api.get("")
@api.get("/")
def api_index() -> Any:
    """Корневое описание API."""
    return jsonify(
        {
            "service": "Hotel Booking API (вариант 4 «Отель»)",
            "version": "1.0",
            "resources": {
                "rooms": "/api/rooms",
                "guests": "/api/guests",
                "bookings": "/api/bookings",
                "availability": "/api/rooms/<id>/availability?check_in=&check_out=",
            },
        }
    )


# ------------------------------- Номера -------------------------------


@api.get("/rooms")
def rooms_list() -> Any:
    """GET /api/rooms — список номеров с поиском, фильтрами и сортировкой."""
    services = get_services()
    f = _query_filters()
    rooms = services.rooms.list(
        search=f["search"],
        room_type=request.args.get("room_type") or None,
        is_active=f["_bool"]("is_active"),
        min_capacity=f["_int"]("min_capacity"),
        sort=f["sort"] or "number",
        order=f["order"],
    )
    return jsonify({"count": len(rooms), "items": [r.to_dict() for r in rooms]})


@api.get("/rooms/<int:room_id>")
def rooms_get(room_id: int) -> Any:
    """GET /api/rooms/<id>."""
    services = get_services()
    room = services.rooms.get(room_id)
    data = room.to_dict()
    data["bookings"] = [b.to_dict(with_relations=False) for b in
                        services.bookings.list(room_id=room_id, sort="check_in", order="desc")]
    return jsonify(data)


@api.post("/rooms")
def rooms_create() -> Any:
    """POST /api/rooms — создание номера (201 Created)."""
    services = get_services()
    room = services.rooms.create(_body())
    logger.info("API: создан номер id=%s", room.id)
    return jsonify(room.to_dict()), 201


@api.put("/rooms/<int:room_id>")
@api.patch("/rooms/<int:room_id>")
def rooms_update(room_id: int) -> Any:
    """PUT/PATCH /api/rooms/<id> — обновление номера."""
    services = get_services()
    room = services.rooms.update(room_id, _body())
    return jsonify(room.to_dict())


@api.delete("/rooms/<int:room_id>")
def rooms_delete(room_id: int) -> Any:
    """DELETE /api/rooms/<id> — удаление номера (204 No Content)."""
    services = get_services()
    services.rooms.delete(room_id)
    return ("", 204)


@api.get("/rooms/<int:room_id>/availability")
def rooms_availability(room_id: int) -> Any:
    """GET /api/rooms/<id>/availability — проверка доступности на даты."""
    from datetime import date as _date

    services = get_services()
    room = services.rooms.get(room_id)
    try:
        check_in = _date.fromisoformat((request.args.get("check_in") or "")[:10])
        check_out = _date.fromisoformat((request.args.get("check_out") or "")[:10])
    except ValueError as exc:
        raise ValidationError("Параметры check_in и check_out обязательны (ГГГГ-ММ-ДД)") from exc
    if check_out <= check_in:
        raise ValidationError("check_out должен быть позже check_in")
    available, conflicts = services.bookings.availability(room_id, check_in, check_out)
    return jsonify(
        {
            "room_id": room.id,
            "room_number": room.number,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": (check_out - check_in).days,
            "available": available,
            "estimated_price": services.bookings.calculate_price(room, check_in, check_out),
            "conflicts": conflicts,
        }
    )


# ------------------------------- Гости -------------------------------


@api.get("/guests")
def guests_list() -> Any:
    """GET /api/guests — список гостей."""
    services = get_services()
    f = _query_filters()
    guests = services.guests.list(
        search=f["search"],
        city=request.args.get("city") or None,
        has_bookings=f["_bool"]("has_bookings"),
        sort=f["sort"] or "name",
        order=f["order"],
    )
    return jsonify({"count": len(guests), "items": [g.to_dict() for g in guests]})


@api.get("/guests/<int:guest_id>")
def guests_get(guest_id: int) -> Any:
    """GET /api/guests/<id>."""
    services = get_services()
    guest = services.guests.get(guest_id)
    data = guest.to_dict()
    data["bookings"] = [b.to_dict(with_relations=False) for b in
                        services.bookings.list(guest_id=guest_id, sort="check_in", order="desc")]
    return jsonify(data)


@api.post("/guests")
def guests_create() -> Any:
    """POST /api/guests — создание гостя (201 Created)."""
    services = get_services()
    guest = services.guests.create(_body())
    return jsonify(guest.to_dict()), 201


@api.put("/guests/<int:guest_id>")
@api.patch("/guests/<int:guest_id>")
def guests_update(guest_id: int) -> Any:
    """PUT/PATCH /api/guests/<id>."""
    services = get_services()
    guest = services.guests.update(guest_id, _body())
    return jsonify(guest.to_dict())


@api.delete("/guests/<int:guest_id>")
def guests_delete(guest_id: int) -> Any:
    """DELETE /api/guests/<id> (204 No Content)."""
    services = get_services()
    services.guests.delete(guest_id)
    return ("", 204)


# --------------------------- Бронирования ---------------------------


@api.get("/bookings")
def bookings_list() -> Any:
    """GET /api/bookings — список бронирований с фильтрами."""
    from datetime import date as date_type

    services = get_services()
    f = _query_filters()

    def _parse_date(name: str):
        raw = request.args.get(name)
        if not raw:
            return None
        try:
            return date_type.fromisoformat(raw[:10])
        except ValueError:
            return None

    bookings = services.bookings.list(
        search=f["search"],
        room_id=f["_int"]("room_id"),
        guest_id=f["_int"]("guest_id"),
        status=request.args.get("status") or None,
        date_from=_parse_date("date_from"),
        date_to=_parse_date("date_to"),
        sort=f["sort"] or "check_in",
        order=f["order"] if f["order"] in {"asc", "desc"} else "desc",
    )
    return jsonify({"count": len(bookings), "items": [b.to_dict() for b in bookings]})


@api.get("/bookings/<int:booking_id>")
def bookings_get(booking_id: int) -> Any:
    """GET /api/bookings/<id>."""
    services = get_services()
    return jsonify(services.bookings.get(booking_id).to_dict())


@api.post("/bookings")
def bookings_create() -> Any:
    """POST /api/bookings — бронирование.

    При пересечении дат сервис возбуждает BookingConflictError, и
    обработчик ошибок возвращает 409 Conflict.
    """
    services = get_services()
    booking = services.bookings.create(_body())
    return jsonify(booking.to_dict()), 201


@api.put("/bookings/<int:booking_id>")
@api.patch("/bookings/<int:booking_id>")
def bookings_update(booking_id: int) -> Any:
    """PUT/PATCH /api/bookings/<id>."""
    services = get_services()
    booking = services.bookings.update(booking_id, _body())
    return jsonify(booking.to_dict())


@api.post("/bookings/<int:booking_id>/cancel")
def bookings_cancel(booking_id: int) -> Any:
    """POST /api/bookings/<id>/cancel — отмена бронирования."""
    services = get_services()
    return jsonify(services.bookings.cancel(booking_id).to_dict())


@api.delete("/bookings/<int:booking_id>")
def bookings_delete(booking_id: int) -> Any:
    """DELETE /api/bookings/<id> (204 No Content)."""
    services = get_services()
    services.bookings.delete(booking_id)
    return ("", 204)


# ------------------------- Обработка ошибок API -------------------------


@api.errorhandler(HotelError)
def handle_hotel_error(error: HotelError) -> Any:
    """Преобразует доменные исключения в JSON с корректным кодом."""
    logger.warning("API-ошибка %s: %s", type(error).__name__, error.message)
    return jsonify(error.to_dict()), error.status_code


@api.errorhandler(404)
def handle_not_found(error: Any) -> Any:
    """JSON-ответ 404 для неизвестных API-маршрутов."""
    return jsonify({"error": "NotFound", "message": "Ресурс API не найден", "status": 404}), 404


@api.errorhandler(405)
def handle_method_not_allowed(error: Any) -> Any:
    """JSON-ответ 405 (чтобы API не возвращал HTML)."""
    return jsonify({"error": "MethodNotAllowed", "message": "Метод не поддерживается", "status": 405}), 405


@api.errorhandler(500)
def handle_server_error(error: Any) -> Any:
    """JSON-ответ 500 для непредвиденных ошибок."""
    logger.exception("Внутренняя ошибка API: %s", error)
    return jsonify({"error": "InternalServerError", "message": "Внутренняя ошибка сервера",
                    "status": 500}), 500
