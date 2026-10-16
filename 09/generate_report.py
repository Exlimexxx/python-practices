"""Генерация итогового отчёта work/practice9/report.json.

Скрипт собирает структуру отчёта строго по схеме, записывает её через
json.dump(..., ensure_ascii=False, indent=2), затем повторно читает файл
через json.load и проверяет, что все указанные в блоках пути существуют.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR.parent.parent  # .../default-workspace
REPORT_PATH = BASE_DIR / "report.json"


def rel(path: str | Path) -> str:
    """Путь относительно рабочей директории workspace (с прямыми слэшами)."""
    return str(Path(path).resolve().relative_to(WORKSPACE)).replace("\\", "/")


def codefile(caption: str, name: str) -> Dict[str, Any]:
    return {"type": "codefile", "caption": caption, "path": rel(BASE_DIR / name)}


def outputfile(caption: str, name: str) -> Dict[str, Any]:
    return {"type": "outputfile", "caption": caption, "path": rel(BASE_DIR / "demo" / name)}


def label(text_label: str, text: str) -> Dict[str, Any]:
    return {"type": "label", "label": text_label, "text": text}


def heading(text: str) -> Dict[str, Any]:
    return {"type": "heading", "text": text}


def paragraph(text: str) -> Dict[str, Any]:
    return {"type": "text", "text": text}


def code_block(caption: str, text: str) -> Dict[str, Any]:
    return {"type": "code", "caption": caption, "text": text}


TREE = """work/practice9/
├── models.py            # сущность Student + проверка значений
├── exceptions.py        # собственные исключения (AppError, ProtocolError, ...)
├── repository.py        # хранилище в памяти (dict + RLock)
├── service.py           # бизнес-логика: CRUD, фильтры, average_grade, groups
├── protocol.py          # JSON-протокол и LineBuffer (границы сообщений)
├── server.py            # TCP-сервер (socket + ThreadPoolExecutor) + UDP status
├── client.py            # TCP-клиент: консольное меню и пакетный режим
├── udp_client.py        # UDP-клиент операции status
├── run_demo.py          # автодемонстрация -> demo/*.txt
├── conftest.py          # sys.path для pytest
├── README.md
├── tests/
│   ├── __init__.py
│   ├── test_repository.py   # 6 тестов Repository
│   ├── test_service.py      # 9 тестов Service
│   ├── test_protocol.py     # 7 тестов протокола
│   └── test_integration.py  # 5 интеграционных тестов (TCP, UDP, 3 клиента, тайм-аут)
└── demo/
    ├── server_client.txt    # сервер + клиент: команды, ошибки, тайм-аут
    ├── clients3.txt         # три клиента одновременно
    ├── udp.txt              # операция status по UDP
    ├── pytest.txt           # вывод pytest (28 passed)
    ├── scripts/             # сценарии клиентов (stdin)
    └── logs/                # журналы сервера
"""

PROTOCOL_EXAMPLE = """Запрос клиента (каждый JSON заканчивается символом перевода строки):
{"command": "average_grade", "data": {"id": 1}}

Успешный ответ:
{"status": "ok", "data": {"id": 1, "name": "Иванов Иван Иванович", "group": "ИУ7-31Б",
 "grades": [5, 4, 5, 5], "grades_count": 4, "average_grade": 4.75, "min_grade": 4, "max_grade": 5}}

