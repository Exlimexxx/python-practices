class DuplicateISBNError(Exception):
    """Исключение, возникающее при попытке добавить книгу с уже существующим ISBN."""
    pass


class BookNotFoundError(Exception):
    """Исключение, возникающее, если книга не найдена в каталоге."""
    pass