#!/usr/bin/env python
"""Демонстрационный сценарий лабораторной работы №15 (вариант 4 «Отель»).

Скрипт поднимает Flask-приложение через subprocess на порту 5015, выполняет
реальные HTTP-запросы к HTML-страницам и REST API (requests + httpx),
демонстрирует сценарий бронирования и отказ при пересечении дат,
после чего останавливает сервер.

Запуск (из каталога work/practice15):
    python demo/run_demo.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_DIR = Path(__file__).resolve().parent
DB_PATH = DEMO_DIR / "demo_hotel.db"
HOST = "127.0.0.1"
PORT = 5015
BASE_URL = f"http://{HOST}:{PORT}"

SEPARATOR = "=" * 78


def title(text: str) -> None:
    """Печатает заголовок раздела демонстрации."""
    print()
    print(SEPARATOR)
    print(text)
    print(SEPARATOR)


def show(label: str, response: requests.Response | httpx.Response, *, json_out: bool = True,
         snippet: int = 0) -> None:
    """Печатает компактную информацию об HTTP-ответе."""
    content_type = response.headers.get("Content-Type", "?")
    print(f"{label:<58} -> HTTP {response.status_code}  [{content_type.split(';')[0]}]")
    if json_out and "application/json" in content_type:
        print("    JSON: " + json.dumps(response.json(), ensure_ascii=False)[:1200])
        return
    match = re.search(r"<title>(.*?)</title>", response.text, re.DOTALL)
    if match:
        print(f"    <title>: {match.group(1).strip()}")
    if snippet and response.text.lstrip().startswith("<!DOCTYPE"):
        body = re.sub(r"<[^>]+>", " ", response.text)
        body = " ".join(body.split())
        print(f"    Текст страницы: {body[:snippet]}...")


def wait_for_server(process: subprocess.Popen, timeout: float = 25.0) -> None:
    """Ожидает готовности сервера, опрашивая /api."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Сервер завершился с кодом {process.returncode}")
        try:
            response = requests.get(f"{BASE_URL}/api", timeout=1.0)
            if response.status_code == 200:
                print(f"Сервер готов: {BASE_URL} (ответ /api = {response.status_code})")
                return
        except requests.RequestException:
            time.sleep(0.3)
    raise TimeoutError("Сервер не запустился за отведённое время")


