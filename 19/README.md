# Лабораторная работа №19 — гостиница, микросервисы (вариант 4)

Три доменных сервиса имеют независимые SQLite-файлы/volume: rooms, guests, bookings. Клиент обращается к API Gateway. Сервис бронирований проверяет номер и гостя через HTTP, считает стоимость и проверяет пересечение дат; событие `BookingCreated` передаётся через RabbitMQ в Notification Service. Для сетевых вызовов есть bounded retry и Circuit Breaker.

`docker compose up --build` — запуск контейнерного стенда. API Gateway публикуется на `http://localhost:8000`; `/health` — проверка доступности. Тесты без контейнеров: `python -m pytest -v` из каталога проекта.
