# Лабораторная работа №20 — контейнеризация сервиса бронирования гостиницы (вариант 4)

1. Скопировать `.env.example` в `.env` и заменить пароль на локальный.
2. Выполнить `docker compose up --build`.
3. Проверить `GET http://localhost:8000/health` и документацию `http://localhost:8000/docs`.
4. Остановить `docker compose down`, снова запустить `docker compose up`: данные сохраняются в volume `hotel_pgdata`.
5. Локально: `python -m pip install -r requirements.txt`, затем `python -m pytest -q`.

`.env` исключён из Git и Docker build context; workflow запускается при `push` и `pull_request`, выполняет Ruff, pytest и сборку образа.
