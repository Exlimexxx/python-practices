-- ============================================================
--  Практическая работа №11, вариант 4, «Кинотеатр».
--  19 запросов: SELECT, WHERE, ORDER BY, JOIN, LEFT JOIN, GROUP BY,
--  HAVING, COUNT, AVG, SUM, подзапросы, несколько условий,
--  связь нескольких таблиц, N:M, INSERT, UPDATE, DELETE.
--  Маркер «-- @query <название>» отделяет один запрос от другого,
--  этот файл читает run_queries.py.
-- ============================================================

-- @query 1. SELECT: базовый список фильмов
SELECT id, title, duration, rating
FROM movies
ORDER BY rating DESC;

-- @query 2. WHERE: фильмы с рейтингом не ниже 8.8
SELECT title, rating
FROM movies
WHERE rating >= 8.8
ORDER BY rating DESC;

-- @query 3. ORDER BY + LIMIT: пять самых длинных фильмов
SELECT title, duration
FROM movies
ORDER BY duration DESC
LIMIT 5;

-- @query 4. JOIN (1:N): сеансы с названиями фильмов
SELECT s.id, m.title, s.start_time, s.price
FROM screenings s
JOIN movies m ON m.id = s.movie_id
ORDER BY s.start_time;

-- @query 5. LEFT JOIN: все фильмы и число их сеансов (в т.ч. без сеансов)
SELECT m.title, COUNT(s.id) AS screenings_count
FROM movies m
LEFT JOIN screenings s ON s.movie_id = m.id
GROUP BY m.id
ORDER BY screenings_count ASC, m.title;

-- @query 6. GROUP BY: количество сеансов по залам
SELECT h.name AS hall, COUNT(s.id) AS screenings_count
FROM halls h
LEFT JOIN screenings s ON s.hall_id = h.id
GROUP BY h.id
ORDER BY screenings_count DESC;

-- @query 7. HAVING: жанры, которые встречаются у двух и более фильмов
SELECT g.name AS genre, COUNT(mg.movie_id) AS movies_count
FROM genres g
JOIN movie_genres mg ON mg.genre_id = g.id
GROUP BY g.id
HAVING COUNT(mg.movie_id) >= 2
ORDER BY movies_count DESC;

-- @query 8. COUNT: сколько всего сеансов и продано билетов
SELECT COUNT(*) AS screenings_total, SUM(tickets_sold) AS tickets_total
FROM screenings;

-- @query 9. AVG: средний рейтинг и средняя длительность фильмов
SELECT ROUND(AVG(rating), 2) AS avg_rating, ROUND(AVG(duration), 1) AS avg_duration
FROM movies;

-- @query 10. SUM: выручка по каждому фильму
SELECT m.title, SUM(s.price * s.tickets_sold) AS revenue
FROM movies m
JOIN screenings s ON s.movie_id = m.id
GROUP BY m.id
ORDER BY revenue DESC;

-- @query 11. Подзапрос (скалярный): фильмы с рейтингом выше среднего
SELECT title, rating
FROM movies
WHERE rating > (SELECT AVG(rating) FROM movies)
ORDER BY rating DESC;

-- @query 12. Подзапрос EXISTS: фильмы, у которых нет ни одного сеанса
SELECT m.title
FROM movies m
WHERE NOT EXISTS (SELECT 1 FROM screenings s WHERE s.movie_id = m.id);

-- @query 13. Несколько условий: дорогие вечерние сеансы с нераспроданными местами
SELECT s.id, m.title, s.start_time, s.price, s.tickets_sold
FROM screenings s
JOIN movies m ON m.id = s.movie_id
WHERE s.price >= 500 AND s.start_time LIKE '%19:%' AND s.tickets_sold <= 60
ORDER BY s.price DESC;

-- @query 14. JOIN нескольких таблиц (5 таблиц): фильм + зал + жанр + сеанс
SELECT m.title, h.name AS hall, g.name AS genre, s.start_time
FROM screenings s
JOIN movies m ON m.id = s.movie_id
JOIN halls h ON h.id = s.hall_id
JOIN movie_genres mg ON mg.movie_id = m.id
JOIN genres g ON g.id = mg.genre_id
ORDER BY m.title, g.name;

-- @query 15. Связь N:M: фильмы и все их жанры одной строкой
SELECT m.title, GROUP_CONCAT(g.name, ', ') AS genres
FROM movies m
JOIN movie_genres mg ON mg.movie_id = m.id
JOIN genres g ON g.id = mg.genre_id
GROUP BY m.id
ORDER BY m.title;

-- @query 16. INSERT: добавить новый зал
INSERT INTO halls (name, capacity) VALUES ('Зал 5 «Ночной»', 45);

-- @query 17. UPDATE: поднять цену вечерних сеансов на 10%
UPDATE screenings
SET price = ROUND(price * 1.1, 2)
WHERE start_time LIKE '%19:%';

-- @query 18. DELETE: удалить зал, добавленный запросом 16
DELETE FROM halls WHERE name = 'Зал 5 «Ночной»';

-- @query 19. Проверка после DML: итоговое количество строк в таблицах
SELECT (SELECT COUNT(*) FROM halls) AS halls,
       (SELECT COUNT(*) FROM movies) AS movies,
       (SELECT COUNT(*) FROM screenings) AS screenings,
       (SELECT COUNT(*) FROM ticket_sales) AS ticket_sales;
