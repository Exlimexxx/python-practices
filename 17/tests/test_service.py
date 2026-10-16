import pytest
from database.repository import CinemaRepository
from services.cinema import CinemaService


@pytest.fixture
def service(tmp_path):
    repo = CinemaRepository(tmp_path / "test.db", seed=True)
    yield CinemaService(repo)
    repo.close()


def test_seed_contains_more_than_twenty_records(service):
    assert len(service.movies()) >= 10
    assert len(service.schedule()) >= 8


def test_list_movies_returns_genre(service):
    assert all("genre" in movie for movie in service.movies())


def test_search_is_case_insensitive(service):
    result = service.search("КОСМИЧЕСКОЕ")
    assert result and result[0]["title"] == "Космическое путешествие"


def test_add_movie(service):
    movie_id = service.add_movie("Новый фильм", "Драма", 100, 7.5)
    assert service.movie(movie_id)["title"] == "Новый фильм"


def test_add_movie_rejects_empty_title(service):
    with pytest.raises(ValueError, match="Название"):
        service.add_movie(" ", "Драма", 100, 7.5)


def test_add_movie_rejects_rating_out_of_range(service):
    with pytest.raises(ValueError, match="Рейтинг"):
        service.add_movie("Неверный рейтинг", "Драма", 100, 11)


def test_update_movie(service):
    movie_id = service.add_movie("Черновик", "Драма", 90, 6.0)
    service.update_movie(movie_id, "Обновлённый фильм", "Комедия", 95, 7.1)
    assert service.movie(movie_id)["title"] == "Обновлённый фильм"


def test_update_missing_movie_raises(service):
    with pytest.raises(LookupError):
        service.update_movie(9999, "Нет", "Драма", 90, 6)


def test_delete_unreferenced_movie(service):
    movie_id = service.add_movie("К удалению", "Драма", 90, 6)
    service.delete_movie(movie_id)
    with pytest.raises(LookupError):
        service.movie(movie_id)


def test_delete_movie_with_screening_is_rejected(service):
    with pytest.raises(ValueError, match="сеансы"):
        service.delete_movie(1)


def test_book_ticket(service):
    ticket_id = service.book(1, 2, 2, 222)
    assert ticket_id > 1


def test_double_booking_is_rejected(service):
    service.book(2, 2, 2, 222)
    with pytest.raises(ValueError, match="уже забронировано"):
        service.book(2, 2, 2, 333)


def test_invalid_seat_is_rejected(service):
    with pytest.raises(ValueError, match="места"):
        service.book(1, 1, 999, 222)


def test_cancel_ticket_only_by_owner(service):
    ticket_id = service.book(3, 2, 3, 222)
    with pytest.raises(LookupError):
        service.cancel(ticket_id, 333)
    service.cancel(ticket_id, 222)


def test_missing_screening_is_rejected(service):
    with pytest.raises(ValueError, match="Сеанс"):
        service.book(9999, 1, 1, 22)
