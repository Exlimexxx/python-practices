from unittest.mock import Mock, patch

import pytest
from cinema import (CinemaRepository, CinemaService, Movie, NotFoundError,
                    SeatAlreadyTakenError, ValidationError)


@pytest.fixture
def repo(tmp_path):
    item = CinemaRepository(tmp_path / "cinema_test.sqlite")
    yield item
    item.close()


@pytest.fixture
def service(repo):
    return CinemaService(repo)


@pytest.fixture
def movie(service):
    return service.add_movie("Матрица тестовая", "Фантастика", 136, 8.7)


def create_screening(service, movie):
    return service.create_screening(movie.id, "Зал 1", "2026-11-01 18:00", 8, 10)


def test_create_movie(service):
    item = service.add_movie("Альфа", "Драма", 100, 7.0)
    assert item.id > 0 and item.title == "Альфа"


def test_get_movie(service, movie):
    assert service.get_movie(movie.id) == movie


def test_list_movies(service, movie):
    assert len(service.list_movies()) == 1


def test_update_movie(service, movie):
    service.update_movie(movie.id, {"rating": 9.1})
    assert service.get_movie(movie.id).rating == pytest.approx(9.1)


def test_delete_movie(service, movie):
    service.delete_movie(movie.id)
    assert service.list_movies() == []


def test_search_by_title_and_genre(service, movie):
    assert service.search_movies("МАТРИЦА", "фантастика")[0].id == movie.id


def test_screening_creation(service, movie):
    screening = create_screening(service, movie)
    assert screening.movie_id == movie.id


def test_booking_ticket(service, movie):
    screening = create_screening(service, movie)
    ticket = service.book_ticket(screening.id, 2, 5, "Иван Иванов")
    assert ticket.seat_no == 5


def test_cancel_ticket(service, movie):
    screening = create_screening(service, movie)
    ticket = service.book_ticket(screening.id, 2, 5, "Иван Иванов")
    service.cancel_ticket(ticket.id)
    assert repo_ticket_missing(service, ticket.id)


def repo_ticket_missing(service, ticket_id):
    return service.repository.get_ticket(ticket_id) is None


def test_double_booking_is_forbidden(service, movie):
    screening = create_screening(service, movie)
    service.book_ticket(screening.id, 1, 1, "А")
    with pytest.raises(SeatAlreadyTakenError):
        service.book_ticket(screening.id, 1, 1, "Б")


@pytest.mark.parametrize("duration", [0, -1, 401])
def test_duration_boundaries(service, duration):
    with pytest.raises(ValidationError):
        service.add_movie("Некорректная длительность", "Драма", duration, 5)


@pytest.mark.parametrize("rating", [-0.1, 10.1])
def test_rating_boundaries(service, rating):
    with pytest.raises(ValidationError):
        service.add_movie("Некорректный рейтинг", "Драма", 100, rating)


@pytest.mark.parametrize("row,seat", [(0, 1), (1, 0), (9, 1), (1, 11)])
def test_seat_boundaries(service, movie, row, seat):
    screening = create_screening(service, movie)
    with pytest.raises(ValidationError):
        service.book_ticket(screening.id, row, seat, "Покупатель")


def test_empty_title_is_invalid(service):
    with pytest.raises(ValidationError, match="Название"):
        service.add_movie(" ", "Драма", 90, 6)


def test_missing_movie_is_not_found(service):
    with pytest.raises(NotFoundError):
        service.get_movie(999)


def test_invalid_id_is_rejected(service):
    with pytest.raises(ValidationError):
        service.get_movie(0)


def test_missing_screening_movie_is_rejected(service):
    with pytest.raises(NotFoundError):
        service.create_screening(999, "Зал", "2026-11-01 18:00")


def test_mock_repository_list_is_called_once():
    repository = Mock()
    repository.list_movies.return_value = [Movie(1, "Тест", "Драма", 90, 7.0)]
    service = CinemaService(repository)
    assert service.list_movies()[0].title == "Тест"
    repository.list_movies.assert_called_once_with()


def test_mock_not_found_propagates():
    repository = Mock()
    repository.get_movie.return_value = None
    with pytest.raises(NotFoundError):
        CinemaService(repository).get_movie(12)
    repository.get_movie.assert_called_once_with(12)


def test_mock_repository_used_for_update():
    repository = Mock()
    repository.update_movie.return_value = True
    CinemaService(repository).update_movie(4, {"rating": 8.0})
    repository.update_movie.assert_called_once_with(4, {"rating": 8.0})


def test_mock_invalid_value_does_not_write():
    repository = Mock()
    with pytest.raises(ValidationError):
        CinemaService(repository).add_movie("X", "Драма", 999, 8)
    repository.add_movie.assert_not_called()


def test_mock_search_parameters_are_forwarded():
    repository = Mock()
    repository.search_movies.return_value = []
    CinemaService(repository).search_movies("Матрица", "Фантастика")
    repository.search_movies.assert_called_once_with("Матрица", "Фантастика")


def test_patch_repository_add_movie_return_value():
    repository = Mock()
    fake = Movie(77, "Подмена", "Комедия", 90, 6.5)
    with patch.object(repository, "add_movie", return_value=fake) as add_mock:
        service = CinemaService(repository)
        assert service.add_movie("Подмена", "Комедия", 90, 6.5) == fake
        add_mock.assert_called_once()


def test_integration_crud_sqlite(service):
    movie = service.add_movie("Интеграция", "Драма", 90, 6.5)
    service.update_movie(movie.id, {"title": "Интеграция 2"})
    assert service.get_movie(movie.id).title == "Интеграция 2"
    service.delete_movie(movie.id)
    assert service.list_movies() == []


def test_integration_booking_then_cancel(service, movie):
    screening = create_screening(service, movie)
    ticket = service.book_ticket(screening.id, 3, 4, "Тест")
    assert service.repository.get_ticket(ticket.id) is not None
    service.cancel_ticket(ticket.id)
    assert service.repository.get_ticket(ticket.id) is None


def test_delete_movie_with_screening_is_rejected(service, movie):
    create_screening(service, movie)
    with pytest.raises(ValueError, match="сеансами"):
        service.delete_movie(movie.id)
