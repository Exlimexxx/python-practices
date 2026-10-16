"""Сервер-источник (origin) без кэширования.

Отдаёт те же файлы из static/, но с заголовками
Cache-Control: no-cache, no-store, must-revalidate — кэшировать нельзя.

Запуск:  python origin_server.py [--port 8092] [--dir static]
"""
from __future__ import annotations

import argparse
import logging
import mimetypes
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

#: Origin запрещает любое кэширование.
CACHE_CONTROL = "no-cache, no-store, must-revalidate"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("origin")

#: Реестр mimetypes не всегда знает SVG (зависит от ОС) — регистрируем явно.
mimetypes.add_type("image/svg+xml", ".svg")


class OriginRequestHandler(SimpleHTTPRequestHandler):
    """Обработчик сервера-источника: всегда отдаёт полный ответ."""

    server_version = "DHSOrigin/1.0"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", CACHE_CONTROL)
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Origin-Server", "origin-1")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s %s", self.address_string(), format % args)


def make_handler(directory: str | Path = STATIC_DIR):
    return partial(OriginRequestHandler, directory=str(directory))


def create_server(port: int = 8092, directory: str | Path = STATIC_DIR) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(directory))


def main() -> None:
    parser = argparse.ArgumentParser(description="Origin-сервер без кэширования")
    parser.add_argument("--port", type=int, default=8092)
    parser.add_argument("--dir", default=str(STATIC_DIR))
    args = parser.parse_args()

    httpd = create_server(args.port, args.dir)
    logger.info("Origin-сервер: http://127.0.0.1:%s/ (Cache-Control: %s)",
                args.port, CACHE_CONTROL)
    print(f"Origin-сервер запущен: http://127.0.0.1:{args.port}/  (Ctrl+C — остановить)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nOrigin-сервер остановлен")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
