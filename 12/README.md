# Практическая работа №12. Вариант 4 — «Отель»

Работа с реляционными базами данных в Python с использованием **SQLAlchemy 2.x ORM**.

Демонстрируются: декларативные модели (DeclarativeBase, Mapped, mapped_column),
связи one-to-many (relationship + back_populates), CRUD, поиск и фильтрация,
сортировки, получение связанных объектов и транзакционное бронирование номера
с проверкой пересечения дат.

## Предметная область

Три сущности: **Guest** (гость), **Room** (номер), **Booking** (бронирование).

| Таблица    | Поля                                                                                 |
|------------|--------------------------------------------------------------------------------------|
| guests     | id (PK), full_name (NOT NULL), email (UNIQUE, NOT NULL), phone (NOT NULL)             |
| rooms      | id (PK), number (UNIQUE, NOT NULL), room_type, capacity, price_per_night, is_active   |
| bookings   | id (PK), guest_id (FK->guests), room_id (FK->rooms), check_in, check_out, status, total_price |

Ограничения целостности: CHECK (check_out > check_in), CHECK (capacity > 0),
CHECK (price_per_night >= 0), CHECK (total_price >= 0), внешние ключи
ON DELETE CASCADE (гость -> брони) и ON DELETE RESTRICT (номер -> брони).

## Структура проекта

```
practice12/
|-- app/
|   |-- __init__.py
|   |-- database.py            # Engine, Base, фабрика сессий, строка подключения
|   |-- exceptions.py          # собственная иерархия исключений
|   |-- main.py                # консольное приложение с меню
|   |-- models/                # ORM-модели
|   |   |-- __init__.py
|   |   |-- guest.py
|   |   |-- room.py
|   |   |-- booking.py
|   |-- repositories/          # доступ к данным (select, фильтры, сортировки)
|   |   |-- __init__.py
|   |   |-- base.py
|   |   |-- guest_repository.py
|   |   |-- room_repository.py
|   |   |-- booking_repository.py
|   |-- services/              # бизнес-логика и транзакции
|       |-- __init__.py
|       |-- hotel_service.py
|-- scripts/
|   |-- demo_transaction.py    # демонстрация commit и rollback
|-- tests/
|   |-- conftest.py
|   |-- test_models.py
|   |-- test_repositories.py
|   |-- test_services.py
|-- demo/                      # сохранённые реальные протоколы запусков
|-- requirements.txt
|-- pytest.ini
|-- README.md
```

## Установка и запуск

```bash
pip install -r requirements.txt
python -m app.main                 # консольное приложение
python scripts/demo_transaction.py # демонстрация транзакций
python -m pytest -v                # тесты
```

## Настройка подключения к БД

Строка подключения задаётся переменной окружения HOTEL_DATABASE_URL
(см. app/database.py), по умолчанию — файл SQLite hotel.db:

```bash
set HOTEL_DATABASE_URL=sqlite:///hotel.db
set HOTEL_DATABASE_URL=postgresql+psycopg://hotel_user:secret@localhost:5432/hotel_db
```

Весь код приложения не зависит от конкретной СУБД: используются только
конструкции SQLAlchemy ORM, поэтому смена строки подключения переводит
приложение на PostgreSQL без изменения моделей, репозиториев и сервисов.

## Отклонение от методички

В учебной среде отсутствует сервер PostgreSQL, поэтому демонстрации выполнены
на SQLite. Строка подключения вынесена в конфигурацию, а в database.py
приведён рабочий пример строки для PostgreSQL. Для SQLite вручную включён
контроль внешних ключей (PRAGMA foreign_keys=ON), так как по умолчанию
SQLite их не проверяет.
