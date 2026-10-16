"""Демонстрация паттерна cache-aside: промах, попадание, TTL, инвалидация."""
from __future__ import annotations

import time

from common import make_service, print_backends, setup_logging, title

setup_logging()


def cache_line(service, movie_id) -> str:
    key = service.movie_cache_key(movie_id)
    return f"{key} -> value={'есть' if service.cache.get(key) else 'нет'}, ttl={service.cache.ttl(key)}"


def main() -> None:
    service, info = make_service(reset=True, ttl=60)
    repo = service.repository

    title("5. CACHE-ASIDE: ПРОМАХ, ПОПАДАНИЕ, TTL, ИНВАЛИДАЦИЯ")
    print_backends(info)

    movie_id = repo.find({}, sort=[("rating", -1)], limit=1)[0]["_id"]
    print("Тестовый фильм _id =", movie_id)
    service.clear_cache()

    title("5.1. Первый запрос: промах кэша (CACHE MISS) -> MongoDB -> Redis")
    movie = service.get_movie(movie_id)
    print("Получено из MongoDB:", movie.summary())
    print("Состояние ключа:", cache_line(service, movie_id))

    title("5.2. Второй запрос: попадание в кэш (CACHE HIT), MongoDB не вызывается")
    movie_hit = service.get_movie(movie_id)
    print("Получено из Redis:", movie_hit.summary())
    print("Состояние ключа:", cache_line(service, movie_id))
    print("Статистика обращений:", service.stats)

    title("5.3. TTL: автоматическое истечение ключа")
    demo_key = service.cache.key("demo", "ttl")
    service.cache.set(demo_key, "живёт 2 секунды", ttl=2)
    print(f"SET {demo_key} EX 2 -> значение={service.cache.get(demo_key)!r}, ttl={service.cache.ttl(demo_key)}")
    print("... ожидание 3 секунды ...")
    time.sleep(3)
    print(f"GET {demo_key} -> {service.cache.get(demo_key)!r}, ttl={service.cache.ttl(demo_key)}")
    print("Ключ movie всё ещё жив (TTL 60 c):", cache_line(service, movie_id))

    title("5.4. Инвалидация кэша при изменении объекта (update -> DEL)")
    before = repo.get_document(movie_id)
    print(f"Рейтинг до изменения: {before['rating']}")
    updated = service.update_movie(movie_id, {"rating": 9.9})
    print(f"Рейтинг после изменения: {updated.rating}")
    print("Состояние ключа после update (должно быть 'нет'):", cache_line(service, movie_id))

    title("5.5. Следующий запрос снова идёт в MongoDB (CACHE MISS) и обновляет кэш")
    refreshed = service.get_movie(movie_id)
    print("Получено:", refreshed.summary())
    print("Состояние ключа:", cache_line(service, movie_id))
    print("Статистика обращений:", service.stats)

    title("5.6. Инвалидация при удалении (delete -> DEL + ZREM)")
    service.delete_movie(movie_id)
    print("Документ удалён. Состояние ключа:", cache_line(service, movie_id))
    try:
        service.get_movie(movie_id)
    except Exception as exc:  # наглядно показываем результат
        print(f"Ожидаемая ошибка: {type(exc).__name__}: {exc}")

    title("5.7. Состояние кэша (ключи, типы, TTL)")
    status = service.cache_status()
    print("namespace   :", status["namespace"])
    print("ключей всего:", status["keys_total"])
    print("hits/misses :", status["hits"], "/", status["misses"])
    for entry in status["entries"]:
        print("  -", entry)


if __name__ == "__main__":
    main()
