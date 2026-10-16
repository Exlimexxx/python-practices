"""Сравнение CDN и origin-сервера: заголовки, размер и время ответа.

Скрипт сам поднимает оба сервера в фоновых потоках, выполняет HTTP-запросы
к одному и тому же постеру и печатает подробный отчёт.

Запуск:  python cdn_demo.py
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from cdn_server import CACHE_CONTROL as CDN_CACHE_CONTROL
from cdn_server import STATIC_DIR, create_server as create_cdn
from origin_server import CACHE_CONTROL as ORIGIN_CACHE_CONTROL
from origin_server import create_server as create_origin

CDN_PORT = 8091
ORIGIN_PORT = 8092
CDN_BASE = f"http://127.0.0.1:{CDN_PORT}"
ORIGIN_BASE = f"http://127.0.0.1:{ORIGIN_PORT}"
POSTER = "/posters/poster_1.svg"
ALL_RESOURCES = ("/posters/poster_1.svg", "/posters/poster_2.svg",
                 "/posters/poster_3.svg", "/css/style.css", "/js/app.js")


@dataclass
class Probe:
    """Результат одного HTTP-запроса."""

    label: str
    url: str
    status: int
    headers: dict[str, str]
    size: int
    elapsed_ms: float


def probe(label: str, url: str, if_none_match: str | None = None) -> Probe:
    headers = {"If-None-Match": if_none_match} if if_none_match else {}
    started = time.perf_counter()
    response = requests.get(url, headers=headers, timeout=10)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return Probe(label, url, response.status_code, dict(response.headers),
                 len(response.content), elapsed_ms)


def header(probe_result: Probe, name: str) -> str:
    """Заголовок без учёта регистра (http.server пишет «Content-type»)."""
    target = name.lower()
    for key, value in probe_result.headers.items():
        if key.lower() == target:
            return value
    return "— отсутствует"


def print_probe(result: Probe) -> None:
    print("-" * 78)
    print(result.label)
    print("-" * 78)
    print(f"  URL            : {result.url}")
    print(f"  HTTP-статус    : {result.status}")
    print(f"  Cache-Control  : {header(result, 'Cache-Control')}")
    print(f"  Content-Length : {header(result, 'Content-Length')}")
    print(f"  Content-Type   : {header(result, 'Content-Type')}")
    print(f"  ETag           : {header(result, 'ETag')}")
    print(f"  Age            : {header(result, 'Age')}")
    print(f"  Размер ответа  : {result.size} байт")
    print(f"  Время ответа   : {result.elapsed_ms:.2f} мс")
    print()


def run_server(httpd) -> threading.Thread:
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return thread


def main() -> int:
    cdn_server = create_cdn(CDN_PORT, STATIC_DIR)
    origin_server = create_origin(ORIGIN_PORT, STATIC_DIR)
    run_server(cdn_server)
    run_server(origin_server)
    time.sleep(0.4)  # даём серверам подняться

    print("=" * 78)
    print("СРАВНЕНИЕ CDN И ORIGIN-СЕРВЕРА (статика: постеры, CSS, JS)")
    print("=" * 78)
    print(f"CDN    : {CDN_BASE}   Cache-Control: {CDN_CACHE_CONTROL}")
    print(f"Origin : {ORIGIN_BASE}  Cache-Control: {ORIGIN_CACHE_CONTROL}")
    print(f"Папка статики: {STATIC_DIR}")
    print()

    print("Файлы, раздаваемые CDN:")
    for resource in ALL_RESOURCES:
        file_path = Path(STATIC_DIR) / resource.lstrip("/")
        size = file_path.stat().st_size if file_path.exists() else -1
        print(f"  {resource:28s} {size:6d} байт на диске")
    print()

    try:
        # --- CDN: первый запрос ----------------------------------------
        first = probe("1. CDN — ПЕРВЫЙ запрос постера (кэш узла пуст)", CDN_BASE + POSTER)
        print_probe(first)

        # --- CDN: повторный запрос -------------------------------------
        time.sleep(1.1)  # чтобы заголовок Age наглядно увеличился
        second = probe("2. CDN — ПОВТОРНЫЙ запрос того же постера", CDN_BASE + POSTER)
        print_probe(second)

        # --- CDN: условный запрос по ETag ------------------------------
        etag = first.headers.get("ETag")
        third = probe("3. CDN — условный запрос If-None-Match (кэш браузера)", CDN_BASE + POSTER, etag)
        print_probe(third)
        if third.status == 304:
            print(f"  => Ответ 304: тело не передаётся, экономия {first.size} байт на запрос.\n")
        else:
            print(f"  => Внимание: ожидался 304, получен {third.status}.\n")

        # --- Origin ----------------------------------------------------
        o_first = probe("4. ORIGIN — первый запрос постера", ORIGIN_BASE + POSTER)
        print_probe(o_first)
        o_second = probe("5. ORIGIN — повторный запрос того же постера", ORIGIN_BASE + POSTER)
        print_probe(o_second)

        # --- Сводка ----------------------------------------------------
        print("=" * 78)
        print("СВОДКА: CDN против ORIGIN")
        print("=" * 78)
        print(f"{'Запрос':52s} {'Статус':>6s} {'Байт':>7s} {'мс':>8s}")
        print("-" * 78)
        for item in (first, second, third, o_first, o_second):
            print(f"{item.label:52s} {item.status:>6d} {item.size:>7d} {item.elapsed_ms:>8.2f}")
        print()
        print("Вывод:")
        print("  * CDN отдаёт Cache-Control: public, max-age=3600 — ответ можно кэшировать на час;")
        print(f"  * повторный запрос к CDN отдаёт Age={header(second, 'Age')} и тот же ETag={header(second, 'ETag')},")
        print(f"    а условный запрос If-None-Match — статус {third.status} без тела;")
        print("  * origin отдаёт Cache-Control: no-cache, no-store — каждый запрос идёт")
        print(f"    за полным файлом ({o_second.size} байт), кэширование запрещено;")
        print("  * статика (постеры, CSS, JS) вынесена на CDN, а не на сервер приложения.")
        print("=" * 78)
    finally:
        cdn_server.shutdown()
        origin_server.shutdown()
        cdn_server.server_close()
        origin_server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
