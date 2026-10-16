"""Сервисный слой: бизнес-операции кинотеатра с собственными исключениями."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction

from .exceptions import (
    CinemaError,
    SeatAlreadyTakenError,
    SeatOutOfHallError,
)
from .models import Session, Ticket

logger = logging.getLogger(__name__)


@transaction.atomic
def book_ticket(
    session: Session,
    row: int,
    seat: int,
    buyer_name: str,
    price: Decimal | None = None,
) -> Ticket:
    """Продать билет на сеанс с проверкой границ зала и занятости места.

    Операция выполняется в транзакции; при ошибке изменения откатываются.
    """
    hall = session.hall
    if not (1 <= row <= hall.rows) or not (1 <= seat <= hall.seats_per_row):
        logger.warning(
            "Отказ в продаже: место вне зала (сеанс #%s, ряд %s, место %s)",
            session.pk,
            row,
            seat,
        )
        raise SeatOutOfHallError(row, seat, hall.rows, hall.seats_per_row)

    if Ticket.objects.filter(session=session, row=row, seat=seat).exists():
        logger.warning(
            "Отказ в продаже: место занято (сеанс #%s, ряд %s, место %s)",
            session.pk,
            row,
            seat,
        )
        raise SeatAlreadyTakenError(row, seat, session.pk)

    ticket = Ticket.objects.create(
        session=session,
        row=row,
        seat=seat,
        buyer_name=buyer_name,
        price=price if price is not None else session.price,
    )
    logger.info(
        "Продан билет #%s на сеанс #%s (ряд %s, место %s)",
        ticket.pk,
        session.pk,
        row,
        seat,
    )
    return ticket


def safe_book_ticket(session: Session, row: int, seat: int, buyer_name: str) -> str:
    """Обёртка, демонстрирующая перехват собственных исключений."""
    try:
        ticket = book_ticket(session, row, seat, buyer_name)
    except CinemaError as exc:
        return f"ОШИБКА: {exc}"
    return f"OK: билет #{ticket.pk} на {ticket.session.movie.title}"
