"""Демонстрация Redis: 5 типов данных и более 20 команд."""
from __future__ import annotations

import time

from common import make_service, print_backends, setup_logging, title

setup_logging()

COMMANDS = 0


def cmd(redis_command: str, value: object) -> None:
    """Печать одной команды Redis и её результата (как в redis-cli)."""
    global COMMANDS
    COMMANDS += 1
    print(f"> {redis_command}")
    print(f"  {value!r}")


def main() -> None:
    service, info = make_service(reset=True)
    cache = service.cache
    repo = service.repository

    title("4. REDIS: СТРУКТУРЫ ДАННЫХ И КОМАНДЫ")
    print_backends(info)
    print("Подключение:", type(cache.client).__name__)

    # ------------------------------------------------------------- String
    title("4.1. String: SET / GET / EXPIRE / TTL / INCR / DEL")
    cmd('SET city:weather "Москва: +24"', cache.set("city:weather", "Москва: +24"))
    cmd('GET city:weather', cache.get("city:weather"))
    cmd('EXPIRE city:weather 30', cache.expire("city:weather", 30))
    cmd('TTL city:weather', cache.ttl("city:weather"))
    cmd('INCR counter:requests', cache.incr("counter:requests"))
    cmd('INCRBY counter:requests 4', cache.incr("counter:requests", 4))
    cmd('GET counter:requests', cache.get("counter:requests"))
    cmd('EXISTS city:weather counter:requests', cache.exists("city:weather", "counter:requests"))
    time.sleep(1)
    cmd('TTL city:weather (через 1 c)', cache.ttl("city:weather"))
    cmd('DEL city:weather', cache.delete("city:weather"))
    cmd('EXISTS city:weather', cache.exists("city:weather"))

    # --------------------------------------------------------------- Hash
    title("4.2. Hash: HSET / HGET / HGETALL / HDEL")
    movie_id = repo.find({}, limit=1)[0]["_id"]
    meta_key = cache.key("movie", movie_id, "meta")
    cmd('HSET ' + meta_key + ' title="Побег из Шоушенка" year=1994 rating=9.3',
        cache.hset(meta_key, {"title": "Побег из Шоушенка", "year": 1994, "rating": 9.3}))
    cmd('HGET ' + meta_key + ' title', cache.hget(meta_key, "title"))
    cmd('HGETALL ' + meta_key, cache.hgetall(meta_key))
    cmd('HDEL ' + meta_key + ' year', cache.hdel(meta_key, "year"))

    # --------------------------------------------------------------- List
    title("4.3. List: RPUSH / LPUSH / LRANGE / LLEN / LTRIM")
    list_key = cache.key("schedule", "2024-06-01")
    cmd('RPUSH ' + list_key + ' "10:30 Начало"', cache.rpush(list_key, "10:30 Начало"))
    cmd('RPUSH ' + list_key + ' "14:00 Матрица" "18:30 Дюна"', cache.rpush(list_key, "14:00 Матрица", "18:30 Дюна"))
    cmd('LPUSH ' + list_key + ' "08:00 Утренний сеанс"', cache.lpush(list_key, "08:00 Утренний сеанс"))
    cmd('LRANGE ' + list_key + ' 0 -1', cache.lrange(list_key, 0, -1))
    cmd('LLEN ' + list_key, cache.llen(list_key))
    cmd('LTRIM ' + list_key + ' 0 2', cache.ltrim(list_key, 0, 2))
    cmd('LRANGE после LTRIM 0 -1', cache.lrange(list_key, 0, -1))

    # ---------------------------------------------------------------- Set
    title("4.4. Set: SADD / SMEMBERS / SISMEMBER / SREM / SCARD")
    set_key = cache.key("halls", "imax")
    cmd('SADD ' + set_key + ' "IMAX-1" "IMAX-2"', cache.sadd(set_key, "IMAX-1", "IMAX-2"))
    cmd('SADD ' + set_key + ' "IMAX-2" "IMAX-3"', cache.sadd(set_key, "IMAX-2", "IMAX-3"))
    cmd('SMEMBERS ' + set_key, sorted(cache.smembers(set_key)))
    cmd('SISMEMBER ' + set_key + ' "IMAX-1"', cache.sismember(set_key, "IMAX-1"))
    cmd('SREM ' + set_key + ' "IMAX-3"', cache.srem(set_key, "IMAX-3"))
    cmd('SMEMBERS после SREM', sorted(cache.smembers(set_key)))

    # ---------------------------------------------------------- Sorted Set
    title("4.5. Sorted Set: ZADD / ZRANGE / ZREVRANGE / ZSCORE / ZREM")
    z_key = cache.key("rating:demo")
    cmd('ZADD ' + z_key + ' {Начало:8.8, Матрица:8.7, Побег:9.3}',
        cache.zadd(z_key, {"Начало": 8.8, "Матрица": 8.7, "Побег": 9.3}))
    cmd('ZRANGE ' + z_key + ' 0 -1 WITHSCORES', cache.zrange(z_key, 0, -1, withscores=True))
    cmd('ZREVRANGE ' + z_key + ' 0 1 WITHSCORES', cache.zrevrange(z_key, 0, 1, withscores=True))
    cmd('ZSCORE ' + z_key + ' Матрица', cache.zscore(z_key, "Матрица"))
    cmd('ZREM ' + z_key + ' Матрица', cache.zrem(z_key, "Матрица"))

    # ------------------------------------------------- доменное применение
    title("4.6. Применение в предметной области: рейтинг популярных фильмов")
    for movie_id in repo.find({}, sort=[("rating", -1)], limit=3):
        service.cache.zadd(cache.key("rating"), {str(movie_id["_id"]): movie_id["rating"]})
    titles = {str(d["_id"]): d["title"] for d in repo.find({}, projection={"title": 1})}
    cmd('ZREVRANGE cinema:rating 0 -1 WITHSCORES',
        [(titles.get(mid, mid), score) for mid, score in service.top_rated(5)])
    for doc in repo.find({}, limit=4):
        service.get_movie(doc["_id"])  # формирует популярность и историю просмотров
    cmd('ZREVRANGE cinema:popular 0 -1 WITHSCORES',
        [(titles.get(mid, mid), score) for mid, score in service.popular(4)])
    cmd('LRANGE cinema:recent 0 -1',
        [titles.get(mid, mid) for mid in service.recent(4)])

    print(f"\nИТОГО выполнено команд Redis: {COMMANDS}")


if __name__ == "__main__":
    main()
