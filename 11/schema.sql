-- ============================================================
--  Практическая работа №11, вариант 4. Предметная область: «Кинотеатр».
--  СУБД: SQLite (методичка допускает SQLite в основной части работы).
--  В базе 6 таблиц, связи 1:N и N:M, ограничения
--  PRIMARY KEY / FOREIGN KEY / NOT NULL / UNIQUE / CHECK,
--  6 индексов для ускорения типовых запросов.
-- ============================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS ticket_sales;
DROP TABLE IF EXISTS movie_genres;
DROP TABLE IF EXISTS screenings;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS halls;

-- Основная сущность: фильм.
CREATE TABLE movies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,   -- PRIMARY KEY
    title       TEXT    NOT NULL UNIQUE,             -- NOT NULL + UNIQUE
    duration    INTEGER NOT NULL CHECK (duration > 0),
    rating      REAL    NOT NULL DEFAULT 0.0 CHECK (rating >= 0.0 AND rating <= 10.0),
    poster_path TEXT    NOT NULL,                    -- путь к постеру, который раздаёт CDN
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Кинозалы (справочник).
CREATE TABLE halls (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL UNIQUE,
    capacity INTEGER NOT NULL CHECK (capacity > 0)
);

-- Сеансы: связь 1:N (один фильм — много сеансов, один зал — много сеансов).
CREATE TABLE screenings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id     INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    hall_id      INTEGER NOT NULL REFERENCES halls(id)  ON DELETE RESTRICT,
    start_time   TEXT    NOT NULL,
    price        REAL    NOT NULL CHECK (price > 0),
    tickets_sold INTEGER NOT NULL DEFAULT 0 CHECK (tickets_sold >= 0),
    UNIQUE (hall_id, start_time)   -- в одном зале не может быть двух сеансов одновременно
);

-- Жанры (справочник).
CREATE TABLE genres (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL UNIQUE
);

-- Связь N:M «фильмы — жанры» через промежуточную таблицу.
CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- Продажи билетов: используется в транзакции продажи.
CREATE TABLE ticket_sales (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    screening_id INTEGER NOT NULL REFERENCES screenings(id) ON DELETE CASCADE,
    tickets      INTEGER NOT NULL CHECK (tickets > 0),
    total_price  REAL    NOT NULL CHECK (total_price > 0),
    sold_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
--  Индексы (по заданию — минимум 2, здесь 6).
-- ============================================================
-- 1) JOIN movies<->screenings и выборка «сеансы одного фильма».
CREATE INDEX idx_screenings_movie ON screenings(movie_id);
-- 2) WHERE/ORDER BY по дате и времени начала (афиша, расписание).
CREATE INDEX idx_screenings_start ON screenings(start_time);
-- 3) Отчёты и группировка по залам.
CREATE INDEX idx_screenings_hall ON screenings(hall_id);
-- 4) Топ фильмов по рейтингу (ORDER BY rating DESC).
CREATE INDEX idx_movies_rating ON movies(rating DESC);
-- 5) Подбор фильмов по жанру и построение рекомендаций (N:M).
CREATE INDEX idx_movie_genres_genre ON movie_genres(genre_id);
-- 6) Подсчёт выручки и история продаж по сеансу.
CREATE INDEX idx_sales_screening ON ticket_sales(screening_id);
