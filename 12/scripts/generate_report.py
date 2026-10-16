"""Генерация итогового отчёта work/practice12/report.json.

Скрипт собирает структуру отчёта, записывает её через json.dump с
ensure_ascii=False и indent=2, затем повторно читает файл через json.load
и проверяет, что все указанные в блоках пути существуют.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # work/practice12
WORKSPACE = os.path.dirname(os.path.dirname(ROOT))                     # корень рабочей области
REPORT_PATH = os.path.join(ROOT, "report.json")

SKIP_DIRS = {"__pycache__", ".pytest_cache", "demo", ".git", ".idea"}
SKIP_PREFIX = ("pytest-cache-files-",)
SKIP_EXT = (".pyc", ".db", ".sqlite", ".sqlite3")


def build_tree(path: str, prefix: str = "") -> list[str]:
    """Построить текстовое дерево каталогов проекта."""
    entries = sorted(os.listdir(path))
    dirs = [
        e for e in entries
        if os.path.isdir(os.path.join(path, e))
        and e not in SKIP_DIRS
        and not e.startswith(SKIP_PREFIX)
    ]
    files = [
        e for e in entries
        if os.path.isfile(os.path.join(path, e)) and not e.endswith(SKIP_EXT)
    ]
    lines: list[str] = []
    items = [(d, True) for d in dirs] + [(f, False) for f in files]
    for index, (name, is_dir) in enumerate(items):
        last = index == len(items) - 1
        branch = "└── " if last else "├── "
        lines.append(prefix + branch + name + ("/" if is_dir else ""))
        if is_dir:
            lines.extend(build_tree(os.path.join(path, name), prefix + ("    " if last else "│   ")))
    return lines


TREE = "practice12/\n" + "\n".join(build_tree(ROOT))


def label(text_label: str, text: str) -> dict:
    return {"type": "label", "label": text_label, "text": text}


def heading(text: str) -> dict:
    return {"type": "heading", "text": text}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def code_block(caption: str, text: str) -> dict:
    return {"type": "code", "caption": caption, "text": text}


def code_file(caption: str, rel_path: str) -> dict:
    return {"type": "codefile", "caption": caption, "path": rel_path}


def output_file(caption: str, rel_path: str) -> dict:
    return {"type": "outputfile", "caption": caption, "path": rel_path}


BLOCKS: list[dict] = [
    label(
        "Ход работы (вариант 4)",
        "Предметная область — «Отель». Сущности: Guest (гость), Room (номер), "
        "Booking (бронирование). Требуется реализовать бронирование номера и проверку "
        "пересечения бронирований средствами SQLAlchemy 2.x ORM.",
    ),
    label(
        "Цель работы",
        "Изучить работу с реляционными базами данных в Python с использованием "
        "SQLAlchemy 2.x ORM: описать декларативные модели и связи, реализовать CRUD, "
        "поиск, фильтрацию и сортировку, а также транзакционное бронирование номера "
        "с проверкой пересечения дат и откатом при ошибке.",
    ),
    heading("Постановка задачи (вариант 4 — «Отель»)"),
    text_block(
        "Необходимо разработать приложение для управления бронированием номеров отеля. "
        "Приложение должно хранить гостей, номера и бронирования в реляционной базе данных, "
        "предоставлять операции создания, чтения, изменения и удаления записей, поддерживать "
        "поиск и фильтрацию, а также транзакционно оформлять бронь: проверить корректность дат, "
        "существование гостя и номера, активность номера, достаточную вместимость и отсутствие "
        "пересечения с уже существующими бронями, рассчитать стоимость и только затем вставить запись."
    ),
    label(
        "Модели и поля",
        "Guest: id (PK), full_name (NOT NULL), email (UNIQUE, NOT NULL, индекс), phone (NOT NULL). "
        "Room: id (PK), number (UNIQUE, NOT NULL, индекс), room_type, capacity, price_per_night "
        "(NUMERIC(10,2)), is_active. Booking: id (PK), guest_id (FK → guests.id, NOT NULL), "
        "room_id (FK → rooms.id, NOT NULL), check_in (DATE, NOT NULL), check_out (DATE, NOT NULL), "
        "status, total_price (NUMERIC(10,2)).",
    ),
    label(
        "Связи",
        "Реализованы две связи one-to-many: Guest → Booking (guest.bookings / booking.guest) и "
        "Room → Booking (room.bookings / booking.room). Обе описаны через relationship с "
        "back_populates. Для гостя задан каскад all, delete-orphan, для номера — ограничение "
        "ON DELETE RESTRICT на уровне внешнего ключа.",
    ),
    label(
        "Ограничения целостности",
        "Первичные и внешние ключи, NOT NULL для обязательных полей, UNIQUE для email гостя и "
        "номера комнаты, а также CHECK-ограничения: check_out > check_in, capacity > 0, "
        "price_per_night >= 0, total_price >= 0. Для SQLite принудительно включена проверка "
        "внешних ключей через PRAGMA foreign_keys=ON.",
    ),
    heading("Структура проекта"),
    text_block(
        "Проект разделён на слои: app/models — ORM-модели, app/repositories — доступ к данным "
        "исключительно через select()/ORM, app/services — бизнес-логика и границы транзакций, "
        "app/main.py — консольное приложение с меню. Дополнительно: app/database.py "
        "(подключение, Base, фабрика сессий), app/exceptions.py (собственная иерархия исключений), "
        "tests/ (pytest), scripts/demo_transaction.py (демонстрация commit и rollback)."
    ),
    code_block("Дерево проекта", TREE),
    heading("Листинги основных файлов"),
    text_block(
        "Ниже приведены исходные коды основных модулей приложения. Используется только "
        "декларативный стиль SQLAlchemy 2.x (DeclarativeBase, Mapped, mapped_column, relationship, "
        "select); прямые SQL-запросы для основных операций не применяются."
    ),
    code_file("app/database.py — подключение к БД, Base, фабрика сессий", "work/practice12/app/database.py"),
    code_file("app/exceptions.py — собственная иерархия исключений", "work/practice12/app/exceptions.py"),
    code_file("app/models/guest.py — модель Guest", "work/practice12/app/models/guest.py"),
    code_file("app/models/room.py — модель Room", "work/practice12/app/models/room.py"),
    code_file("app/models/booking.py — модель Booking и статусы", "work/practice12/app/models/booking.py"),
    code_file("app/repositories/base.py — обобщённый CRUD-репозиторий", "work/practice12/app/repositories/base.py"),
    code_file("app/repositories/guest_repository.py — гости: CRUD, поиск, сортировка", "work/practice12/app/repositories/guest_repository.py"),
    code_file("app/repositories/room_repository.py — номера: фильтры и свободные номера", "work/practice12/app/repositories/room_repository.py"),
    code_file("app/repositories/booking_repository.py — брони и поиск пересечений", "work/practice12/app/repositories/booking_repository.py"),
    code_file("app/services/hotel_service.py — бизнес-логика и транзакции", "work/practice12/app/services/hotel_service.py"),
    code_file("app/main.py — консольное приложение с меню", "work/practice12/app/main.py"),
    heading("Тесты"),
    text_block(
        "Тесты написаны на pytest и используют изолированную базу SQLite в памяти. Проверяются "
        "модели и ограничения целостности, репозитории (поиск, фильтрация, сортировки, "
        "обнаружение пересечений) и сервисы (транзакции, откаты, обработка ошибок)."
    ),
    code_file("tests/conftest.py — фикстуры", "work/practice12/tests/conftest.py"),
    code_file("tests/test_models.py — модели и ограничения", "work/practice12/tests/test_models.py"),
    code_file("tests/test_repositories.py — репозитории", "work/practice12/tests/test_repositories.py"),
    code_file("tests/test_services.py — сервисы и транзакции", "work/practice12/tests/test_services.py"),
    label(
        "Инфраструктура",
        "Зависимости зафиксированы в requirements.txt (SQLAlchemy>=2.0, pytest, psycopg для "
        "PostgreSQL). В pytest.ini заданы testpaths=tests. README.md содержит инструкции по "
        "установке, запуску и переключению на PostgreSQL.",
    ),
    heading("Результаты выполнения"),
    text_block(
        "Демонстрации выполнены реальными запусками в среде Windows с интерпретатором "
        "C:\\Users\\Artem\\AppData\\Local\\Programs\\Python\\Python313\\python.exe. "
        "Выводы сохранены без редактирования в каталоге work/practice12/demo."
    ),
    output_file(
        "Результат выполнения: прогон консольного приложения main.py (сценарий из demo/scenario_console.txt)",
        "work/practice12/demo/console.txt",
    ),
    output_file(
        "Результат выполнения: успешная транзакция и откаты (scripts/demo_transaction.py, SQL-эхо)",
        "work/practice12/demo/transaction.txt",
    ),
    output_file(
        "Результат выполнения: pytest -v (все тесты проходят)",
        "work/practice12/demo/pytest.txt",
    ),
    heading("Соответствие требованиям методички"),
    label("Только SQLAlchemy 2.x ORM", "модели описаны через DeclarativeBase/Mapped/mapped_column, связи — через relationship, запросы — через select(); прямой SQL для основных операций не используется."),
    label("Минимум 3 таблицы", "реализованы guests, rooms и bookings со всеми требуемыми полями."),
    label("Ключи и ограничения", "первичные ключи, внешние ключи guest_id и room_id, NOT NULL, UNIQUE (guests.email, rooms.number), CHECK-ограничения на даты, вместимость и цены."),
    label("Связи one-to-many", "Guest → Booking и Room → Booking, обе через relationship + back_populates (превышает минимальное требование одной связи)."),
    label("CRUD", "создание, получение по id, получение списка, изменение и удаление реализованы для гостей, номеров и броней (BaseRepository + специализированные методы)."),
    label("Поиск по атрибутам", "GuestRepository.search() комбинирует условия по ФИО, телефону и email (AND), find_by_name_or_email() — OR-условие; RoomRepository.search() — тип, вместимость, активность, диапазон цены."),
    label("Фильтрация", "свободные номера на даты (find_available), активные/неактивные номера, брони по статусу, датам и диапазону стоимости."),
    label("Две сортировки", "номера — по цене и по вместимости; брони — по дате заезда и по итоговой стоимости (плюс сортировка гостей по ФИО)."),
    label("Связанные объекты", "bookings_of_guest() и bookings_of_room() возвращают связанные брони; связи подгружаются через joinedload/selectin, есть JOIN трёх таблиц."),
    label("Транзакция", "book_room() в одной транзакции выполняет проверку дат, существования гостя и номера, активности номера, вместимости, пересечения броней, рассчитывает стоимость, вставляет запись и делает commit; при ошибке — session.rollback() и доменное исключение."),
    label("Обработка ошибок", "реализованы исключения ValidationError, NotFoundError, DuplicateError, NotEnoughCapacityError, RoomUnavailableError, BookingConflictError, TransactionError; консольное приложение перехватывает их и не завершается аварийно."),
    label("Консольное приложение", "app/main.py реализует меню из 18 пунктов с чтением input() и обработкой ошибок на каждом шаге."),
    label("pytest", "31 тест: модели и ограничения, репозитории, сервисы (включая проверку пересечения бронирований и откатов). Все тесты проходят."),
    heading("Отклонения и ограничения"),
    label(
        "СУБД",
        "Отклонение от методички: сервер PostgreSQL в учебной среде не установлен, поэтому "
        "демонстрации выполнены на SQLite. Строка подключения не зашита в код, а настраивается "
        "через переменную окружения HOTEL_DATABASE_URL или константу DEFAULT_DATABASE_URL в "
        "app/database.py, поэтому переключение на PostgreSQL не требует изменений в моделях, "
        "репозиториях и сервисах.",
    ),
    label(
        "Как переключиться на PostgreSQL",
        "достаточно установить драйвер psycopg (входит в requirements.txt) и задать строку "
        "подключения; виртуальный адрес сервера в примере — localhost:5432, база hotel_db:",
    ),
    code_block(
        "Пример строки подключения PostgreSQL и запуск",
        "set HOTEL_DATABASE_URL=postgresql+psycopg://hotel_user:secret@localhost:5432/hotel_db\n"
        "python -m app.main\n\n"
        "# либо через атрибут при создании приложения:\n"
        "# configure_database(\"postgresql+psycopg://hotel_user:secret@localhost:5432/hotel_db\")",
    ),
    label(
        "Особенности SQLite",
        "для SQLite вручную включён контроль внешних ключей (PRAGMA foreign_keys=ON) и для "
        "базы в памяти используется StaticPool, иначе каждая сессия видела бы свою пустую БД. "
        "Тип NUMERIC в SQLite хранится как число с плавающей точкой, поэтому в консольном "
        "выводе цены иногда печатаются как 3500 вместо 3500.00.",
    ),
    label(
        "Прочие замечания",
        "каталог pytest-cache-files-* в корне проекта — служебный каталог pytest, который среда "
        "не позволила удалить; он исключён из обхода через pytest.ini (testpaths=tests) и не "
        "влияет на тесты. Часть файлов базы demo/*.db созданы в ходе демонстраций.",
    ),
    heading("Вывод"),
    text_block(
        "В результате работы разработано приложение «Отель» на SQLAlchemy 2.x ORM с тремя "
        "связанными таблицами, полным набором CRUD-операций, поиском по нескольким атрибутам, "
        "фильтрацией и двумя вариантами сортировки для каждой сущности. Реализована "
        "транзакционная операция бронирования: проверка корректности дат, существования гостя и "
        "номера, активности номера, вместимости и пересечения броней, расчёт стоимости и вставка "
        "записи; при любой ошибке выполняется session.rollback() и выбрасывается понятное "
        "исключение, а приложение продолжает работу. Корректность подтверждена 31 автотестом "
        "pytest (все проходят) и реальными протоколами запусков консольного приложения и "
        "демонстрации транзакций. Требования методички выполнены; единственное отклонение — "
        "использование SQLite вместо PostgreSQL из-за отсутствия сервера, при этом строка "
        "подключения настраивается и готова к переключению на PostgreSQL."
    ),
]


def main() -> int:
    report = {
        "practice": 12,
        "title": "ПРАКТИЧЕСКАЯ РАБОТА №12",
        "subtitle": "Работа с реляционными базами данных в Python с использованием SQLAlchemy и ORM",
        "goal": (
            "Изучить применение SQLAlchemy 2.x ORM для работы с реляционной базой данных: "
            "описать модели Guest, Room и Booking со связями и ограничениями целостности, "
            "реализовать CRUD, поиск, фильтрацию и сортировку данных. "
            "Разработать транзакционную операцию бронирования номера с проверкой пересечения дат "
            "и расчётом стоимости."
        ),
        "blocks": BLOCKS,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    # Проверка: читаем файл заново через json.load.
    with open(REPORT_PATH, encoding="utf-8") as file:
        loaded = json.load(file)

    allowed = {"label", "heading", "text", "code", "codefile", "outputfile"}
    missing = []
    for block in loaded["blocks"]:
        assert block["type"] in allowed, "Недопустимый тип блока: " + block["type"]
        if block["type"] in {"codefile", "outputfile"}:
            full = os.path.join(WORKSPACE, block["path"])
            if not os.path.isfile(full):
                missing.append(block["path"])

    print("report.json создан:", REPORT_PATH)
    print("Блоков:", len(loaded["blocks"]))
    print("Проверка json.load: OK")
    print("Отсутствующие пути:", missing if missing else "нет")
    assert not missing, "Не найдены файлы: " + ", ".join(missing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
