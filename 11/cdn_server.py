"""CDN-сервер (имитация edge-узла CDN) на базе http.server.

Отдаёт статику из папки static/ и добавляет заголовок
Cache-Control: public, max-age=3600 — браузер (и промежуточный кэш)
может 3600 секунд не запрашивать постеры повторно.

Запуск:  python cdn_server.py [--port 8091] [--dir static]
"""
from __future__ import annotations

import argparse
import logging
import mimetypes
import os
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

#: Политика кэширования CDN: ресурс публичный, живёт в кэше 1 час.
CACHE_CONTROL = "public, max-age=3600"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cdn")

#: Реестр mimetypes не всегда знает SVG (зависит от ОС) — регистрируем явно.
mimetypes.add_type("image/svg+xml", ".svg")


class CDNRequestHandler(SimpleHTTPRequestHandler):
    """Статический обработчик с CDN-заголовками.

    Реализованы заголовки кэширования:
      * Cache-Control: public, max-age=3600;
      * ETag (хеш от времени изменения и размера файла) и условный ответ
        304 Not Modified на If-None-Match — браузер не скачивает постер заново;
      * Age — сколько секунд ресурс живёт на edge-узле.
    """

    server_version = "DHSCDN/1.0"

    def etag_for(self, path: str) -> str | None:
        try:
            stat = os.stat(path)
        except OSError:
            return None
        return f'"{int(stat.st_mtime):x}-{stat.st_size:x}"'

    def send_head(self):
        """Обрабатывает If-None-Match (условный GET) до отдачи файла."""
        if self.headers.get("If-None-Match"):
            etag = self.etag_for(self.translate_path(self.path))
            if etag and etag == self.headers.get("If-None-Match"):
                self.send_response(304)
                self.end_headers()   # Cache-Control/ETag/Age добавит наш end_headers
                return None
        return super().send_head()

    def end_headers(self) -> None:
        first_seen: dict[str, float] = getattr(self.server, "first_seen", {})
        now = time.time()
        first = first_seen.setdefault(self.path, now)
        self.send_header("Cache-Control", CACHE_CONTROL)
        self.send_header("X-CDN-Node", "edge-1")
        self.send_header("Age", str(int(now - first)))
        etag = self.etag_for(self.translate_path(self.path))
        if etag:
            self.send_header("ETag", etag)
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s %s", self.address_string(), format % args)


def make_handler(directory: str | Path = STATIC_DIR):
    return partial(CDNRequestHandler, directory=str(directory))


def create_server(port: int = 8091, directory: str | Path = STATIC_DIR) -> ThreadingHTTPServer:
    """Создаёт готовый к запуску сервер (не блокирует поток)."""
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(directory))
    httpd.first_seen = {}  # type: ignore[attr-defined]
    return httpd


def main() -> None:
    parser = argparse.ArgumentParser(description="CDN-сервер для постеров")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--dir", default=str(STATIC_DIR))
    args = parser.parse_args()

    httpd = create_server(args.port, args.dir)
    logger.info("CDN-сервер: http://127.0.0.1:%s/ (Cache-Control: %s)",
                args.port, CACHE_CONTROL)
    print(f"CDN-сервер запущен: http://127.0.0.1:{args.port}/  (Ctrl+C — остановить)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCDN-сервер остановлен")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
