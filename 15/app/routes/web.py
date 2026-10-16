"""HTML-маршруты (серверный рендеринг Jinja2) — Blueprint web."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.dependencies import get_services
from app.exceptions import HotelError
from app.models import BOOKING_STATUSES, ROOM_TYPES, STATUS_LABELS, Booking, Guest, Room

logger = logging.getLogger(__name__)

web = Blueprint("web", __name__)

#: Допустимые поля сортировки списков (защита от произвольных значений).
ROOM_SORT_FIELDS = ("number", "price", "capacity", "floor")
GUEST_SORT_FIELDS = ("name", "email", "city")
BOOKING_SORT_FIELDS = ("check_in", "check_out", "price")


def _arg(name: str, default: str = "") -> str:
    """Безопасно читает строковый query-параметр."""
    return (request.args.get(name) or default).strip()


def _bool_arg(name: str) -> bool | None:
    """Читает трёхзначный фильтр: пусто / 1 / 0."""
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    return raw in {"1", "true", "on", "yes"}


def _int_arg(name: str) -> int | None:
    """Читает необязательный целочисленный параметр."""
    raw = request.args.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _date_arg(name: str) -> date | None:
    """Читает необязательную дату в формате ISO."""
    raw = request.args.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw.strip()[:10])
    except ValueError:
        return None


@web.route("/")
def index() -> str:
    """Главная страница со сводкой и последними бронированиями."""
    services = get_services()
    stats = services.bookings.statistics()
    recent = services.bookings.list(sort="id", order="desc")[:5]
    return render_template("index.html", stats=stats, recent=recent, active="index")


# --------------------------- Номера (Rooms) ---------------------------


@web.route("/rooms")
def room_list() -> str:
    """Список номеров: поиск, два фильтра и две сортировки."""
    services = get_services()
    search = _arg("search")
    room_type = _arg("room_type")
    is_active = _bool_arg("is_active")
    min_capacity = _int_arg("min_capacity")
    sort = _arg("sort", "number") or "number"
    order = _arg("order", "asc") or "asc"
    if sort not in ROOM_SORT_FIELDS:
        sort = "number"
    rooms = services.rooms.list(
        search=search or None,
        room_type=room_type or None,
        is_active=is_active,
        min_capacity=min_capacity,
        sort=sort,
        order=order,
    )
    logger.info("HTML: список номеров (%s записей)", len(rooms))
    return render_template(
        "rooms/list.html",
        rooms=rooms,
        room_types=ROOM_TYPES,
        filters={"search": search, "room_type": room_type, "is_active": request.args.get("is_active", ""),
                 "min_capacity": request.args.get("min_capacity", ""), "sort": sort, "order": order},
        active="rooms",
    )


@web.route("/rooms/create", methods=["GET", "POST"])
def room_create() -> str:
    """Форма создания номера."""
    services = get_services()
    if request.method == "POST":
        try:
            room = services.rooms.create(request.form.to_dict())
        except HotelError as exc:
            flash(exc.message, "error")
            return render_template("rooms/form.html", room=None, form=request.form,
                                   room_types=ROOM_TYPES, active="rooms"), exc.status_code
        flash(f"Номер «{room.number}» успешно создан", "success")
        return redirect(url_for("web.room_detail", room_id=room.id))
    return render_template("rooms/form.html", room=None, form={}, room_types=ROOM_TYPES, active="rooms")


@web.route("/rooms/<int:room_id>")
def room_detail(room_id: int) -> str:
    """Карточка номера со списком бронирований."""
    services = get_services()
    try:
        room = services.rooms.get(room_id)
    except HotelError:
        abort(404)
    bookings = services.bookings.list(room_id=room_id, sort="check_in", order="desc")
    return render_template("rooms/detail.html", room=room, bookings=bookings, active="rooms")


@web.route("/rooms/<int:room_id>/edit", methods=["GET", "POST"])
def room_edit(room_id: int) -> str:
    """Форма редактирования номера."""
    services = get_services()
    try:
        room = services.rooms.get(room_id)
    except HotelError:
        abort(404)
    if request.method == "POST":
        try:
            updated = services.rooms.update(room_id, request.form.to_dict())
        except HotelError as exc:
            flash(exc.message, "error")
            return render_template("rooms/form.html", room=room, form=request.form,
                                   room_types=ROOM_TYPES, active="rooms"), exc.status_code
        flash(f"Номер «{updated.number}» обновлён", "success")
        return redirect(url_for("web.room_detail", room_id=updated.id))
    return render_template("rooms/form.html", room=room, form=room.to_dict(),
                           room_types=ROOM_TYPES, active="rooms")


@web.route("/rooms/<int:room_id>/delete", methods=["POST"])
def room_delete(room_id: int) -> str:
    """Удаление номера (только POST, с подтверждением на клиенте)."""
    services = get_services()
    try:
        room = services.rooms.get(room_id)
        number = room.number
        services.rooms.delete(room_id)
    except HotelError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.room_list"))
    flash(f"Номер «{number}» удалён", "info")
    return redirect(url_for("web.room_list"))


# --------------------------- Гости (Guests) ---------------------------


@web.route("/guests")
def guest_list() -> str:
    """Список гостей с поиском, фильтром по городу и сортировкой."""
    services = get_services()
    search = _arg("search")
    city = _arg("city")
    has_bookings = _bool_arg("has_bookings")
    sort = _arg("sort", "name") or "name"
    order = _arg("order", "asc") or "asc"
    if sort not in GUEST_SORT_FIELDS:
        sort = "name"
    guests = services.guests.list(
        search=search or None, city=city or None, has_bookings=has_bookings, sort=sort, order=order
    )
    logger.info("HTML: список гостей (%s записей)", len(guests))
    return render_template(
        "guests/list.html",
        guests=guests,
        cities=services.guests.repo.cities(),
        filters={"search": search, "city": city, "has_bookings": request.args.get("has_bookings", ""),
                 "sort": sort, "order": order},
        active="guests",
    )


@web.route("/guests/create", methods=["GET", "POST"])
def guest_create() -> str:
    """Форма создания гостя."""
    services = get_services()
    if request.method == "POST":
        try:
            guest = services.guests.create(request.form.to_dict())
        except HotelError as exc:
            flash(exc.message, "error")
            return render_template("guests/form.html", guest=None, form=request.form,
                                   active="guests"), exc.status_code
        flash(f"Гость «{guest.full_name}» добавлен", "success")
        return redirect(url_for("web.guest_detail", guest_id=guest.id))
    return render_template("guests/form.html", guest=None, form={}, active="guests")


@web.route("/guests/<int:guest_id>")
def guest_detail(guest_id: int) -> str:
    """Карточка гостя с историей бронирований."""
    services = get_services()
    try:
        guest = services.guests.get(guest_id)
    except HotelError:
        abort(404)
    bookings = services.bookings.list(guest_id=guest_id, sort="check_in", order="desc")
    total = round(sum(b.total_price for b in bookings if b.status == "confirmed"), 2)
    return render_template("guests/detail.html", guest=guest, bookings=bookings, total=total,
                           active="guests")


@web.route("/guests/<int:guest_id>/edit", methods=["GET", "POST"])
def guest_edit(guest_id: int) -> str:
    """Форма редактирования гостя."""
    services = get_services()
    try:
        guest = services.guests.get(guest_id)
    except HotelError:
        abort(404)
    if request.method == "POST":
        try:
            updated = services.guests.update(guest_id, request.form.to_dict())
        except HotelError as exc:
            flash(exc.message, "error")
            return render_template("guests/form.html", guest=guest, form=request.form,
                                   active="guests"), exc.status_code
        flash(f"Гость «{updated.full_name}» обновлён", "success")
        return redirect(url_for("web.guest_detail", guest_id=updated.id))
    return render_template("guests/form.html", guest=guest, form=guest.to_dict(), active="guests")


@web.route("/guests/<int:guest_id>/delete", methods=["POST"])
def guest_delete(guest_id: int) -> str:
    """Удаление гостя."""
    services = get_services()
    try:
        guest = services.guests.get(guest_id)
        name = guest.full_name
        services.guests.delete(guest_id)
    except HotelError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.guest_list"))
    flash(f"Гость «{name}» удалён", "info")
    return redirect(url_for("web.guest_list"))


# ----------------------- Бронирования (Bookings) -----------------------


def _booking_form_context(services) -> dict[str, object]:
    """Формирует справочники для формы бронирования."""
    return {
        "rooms": [r for r in services.rooms.list(sort="number") if r.is_active],
        "all_rooms": services.rooms.list(sort="number"),
        "guests": services.guests.list(sort="name"),
        "statuses": STATUS_LABELS,
        "booking_statuses": BOOKING_STATUSES,
    }


@web.route("/bookings")
def booking_list() -> str:
    """Список бронирований с фильтрами по статусу, номеру и датам."""
    services = get_services()
    search = _arg("search")
    status = _arg("status")
    room_id = _int_arg("room_id")
    guest_id = _int_arg("guest_id")
    date_from = _date_arg("date_from")
    date_to = _date_arg("date_to")
    sort = _arg("sort", "check_in") or "check_in"
    order = _arg("order", "desc") or "desc"
    if sort not in BOOKING_SORT_FIELDS:
        sort = "check_in"
    bookings = services.bookings.list(
        search=search or None, status=status or None, room_id=room_id, guest_id=guest_id,
        date_from=date_from, date_to=date_to, sort=sort, order=order,
    )
    logger.info("HTML: список бронирований (%s записей)", len(bookings))
    return render_template(
        "bookings/list.html",
        bookings=bookings,
        rooms=services.rooms.list(sort="number"),
        statuses=STATUS_LABELS,
        filters={"search": search, "status": status, "room_id": request.args.get("room_id", ""),
                 "guest_id": request.args.get("guest_id", ""), "date_from": request.args.get("date_from", ""),
                 "date_to": request.args.get("date_to", ""), "sort": sort, "order": order},
        active="bookings",
    )


@web.route("/bookings/create", methods=["GET", "POST"])
def booking_create() -> str:
    """Форма создания бронирования с проверкой пересечения дат."""
    services = get_services()
    context = _booking_form_context(services)
    if request.method == "POST":
        try:
            booking = services.bookings.create(request.form.to_dict())
        except HotelError as exc:
            flash(exc.message, "error")
            return render_template("bookings/form.html", booking=None, form=request.form,
                                   **context, active="bookings"), exc.status_code
        flash(f"Бронирование №{booking.id} оформлено на сумму {booking.total_price:.2f} ₽", "success")
        return redirect(url_for("web.booking_detail", booking_id=booking.id))
    today = date.today()
    default_form = {
        "check_in": today.isoformat(),
        "check_out": (today + timedelta(days=2)).isoformat(),
        "guests_count": "1",
        "status": "confirmed",
    }
    return render_template("bookings/form.html", booking=None, form=default_form, **context,
                           active="bookings")


@web.route("/bookings/<int:booking_id>")
def booking_detail(booking_id: int) -> str:
    """Карточка бронирования."""
    services = get_services()
    try:
        booking = services.bookings.get(booking_id)
    except HotelError:
        abort(404)
    return render_template("bookings/detail.html", booking=booking, active="bookings")


@web.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
def booking_edit(booking_id: int) -> str:
    """Форма редактирования бронирования."""
    services = get_services()
    try:
        booking = services.bookings.get(booking_id)
    except HotelError:
        abort(404)
    context = _booking_form_context(services)
    if request.method == "POST":
        try:
            updated = services.bookings.update(booking_id, request.form.to_dict())
        except HotelError as exc:
            flash(exc.message, "error")
            return render_template("bookings/form.html", booking=booking, form=request.form,
                                   **context, active="bookings"), exc.status_code
        flash(f"Бронирование №{updated.id} обновлено", "success")
        return redirect(url_for("web.booking_detail", booking_id=updated.id))
    return render_template("bookings/form.html", booking=booking, form=booking.to_dict(),
                           **context, active="bookings")


@web.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
def booking_cancel(booking_id: int) -> str:
    """Отмена бронирования."""
    services = get_services()
    try:
        services.bookings.cancel(booking_id)
    except HotelError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.booking_list"))
    flash(f"Бронирование №{booking_id} отменено", "info")
    return redirect(url_for("web.booking_detail", booking_id=booking_id))


@web.route("/bookings/<int:booking_id>/delete", methods=["POST"])
def booking_delete(booking_id: int) -> str:
    """Удаление бронирования."""
    services = get_services()
    try:
        services.bookings.delete(booking_id)
    except HotelError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.booking_list"))
    flash(f"Бронирование №{booking_id} удалено", "info")
    return redirect(url_for("web.booking_list"))


@web.route("/bookings/new/<int:room_id>")
def booking_new_for_room(room_id: int) -> str:
    """Быстрое бронирование: форма с предвыбранным номером."""
    services = get_services()
    try:
        room = services.rooms.get(room_id)
    except HotelError:
        abort(404)
    context = _booking_form_context(services)
    today = date.today()
    form = {
        "room_id": str(room.id),
        "check_in": today.isoformat(),
        "check_out": (today + timedelta(days=2)).isoformat(),
        "guests_count": "1",
        "status": "confirmed",
    }
    return render_template("bookings/form.html", booking=None, form=form, **context,
                           active="bookings")
