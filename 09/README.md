# Лабораторная работа №9. Сетевое взаимодействие в Python (вариант 4)

Предметная область: **Университет**, основная сущность -- **Student**.
Специализированная команда -- **average_grade** (средний балл студента).

## Состав

| Файл | Назначение |
|------|------------|
| models.py | сущность Student (id, name, group, grades, email, year, status) |
| exceptions.py | собственные исключения (AppError, ProtocolError, NotFoundError ...) |
| repository.py | хранение в памяти (dict + RLock), add/get/get_all/update/delete |
| service.py | бизнес-логика: CRUD, фильтрация, average_grade, groups, status |
| protocol.py | JSON-протокол, newline-delimited JSON, LineBuffer |
| server.py | TCP-сервер (socket, ThreadPoolExecutor) + UDP-сервер (status) |
| client.py | TCP-клиент с консольным меню и пакетным режимом |
| udp_client.py | UDP-клиент операции status |
| run_demo.py | автоматическая демонстрация, пишет файлы в demo/ |
| tests/ | 28 автотестов pytest |

## Запуск

    python server.py --port 5509 --udp-port 5509 --seed
    python client.py --port 5509                  # консольное меню
    python udp_client.py --port 5509              # статус по UDP
    python -m pytest tests -v                     # автотесты
    python run_demo.py                            # все демонстрации в demo/*.txt

## Протокол

Запрос: {"command": "get", "data": {"id": 1}} + "\n"
Ответ:  {"status": "ok", "data": {...}} или {"status": "error", "error": "...", "code": "..."}

Команды: list, get, create, update, delete, average_grade, groups, status, ping.
