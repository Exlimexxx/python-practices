"""Тесты бизнес-логики (service): транзакции и кэш рекомендаций."""
from __future__ import annotations

import pytest

from db import fetch_one
from repository import EntityNotFoundError, ScreeningRepository
from service import RECOMMENDATIONS_KEY, CinemaService, SeatUnavailableError


def test_sell_ticket_commits(conn, service: CinemaService) -> None:
    screenings = ScreeningRepository(conn)
    before = screenings.get(5).tickets_sold

    sale = service.sell_ticket(5, tickets=2)

    assert sale.tickets == 2
    assert sale.total_price == pytest.approx(screening_price(conn, 5) * 2, rel=1e-6)
    assert screenings.get(5).tickets_sold == before + 2
    sales = fetch_one(conn, "SELECT COUNT(*) AS cnt FROM ticket_sales WHERE screening_id = ?", (5,))
    assert sales["cnt"] == 1


def test_sell_ticket_rollback_when_not_enough_seats(conn, service: CinemaService) -> None:
    screenings = ScreeningRepository(conn)
    sold_before = screenings.get(5).tickets_sold
    sales_before = fetch_one(conn, "SELECT COUNT(*) AS cnt FROM ticket_sales")["cnt"]

    with pytest.raises(SeatUnavailableError):
        service.sell_ticket(5, tickets=10_000)

    # ROLLBACK: ни счётчик, ни таблица продаж не изменились.
    assert screenings.get(5).tickets_sold == sold_before
    assert fetch_one(conn, "SELECT COUNT(*) AS cnt FROM ticket_sales")["cnt"] == sales_before


def test_sell_ticket_rejects_non_positive_count(conn, service: CinemaService) -> None:
    with pytest.raises(ValueError):
        service.sell_ticket(5, tickets=0)


def test_sell_ticket_unknown_screening(conn, service: CinemaService) -> None:
    with pytest.raises(EntityNotFoundError):
        service.sell_ticket(99999, tickets=1)


def test_recommendations_cache_miss_then_hit(conn, cache, service: CinemaService) -> None:
    key = RECOMMENDATIONS_KEY.format(movie_id=1)
    assert cache.get(key) is None  # промах

    first = service.recommendations(1)
    assert len(first) >= 5
    assert all(item.id != 1 for item in first)
    assert cache.get(key) is not None  # данные положены в кэш
    assert cache.get("stats:cache_misses") == "1"

    second = service.recommendations(1)
    assert [item.id for item in second] == [item.id for item in first]
    assert cache.get("stats:cache_hits") == "1"  # попадание


def test_recommendations_are_json_serializable_with_cyrillic(conn, cache, service: CinemaService) -> None:
    service.recommendations(1)
    payload = cache.get(RECOMMENDATIONS_KEY.format(movie_id=1))
    assert payload is not None
    assert "Начало" not in payload  # сам фильм в рекомендации не попадает
    assert "Тёмный рыцарь" in payload  # кириллица не экранируется (ensure_ascii=False)


def test_cache_invalidation(conn, cache, service: CinemaService) -> None:
    service.recommendations(1)
    key = RECOMMENDATIONS_KEY.format(movie_id=1)
    assert cache.get(key) is not None
    assert service.invalidate_recommendations(1) is True
    assert cache.get(key) is None
    assert service.invalidate_recommendations(1) is False


def test_cache_ttl_expires(cache) -> None:
    cache.set("k", "v", ttl=1)
    assert cache.get("k") == "v"
    assert cache.ttl("k") in (0, 1)
    import time
    time.sleep(1.2)
    assert cache.get("k") is None
    assert cache.ttl("k") == -2


def test_incr_and_expire(cache) -> None:
    assert cache.incr("counter") == 1
    assert cache.incr("counter", 5) == 6
    cache.set("k", "v")
    assert cache.ttl("k") == -1
    assert cache.expire("k", 30) is True
    assert cache.ttl("k") > 0
    assert cache.delete("k") is True
    assert cache.delete("k") is False


def screening_price(conn, screening_id: int) -> float:
    row = fetch_one(conn, "SELECT price FROM screenings WHERE id = ?", (screening_id,))
    return float(row["price"])
