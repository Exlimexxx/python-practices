def books_by_period_generator(books, start_year: int, end_year: int):
    """Генератор книг, выпущенных в заданный период годов."""
    for book in books:
        if start_year <= book.year <= end_year:
            yield book


class BookIterator:
    """Собственный класс-итератор для последовательного перебора книг."""
    def __init__(self, books):
        self._books = books
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._books):
            raise StopIteration
        book = self._books[self._index]
        self._index += 1
        return book