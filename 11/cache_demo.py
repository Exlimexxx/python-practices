"""Демонстрация кэш-слоя: промах, попадание, TTL, EXPIRE, INCR, DELETE.

Запуск:  python cache_demo.py [--db cinema.db]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from cache import create_cache
from db import DB_PATH, connect
from repository import MovieRepository
from service import RECOMMENDATIONS_KEY, RECOMMENDATIONS_TTL, CinemaService

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s",
                    stream=sys.stdout)
logger = logging.getLogger("demo.cache")


def main() -> int:
    parser = argparse.ArgumentParser(description="Демонстрация кэширования рекомендаций")
    parser.add_argument("--db", default=str(DB_PATH))
    args = parser.parse_args()

    conn = connect(args.db)
    cache = create_cache()
    service = CinemaService(conn, cache)
    movies = MovieRepository(conn)

    print("=" * 78)
    print("ДЕМОНСТРАЦИЯ КЭШ-СЛОЯ (рекомендации фильмов)")
    print("=" * 78)
    print(f"Реализация кэша : {cache.name}")
    print(f"Ключ            : {RECOMMENDATIONS_KEY.format(movie_id=1)}")
    print(f"TTL по заданию  : {RECOMMENDATIONS_TTL} сек.")
    print()

    movie = movies.get(1)
    print(f"Фильм-источник  : id={movie.id}, «{movie.title}», рейтинг {movie.rating}")

    # ---- Операция 1: GET (промах) + SET -------------------------------
    print()
    print("-" * 78)
    print("1) ПРОМАХ КЭША (cache miss): GET -> None, затем SET с TTL")
    print("-" * 78)
    key = RECOMMENDATIONS_KEY.format(movie_id=movie.id)
    print(f"  GET {key} -> {cache.get(key)!r}")
    t0 = time.perf_counter()
    recs_miss = service.recommendations(movie.id)
    dt_miss = (time.perf_counter() - t0) * 1000
    print(f"  Источник данных: SQLite (кэш пуст), время {dt_miss:.2f} мс")
    for r in recs_miss:
        print(f"    - {r.title} (рейтинг {r.rating})")
    print(f"  SET {key} <JSON, {len(recs_miss)} элементов> EX {RECOMMENDATIONS_TTL}")
    print(f"  TTL ключа после записи: {cache.ttl(key)} сек.")

    # ---- Операция 2: GET (попадание) ----------------------------------
    print()
    print("-" * 78)
    print("2) ПОПАДАНИЕ В КЭШ (cache hit): данные берутся из кэша, SQLite не читается")
    print("-" * 78)
    t0 = time.perf_counter()
    recs_hit = service.recommendations(movie.id)
    dt_hit = (time.perf_counter() - t0) * 1000
    print(f"  GET {key} -> найден, время {dt_hit:.2f} мс "
          f"(в {dt_miss / max(dt_hit, 0.001):.1f} раз быстрее промаха)")
    print(f"  Совпадает с результатом из SQLite: {recs_miss == recs_hit}")

    # ---- Операция 3: INCR ---------------------------------------------
    print()
    print("-" * 78)
    print("3) INCR: счётчики обращений к кэшу")
    print("-" * 78)
    print(f"  INCR stats:cache_misses -> {cache.incr('stats:cache_misses')}")
    print(f"  INCR stats:cache_hits   -> {cache.incr('stats:cache_hits')}")
    print(f"  INCR stats:cache_hits   -> {cache.incr('stats:cache_hits')}")
    print(f"  GET stats:cache_hits    -> {cache.get('stats:cache_hits')}")

    # ---- Операция 4: EXPIRE -------------------------------------------
    print()
    print("-" * 78)
    print("4) EXPIRE: изменение TTL существующего ключа")
    print("-" * 78)
    print(f"  TTL до EXPIRE           : {cache.ttl(key)} сек.")
    print(f"  EXPIRE {key} 2          -> {cache.expire(key, 2)}")
    print(f"  TTL после EXPIRE        : {cache.ttl(key)} сек.")

    # ---- Операция 5: истечение TTL ------------------------------------
    print()
    print("-" * 78)
    print("5) ИСТЕЧЕНИЕ TTL: ждём 3 секунды и наблюдаем повторный промах")
    print("-" * 78)
    time.sleep(3)
    print(f"  GET {key} -> {cache.get(key)!r}  (ключ исчез)")
    print(f"  TTL ключа               : {cache.ttl(key)} (=-2: ключа нет)")
    recs_again = service.recommendations(movie.id)
    print(f"  После истечения TTL снова читаем SQLite и кладём в кэш: "
          f"{len(recs_again)} рекомендаций, TTL={cache.ttl(key)} сек.")

    # ---- Операция 6: DELETE (инвалидация) -----------------------------
    print()
    print("-" * 78)
    print("6) DELETE: инвалидация кэша при изменении данных")
    print("-" * 78)
    print(f"  Ключ есть в кэше перед инвалидацией: {cache.get(key) is not None}")
    print(f"  DELETE через сервис -> {service.invalidate_recommendations(movie.id)} (ключ был в кэше)")
    print(f"  DELETE повторно     -> {service.invalidate_recommendations(movie.id)} (ключа уже нет)")
    cache.set(key, '{"stale": true}', ttl=30)
    print(f"  Ручной SET устаревшего значения, TTL={cache.ttl(key)} сек.")
    print(f"  Ручной DEL {key} -> {cache.delete(key)}")
    print(f"  TTL                 : {cache.ttl(key)} (=-2: ключа нет)")

    print()
    print("=" * 78)
    print("Операции SET, GET, DELETE, EXPIRE, INCR и истечение TTL показаны.")
    print("=" * 78)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