def start_server() -> subprocess.Popen:
    """Запускает Flask в отдельном процессе с чистой БД."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{DB_PATH.as_posix()}",
            "SECRET_KEY": "demo-secret-key",
            "FLASK_ENV": "development",
            "FLASK_DEBUG": "0",
            "LOG_LEVEL": "INFO",
            "LOG_FILE": str((DEMO_DIR / "server.log").as_posix()),
            "SQL_ECHO": "0",
            "HOST": HOST,
            "PORT": str(PORT),
            "SEED_DEMO": "1",
        }
    )
    log_handle = open(DEMO_DIR / "server_stdout.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=BASE_DIR,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    print(f"Запуск: {sys.executable} run.py  (cwd={BASE_DIR})")
    print(f"БД: {DB_PATH}")
    return process


def demo_html(session: requests.Session) -> None:
    """Демонстрация серверного рендеринга HTML-страниц."""
    title("1. HTML-ИНТЕРФЕЙС (серверный рендеринг Jinja2)")
    pages = [
        ("Главная страница", "/", 160),
        ("Список номеров", "/rooms", 160),
        ("Карточка номера №101", "/rooms/1", 160),
        ("Список гостей", "/guests", 160),
        ("Карточка гостя №1", "/guests/1", 160),
        ("Список бронирований", "/bookings", 160),
        ("Форма создания номера", "/rooms/create", 120),
        ("Поиск+фильтр+сортировка: /rooms?search=люкс&sort=price&order=desc",
         "/rooms?search=люкс&sort=price&order=desc", 0),
        ("Фильтр: только закрытые номера /rooms?is_active=0", "/rooms?is_active=0", 0),
        ("Несуществующая страница (404)", "/rooms/9999", 0),
        ("Несуществующий адрес (404)", "/no-such-page", 0),
    ]
    for label, path, snippet in pages:
        response = session.get(BASE_URL + path)
        show(label, response, json_out=False, snippet=snippet)


def demo_api_crud(session: requests.Session) -> dict:
    """Демонстрация REST API: CRUD номеров и гостей, ошибки."""
    title("2. REST API: CRUD, коды ответов, ошибки")
    show("GET /api/rooms", session.get(f"{BASE_URL}/api/rooms"))
    show("GET /api/rooms/1", session.get(f"{BASE_URL}/api/rooms/1"))

    create_room = session.post(
        f"{BASE_URL}/api/rooms",
        json={"number": "512", "room_type": "Комфорт", "capacity": 3,
              "price_per_night": 7200.0, "floor": 5, "description": "Номер из REST API"},
    )
    show("POST /api/rooms (создание)", create_room)
    room_id = create_room.json()["id"]

    show(f"PUT /api/rooms/{room_id}", session.put(
        f"{BASE_URL}/api/rooms/{room_id}", json={"price_per_night": 7500.0}))
    show(f"PATCH /api/rooms/{room_id}", session.patch(
        f"{BASE_URL}/api/rooms/{room_id}", json={"description": "Цена обновлена"}))
    show(f"GET /api/rooms/{room_id}", session.get(f"{BASE_URL}/api/rooms/{room_id}"))

    show("POST /api/rooms без обязательного поля (400)", session.post(
        f"{BASE_URL}/api/rooms", json={"room_type": "Стандарт"}))
    show("POST /api/rooms с дубликатом номера (400)", session.post(
        f"{BASE_URL}/api/rooms", json={"number": "101", "room_type": "Стандарт", "capacity": 2,
                                       "price_per_night": 1000, "floor": 1}))
    show("GET /api/rooms/424242 (404)", session.get(f"{BASE_URL}/api/rooms/424242"))
    show("DELETE /api/rooms (405)", session.delete(f"{BASE_URL}/api/rooms"))
    show("GET /api/rooms?search=люкс&sort=price&order=desc",
         session.get(f"{BASE_URL}/api/rooms", params={"search": "люкс", "sort": "price", "order": "desc"}))

    guest = session.post(
        f"{BASE_URL}/api/guests",
        json={"full_name": "Демо Гость", "email": "demo@example.com",
              "phone": "+7-999-000-11-22", "passport": "9999 000000", "city": "Тверь"},
    )
    show("POST /api/guests (создание)", guest)
    show("POST /api/guests с плохим email (400)", session.post(
        f"{BASE_URL}/api/guests", json={"full_name": "Плохой", "email": "не-почта"}))
    show(f"GET /api/guests/{guest.json()['id']}", session.get(f"{BASE_URL}/api/guests/{guest.json()['id']}"))

    cleanup = session.delete(f"{BASE_URL}/api/rooms/{room_id}")
    print(f"DELETE /api/rooms/{room_id} -> HTTP {cleanup.status_code} (No Content, тело пустое: {cleanup.text!r})")
    return {"guest_id": guest.json()["id"]}


def demo_booking(session: requests.Session, guest_id: int) -> None:
    """Сценарий бронирования: успех, расчёт стоимости, отказ при пересечении."""
    title("3. БИЗНЕС-ЛОГИКА: бронирование и проверка пересечения дат")
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=4)
    payload = {
        "room_id": 1,
        "guest_id": guest_id,
        "check_in": start.isoformat(),
        "check_out": end.isoformat(),
        "guests_count": 2,
        "comment": "Демонстрационное бронирование",
    }
    print(f"Сценарий: номер №101, {start} → {end} ({(end - start).days} ночей), "
          f"цена за ночь 4200.00 ₽")

    availability = session.get(
        f"{BASE_URL}/api/rooms/1/availability",
        params={"check_in": start.isoformat(), "check_out": end.isoformat()},
    )
    show("GET /api/rooms/1/availability (свободно?)", availability)
    print(f"    Расчётная стоимость: {availability.json()['estimated_price']} ₽")

    created = session.post(f"{BASE_URL}/api/bookings", json=payload)
    show("POST /api/bookings (бронирование)", created)
    booking_id = created.json()["id"]

    overlap = dict(payload)
    overlap["check_in"] = (start + timedelta(days=1)).isoformat()
    overlap["check_out"] = (start + timedelta(days=6)).isoformat()
    response = session.post(f"{BASE_URL}/api/bookings", json=overlap)
    show("POST /api/bookings теми же датами (ожидается 409)", response)

    adjacent = dict(payload)
    adjacent["check_in"] = end.isoformat()
    adjacent["check_out"] = (end + timedelta(days=2)).isoformat()
    show("POST /api/bookings сразу после выезда (201, пересечения нет)",
         session.post(f"{BASE_URL}/api/bookings", json=adjacent))

    show("POST /api/bookings с check_out <= check_in (400)", session.post(
        f"{BASE_URL}/api/bookings", json={**payload,
                                          "check_in": start.isoformat(),
                                          "check_out": start.isoformat()}))
    show("POST /api/bookings на 5 гостей в 2-местный номер (400)", session.post(
        f"{BASE_URL}/api/bookings", json={**payload, "guests_count": 5,
                                          "check_in": (start + timedelta(days=20)).isoformat(),
                                          "check_out": (start + timedelta(days=22)).isoformat()}))

    print("Отмена бронирования и повторное использование дат:")
    show(f"POST /api/bookings/{booking_id}/cancel", session.post(
        f"{BASE_URL}/api/bookings/{booking_id}/cancel"))
    show("POST /api/bookings повторно на освободившиеся даты (201)", session.post(
        f"{BASE_URL}/api/bookings", json=payload))


def demo_html_booking_form(session: requests.Session, guest_id: int) -> None:
    """Демонстрация HTML-формы бронирования и flash-сообщений."""
    title("4. HTML-ФОРМА БРОНИРОВАНИЯ (flash-сообщения и валидация)")
    start = date.today() + timedelta(days=90)
    end = start + timedelta(days=3)
    form = {"room_id": "2", "guest_id": str(guest_id), "check_in": start.isoformat(),
            "check_out": end.isoformat(), "guests_count": "1", "status": "confirmed",
            "comment": "Бронь через HTML-форму"}
    response = session.post(f"{BASE_URL}/bookings/create", data=form, allow_redirects=True)
    text = " ".join(response.text.split())
    print(f"POST /bookings/create -> HTTP {response.status_code}")
    print(f"    Есть успешное flash-сообщение: {'оформлено' in text}")

    overlap = dict(form)
    overlap["check_in"] = (start + timedelta(days=1)).isoformat()
    overlap["check_out"] = (start + timedelta(days=4)).isoformat()
    response = session.post(f"{BASE_URL}/bookings/create", data=overlap)
    text = " ".join(response.text.split())
    print(f"POST /bookings/create с пересечением -> HTTP {response.status_code}")
    print(f"    Показано сообщение об отказе: {'уже забронирован' in text}")

    bad = session.post(f"{BASE_URL}/bookings/create",
                       data={"room_id": "1", "guest_id": str(guest_id), "check_in": "",
                             "check_out": ""})
    print(f"POST /bookings/create без дат -> HTTP {bad.status_code}")
    print(f"    Показано сообщение валидации: {'обязательно' in bad.text}")


def demo_httpx() -> None:
    """Дополнительно проверяем API клиентом httpx."""
    title("5. ПРОВЕРКА API КЛИЕНТОМ httpx")
    # trust_env=False: не используем системные proxy-настройки, обращаемся
    # к локальному серверу напрямую.
    with httpx.Client(base_url=BASE_URL, timeout=10.0, trust_env=False) as client:
        response = client.get("/api/bookings", params={"status": "confirmed", "sort": "price",
                                                       "order": "desc"})
        print(f"httpx GET /api/bookings?status=confirmed&sort=price&order=desc -> HTTP {response.status_code}")
        data = response.json()
        print(f"    Подтверждённых броней: {data['count']}")
        for item in data["items"][:3]:
            print(f"    - №{item['id']}: номер {item['room']['number']}, "
                  f"{item['check_in']}..{item['check_out']}, {item['total_price']} ₽")
        summary = client.get("/api")
        print(f"httpx GET /api -> HTTP {summary.status_code}: {json.dumps(summary.json(), ensure_ascii=False)[:220]}")


def main() -> int:
    """Основная процедура демонстрации."""
    print("ЛАБОРАТОРНАЯ РАБОТА №15 · Вариант 4 «Отель» · Flask + SQLAlchemy")
    process = start_server()
    session = requests.Session()
    try:
        wait_for_server(process)
        demo_html(session)
        ctx = demo_api_crud(session)
        demo_booking(session, ctx["guest_id"])
        demo_html_booking_form(session, ctx["guest_id"])
        demo_httpx()
        title("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        session.close()
        print(f"Сервер остановлен (код возврата {process.returncode}).")
        print("Журнал сервера сохранён в demo/server.log, stdout сервера — в demo/server_stdout.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