Ответ-ошибка (все требуемые ситуации этапа 8 показаны в demo/server_client.txt):
{"status": "error", "error": "Студент с id=4 не найден", "code": "not_found"}
"""


def build_blocks() -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 1. вариант и постановка задачи
    # ------------------------------------------------------------------
    blocks.append(
        label(
            "Ход работы (вариант 4)",
            "Выполнена лабораторная работа №9 «Сетевое взаимодействие в Python: TCP/UDP, "
            "клиент-серверная архитектура и прикладные протоколы», вариант 4. Предметная область -- "
            "«Университет», основная сущность -- Student (id, name -- ФИО, group -- группа, "
            "grades -- список оценок, а также дополнительные поля email, year, status). "
            "Специализированная команда варианта -- average_grade (расчёт среднего балла студента). "
            "Реализованы все этапы методички: модель, репозиторий, сервис, собственный JSON-протокол, "
            "многопоточный TCP-сервер, TCP-клиент с консольным меню, обработка ошибок, тайм-ауты, "
            "логирование, одновременная работа трёх клиентов, автотесты pytest и дополнительная "
            "UDP-операция status.",
        )
    )
    blocks.append(heading("1. Постановка задачи"))
    blocks.append(
        paragraph(
            "Требуется разработать клиент-серверное приложение с разделением на слои: "
            "клиент и сервер находятся в разных файлах, бизнес-логика отделена от сетевого кода, "
            "используются модули models.py, repository.py, service.py, protocol.py, exceptions.py, "
            "тесты размещены в tests/. Данные хранятся в памяти процесса (list/dict), база данных "
            "не используется. Запрещены Flask, FastAPI, requests, Django и любые библиотеки, "
            "скрывающие работу с сокетами: применяется только стандартная библиотека socket и json.",
        )
    )
    blocks.append(heading("2. Описание варианта 4"))
    blocks.append(
        label(
            "Основная сущность",
            "Student -- dataclass из семи полей: id (int, идентификатор), name (ФИО), group (учебная "
            "группа), grades (список оценок 2..5), email, year (курс 1..6), status (active / "
            "academic_leave / expelled). Требование «идентификатор + не менее трёх дополнительных "
            "полей» выполнено с запасом: кроме id у сущности шесть полей.",
        )
    )
    blocks.append(
        label(
            "Специализированная команда",
            "average_grade -- по идентификатору студента возвращает его средний балл, количество, "
            "минимальную и максимальную оценку, а также ФИО и группу. Дополнительно реализованы "
            "команды groups (сводка по группам), status (состояние сервера, в том числе по UDP) и ping.",
        )
    )
    blocks.append(
        label(
            "Команды протокола",
            "list, get, create, update, delete, average_grade -- шесть обязательных команд; "
            "дополнительно groups, status, ping (служебная команда sleep применяется только для "
            "демонстрации тайм-аута). Итого сервер поддерживает десять команд.",
        )
    )
    blocks.append(code_block("Пример обмена по протоколу", PROTOCOL_EXAMPLE))

    # ------------------------------------------------------------------
    # 2. структура проекта
    # ------------------------------------------------------------------
    blocks.append(heading("3. Структура проекта"))
    blocks.append(code_block("Дерево файлов проекта", TREE))

    # ------------------------------------------------------------------
    # 3. листинги
    # ------------------------------------------------------------------
    blocks.append(heading("Листинг программы"))
    blocks.append(codefile("models.py -- сущность Student и проверка значений", "models.py"))
    blocks.append(codefile("exceptions.py -- собственные исключения", "exceptions.py"))
    blocks.append(codefile("repository.py -- хранилище в памяти", "repository.py"))
    blocks.append(codefile("service.py -- бизнес-логика (average_grade, фильтрация)", "service.py"))
    blocks.append(codefile("protocol.py -- JSON-протокол и границы сообщений", "protocol.py"))
    blocks.append(codefile("server.py -- TCP-сервер (ThreadPoolExecutor) и UDP-сервер status", "server.py"))
    blocks.append(codefile("client.py -- TCP-клиент с консольным меню", "client.py"))
    blocks.append(codefile("udp_client.py -- UDP-клиент операции status", "udp_client.py"))
    blocks.append(codefile("run_demo.py -- автоматическая демонстрация", "run_demo.py"))
    blocks.append(codefile("tests/test_repository.py -- тесты Repository", "tests/test_repository.py"))
    blocks.append(codefile("tests/test_service.py -- тесты Service", "tests/test_service.py"))
    blocks.append(codefile("tests/test_protocol.py -- тесты протокола", "tests/test_protocol.py"))
    blocks.append(codefile("tests/test_integration.py -- интеграционные тесты", "tests/test_integration.py"))

    # ------------------------------------------------------------------
    # 4. результаты запусков
    # ------------------------------------------------------------------
    blocks.append(heading("4. Результаты выполнения (реальный консольный вывод)"))
    blocks.append(
        paragraph(
            "Все приведённые ниже файлы созданы скриптом run_demo.py, который запускает "
            "server.py через subprocess.Popen, дожидается готовности порта 5509, запускает "
            "клиентов с подготовленным stdin и сохраняет объединённый вывод процессов. Вывод не "
            "редактировался: это фактический результат выполнения программ.",
        )
    )
    blocks.append(
        outputfile(
            "Результат выполнения: TCP-сервер и TCP-клиент (успешные команды, ошибки, тайм-аут)",
            "server_client.txt",
        )
    )
    blocks.append(
        paragraph(
            "В файле server_client.txt показаны: ситуация «сервер недоступен» (порт без слушателя), "
            "запуск сервера, 22 запроса пакетного клиента (в том числе average_grade, create, update, "
            "delete, groups), ошибки «объект не найден», «неизвестная команда», «некорректный JSON», "
            "«отсутствуют обязательные поля», «некорректные значения», ситуация тайм-аута "
            "(sleep 3 с при тайм-ауте клиента 1.5 с) и продолжение работы сервера после отключения "
            "клиентов, а также полный журнал сервера.",
        )
    )
    blocks.append(
        outputfile(
            "Результат выполнения: одновременная работа трёх клиентов",
            "clients3.txt",
        )
    )
    blocks.append(
        outputfile("Результат выполнения: UDP-операция status", "udp.txt")
    )
    blocks.append(outputfile("Результат выполнения: автотесты pytest", "pytest.txt"))

    # ------------------------------------------------------------------
    # 5. пояснения по требованиям
    # ------------------------------------------------------------------
    blocks.append(heading("5. Пояснения по требованиям методички"))
    blocks.append(
        label(
            "Архитектура (этапы 1-4)",
            "Цепочка вызовов: Client -> TCP -> Server -> Service -> Repository. Сетевой код server.py "
            "не изменяет коллекцию объектов напрямую: он разбирает запрос и передаёт данные в "
            "StudentService. Хранение реализует StudentRepository (словарь id -> Student, защищённый "
            "RLock); наружу выдаются копии объектов, поэтому сеть не может испортить состояние. "
            "Модели описаны dataclass-классом Student с type hints.",
        )
    )
    blocks.append(
        label(
            "Протокол и границы сообщений (этап 5)",
            "Каждый запрос -- объект с полями command и data, например "
            '{"command": "get", "data": {"id": 1}}. Каждый ответ содержит поле status: '
            '{"status": "ok", "data": ...} при успехе либо {"status": "error", "error": ..., '
            '"code": ...} при ошибке. '
            "Сообщения разделяются символом перевода строки (newline-delimited JSON). TCP передаёт "
            "поток байтов, поэтому границы восстанавливает класс LineBuffer в protocol.py: он "
            "накапливает данные из recv() и выдаёт только целые строки. Тест "
            "test_line_buffer_splits_stream_into_messages подаёт сообщение по частям.",
        )
    )
    blocks.append(
        label(
            "Многопользовательский сервер (этап 6)",
            "Сервер создаёт socket(AF_INET, SOCK_STREAM), вызывает bind() с SO_REUSEADDR и listen(16). "
            "Цикл accept() передаёт каждую сессию в ThreadPoolExecutor(max_workers=10), поэтому "
            "клиенты обслуживаются независимо и одновременно. Сервер не завершается после "
            "отключения клиента: это видно в demo/server_client.txt (после завершения всех клиентов "
            "новый клиент успешно получает статус) и в demo/clients3.txt.",
        )
    )
    blocks.append(
        label(
            "Клиент с меню (этап 7)",
            "client.py поддерживает интерактивное меню из девяти пунктов (list, get, create, update, "
            "delete, average_grade, groups, status, демонстрация тайм-аута) и пакетный режим --batch, "
            "в котором построчные JSON-запросы читаются из stdin. Пункт 9 меню создаёт отдельного "
            "клиента с socket.settimeout(1.0) и усыпляет сервер на 3 секунды.",
        )
    )
    blocks.append(
        label(
            "Обработка ошибок (этап 8)",
            "Обработаны все требуемые ситуации: сервер недоступен (ServerUnavailableError при "
            "ConnectionRefusedError/OSError), разрыв соединения (ConnectionResetError и пустой recv), "
            "неизвестная команда (unknown_command), некорректный JSON (protocol_error), отсутствие "
            "обязательных полей (validation_error), объект не найден (not_found), некорректные "
            "значения -- оценка вне 2..5, пустое ФИО, неверный e-mail, недопустимый статус "
            "(validation_error), тайм-аут (RemoteTimeoutError). Базовое собственное исключение -- "
            "AppError, отдельно определён class ProtocolError(AppError).",
        )
    )
    blocks.append(
        label(
            "Тайм-ауты (этап 9)",
            "Клиент вызывает socket.settimeout(timeout) (по умолчанию 5 с, в демонстрации 1.5 с), "
            "сервер -- connection.settimeout(30 с), а сокет accept -- 0.5 с, чтобы цикл мог "
            "проверять флаг остановки. Тайм-аут не даёт программе зависнуть навсегда при молчащем "
            "партнёре, позволяет вовремя освободить ресурсы и сообщить пользователю о проблеме. "
            "После тайм-аута клиент помечает соединение как «требующее переподключения» и "
            "восстанавливает его при следующей команде -- это показано в demo/server_client.txt "
            "запросом ping сразу после сработавшего тайм-аута.",
        )
    )
    blocks.append(
        label(
            "Логирование (этап 10)",
            "Модуль logging настроен через basicConfig с форматом «дата время уровень [поток] "
            "сообщение». Логируются: запуск сервера и UDP-сервера, загрузка демо-данных, "
            "подключение и отключение каждого клиента, получение команды, успешное выполнение, "
            "ошибочные запросы (ERROR), предупреждения о тайм-ауте и команде sleep (WARNING), "
            "а также исключения через LOGGER.exception. Журнал сервера включён в demo/*.txt.",
        )
    )
    blocks.append(
        label(
            "Тестирование (этап 12)",
            "Написано 28 автотестов pytest: 6 тестов Repository (add/get/get_all/update/delete, "
            "конфликт id, ошибки валидации), 9 тестов Service (создание, обязательные поля, "
            "некорректные оценки, average_grade, отсутствующий студент, частичное изменение, "
            "фильтрация, удаление и статус, сводка по группам), 7 тестов протокола (кодирование и "
            "декодирование, некорректный JSON, отсутствие command, неверный тип data, формат "
            "ответа, разбор потока байтов) и 5 интеграционных тестов Client -> TCP -> Server -> "
            "Service -> Repository (полный цикл CRUD, обработка ошибок, три клиента одновременно, "
            "тайм-аут, UDP-команда status). Команда запуска: python -m pytest tests -v.",
        )
    )
    blocks.append(
        label(
            "UDP-операция (этап 20)",
            "По UDP реализована команда status: она возвращает количество студентов, список групп, "
            "средний балл, время работы сервера и число завершённых команд. Отсутствие "
            "гарантированной доставки здесь допустимо, потому что запрос статуса идемпотентен: он "
            "ничего не меняет в хранилище, а потеря датаграммы приводит лишь к необходимости "
            "повторить запрос. При этом UDP не тратит время на установление соединения и "
            "подтверждения, что удобно для быстрых служебных проверок и мониторинга. Для операций, "
            "изменяющих данные (create, update, delete), используется TCP, где доставка и порядок "
            "гарантированы. Попытка выполнить по UDP команду delete возвращает ошибку unknown_command "
            "-- это также зафиксировано в demo/udp.txt.",
        )
    )
    blocks.append(
        label(
            "Одновременная работа клиентов (этап 11)",
            "В demo/clients3.txt три процесса client.py запускаются практически одновременно. "
            "Каждый клиент занят около 1.07 с (внутри есть команда sleep 1 с), а фактическое время "
            "демонстрации -- 1.07 с, то есть суммарные 3.20 с работы были выполнены параллельно. "
            "В журнале сервера видно переплетение строк из потоков client_0, client_1 и client_2, "
            "а клиент-наблюдатель после завершения всех трёх видит общее хранилище (4 студента).",
        )
    )

    # ------------------------------------------------------------------
    # 6. вывод
    # ------------------------------------------------------------------
    blocks.append(heading("Вывод"))
    blocks.append(
        paragraph(
            "В ходе работы разработано клиент-серверное приложение на языке Python для предметной "
            "области «Университет» (вариант 4) с разделением на слои models -- repository -- service "
            "-- protocol -- server -- client. Реализован собственный JSON-протокол с разделителем "
            "«перевод строки» и десятью командами, включая обязательные list, get, create, update, "
            "delete и специализированную average_grade. TCP-сервер на базе стандартного модуля "
            "socket обслуживает несколько клиентов одновременно с помощью ThreadPoolExecutor, "
            "продолжает работу после отключения клиента, использует тайм-ауты и подробное "
            "логирование. Реализованы обработка восьми классов ошибок и собственные исключения. "
            "Дополнительно операция status вынесена на UDP с обоснованием допустимости недоставки "
            "датаграмм. Написано 28 автотестов pytest, все проходят успешно; демонстрации "
            "зафиксированы в реальных файлах demo/server_client.txt, demo/clients3.txt, "
            "demo/udp.txt и demo/pytest.txt.",
        )
    )
    blocks.append(
        paragraph(
            "Ограничения работы: данные хранятся только в памяти процесса и теряются при остановке "
            "сервера (это соответствует условию лабораторной работы); служебная команда sleep "
            "существует исключительно для демонстрации тайм-аута и не является частью предметной "
            "логики; UDP-сервер запускается в том же процессе, что и TCP-сервер, чтобы обе операции "
            "работали с одним хранилищем.",
        )
    )
    return blocks


def main() -> int:
    report: Dict[str, Any] = {
        "practice": 9,
        "title": "ПРАКТИЧЕСКАЯ РАБОТА №9",
        "subtitle": (
            "Сетевое взаимодействие в Python: TCP/UDP, клиент-серверная архитектура "
            "и прикладные протоколы"
        ),
        "goal": (
            "Изучить клиент-серверную архитектуру и сетевое взаимодействие в Python: реализовать "
            "многопоточный TCP-сервер и клиент на стандартных сокетах, собственный JSON-протокол "
            "с разделением сообщений по переводу строки, обработку ошибок и тайм-аутов, "
            "логирование и автотесты. Дополнительно закрепить разделение сетевого кода и "
            "бизнес-логики на примере предметной области «Университет» и продемонстрировать "
            "одну операцию через UDP."
        ),
        "blocks": build_blocks(),
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    with open(REPORT_PATH, "r", encoding="utf-8") as handle:
        loaded = json.load(handle)

    assert loaded["practice"] == 9
    assert loaded["blocks"], "отчёт не содержит блоков"

    missing: List[str] = []
    checked = 0
    for block in loaded["blocks"]:
        path = block.get("path")
        if path:
            checked += 1
            if not (WORKSPACE / path).exists():
                missing.append(path)

    print(f"report.json создан: {REPORT_PATH}")
    print(f"блоков: {len(loaded['blocks'])}; проверено путей: {checked}; отсутствует: {len(missing)}")
    if missing:
        for path in missing:
            print("  НЕТ ФАЙЛА:", path)
        return 1
    print("json.load: успешно; все указанные в блоках файлы существуют")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
