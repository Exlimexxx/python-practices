# Практикум по Python (3 курс) — вариант 4

Учебные работы по курсу Python: от базовых конструкций языка до итогового проекта со слоистой
архитектурой, тестами, контейнеризацией и CI. Все работы выполнены по индивидуальному заданию
варианта 4.

Номера папок записаны с ведущим нулём (`01`, `02`, … `09`), чтобы каталоги шли по порядку в
алфавитной сортировке GitHub.

## Содержание

| Папка | Работа | Тема | Листинг |
|---|---|---|---|
| `01` | Лабораторная 1 | Основы программирования: переменные, типы данных, условия, циклы, функции (вариант «Результаты экзамена») | [код](https://github.com/Exlimexxx/python-practices/tree/main/01) |
| `02` | Лабораторная 2 | Коллекции, строки и функции (каталог книг: поиск, фильтрация, статистика) | [код](https://github.com/Exlimexxx/python-practices/tree/main/02) |
| `03` | Лабораторная 3 | Объектно-ориентированное программирование: наследование, полиморфизм, композиция | [код](https://github.com/Exlimexxx/python-practices/tree/main/03) |
| `04` | Лабораторная 4 | Модули, исключения, файлы, JSON и CSV, сохранение состояния между запусками | [код](https://github.com/Exlimexxx/python-practices/tree/main/04) |
| `05` | Лабораторная 5 | Функциональные возможности: лямбды, `map`, `filter`, `reduce`, генераторы, итераторы | [код](https://github.com/Exlimexxx/python-practices/tree/main/05) |
| `06` | Лабораторная 6 | Декораторы, контекстные менеджеры, `dataclass`, `Enum`, `Protocol`, интроспекция | [код](https://github.com/Exlimexxx/python-practices/tree/main/06) |
| `07` | Лабораторная 7 | Принципы SOLID и рефакторинг архитектуры приложения | [код](https://github.com/Exlimexxx/python-practices/tree/main/07) |
| `08` | Лабораторная 8 | Паттерны проектирования: Factory, Strategy, Observer, Repository, Adapter | [код](https://github.com/Exlimexxx/python-practices/tree/main/08) |
| `09` | Лабораторная 9 | Сетевое взаимодействие: TCP/UDP, клиент-сервер, сокеты, JSON-протокол | [код](https://github.com/Exlimexxx/python-practices/tree/main/09) |
| `10` | Лабораторная 10 | HTTP и REST API: клиент-серверное приложение на Flask | [код](https://github.com/Exlimexxx/python-practices/tree/main/10) |
| `11` | Лабораторная 11 | Реляционные и нереляционные БД, транзакции, CDN | [код](https://github.com/Exlimexxx/python-practices/tree/main/11) |
| `12` | Лабораторная 12 | Реляционные БД в Python: SQLAlchemy 2.x ORM | [код](https://github.com/Exlimexxx/python-practices/tree/main/12) |
| `13` | Лабораторная 13 | MongoDB и Redis: документные данные, кэширование cache-aside | [код](https://github.com/Exlimexxx/python-practices/tree/main/13) |
| `14` | Лабораторная 14 | REST API на FastAPI: Pydantic-схемы, валидация, кэш | [код](https://github.com/Exlimexxx/python-practices/tree/main/14) |
| `15` | Лабораторная 15 | Веб-приложение на Flask: фабрика приложений, Blueprint, Jinja2, ORM | [код](https://github.com/Exlimexxx/python-practices/tree/main/15) |
| `16` | Лабораторная 16 | Веб-приложение на Django: модели, FBV/CBV, формы, админка, тесты | [код](https://github.com/Exlimexxx/python-practices/tree/main/16) |
| `17` | Лабораторная 17 | Асинхронный Telegram-бот на aiogram 3: FSM, клавиатуры, SQLite | [код](https://github.com/Exlimexxx/python-practices/tree/main/17) |
| `18` | Лабораторная 18 | Тестирование: pytest, `unittest.mock`, параметризация, фикстуры | [код](https://github.com/Exlimexxx/python-practices/tree/main/18) |
| `19` | Лабораторная 19 | Микросервисная архитектура: API Gateway, события, RabbitMQ, Circuit Breaker | [код](https://github.com/Exlimexxx/python-practices/tree/main/19) |
| `20` | Лабораторная 20 | Контейнеризация и CI/CD: Docker, Docker Compose, GitHub Actions | [код](https://github.com/Exlimexxx/python-practices/tree/main/20) |
| `21` | Лабораторная 21 | Итоговый проект: FastAPI + PostgreSQL, JWT-авторизация, тесты, покрытие, CI | [код](https://github.com/Exlimexxx/python-practices/tree/main/21) |

## Требования

- Python 3.11 или выше (работы проверены на 3.12 и 3.13);
- для работ с веб-фреймворками и базами данных зависимости указаны в `requirements.txt`
  соответствующей папки;
- Docker и Docker Compose — только для работ 19, 20 и 21.

## Запуск работ

Консольные работы (01–08) запускаются из своей папки:

```bash
cd 05
python main.py
```

Работы с тестами и зависимостями:

```bash
cd 21
python -m pip install -r requirements.txt
python -m pytest
```

Серверные работы поднимаются штатной командой своей папки (Flask, FastAPI, Django, aiogram):
подробности — в `README.md` соответствующей работы, где он есть.

## Примечания

- Виртуальные окружения, кэши, базы данных, журналы и файлы `.env` в репозиторий не включены
  (см. `.gitignore`); рядом с настройками лежат только примеры `.env.example`.
- Пароли в тестах (например, в работе 16) — учебные заглушки и не относятся к реальным учётным
  записям.
- Отчётные документы (`.docx`) в репозиторий не добавлены.
