class Book:
    """Базовый класс книги."""
    def __init__(self, title: str, author: str, year: int, pages_count: int, rating: float):
        self.title = title
        self.author = author
        self.year = year
        self.pages_count = pages_count
        self.rating = rating

    def __str__(self):
        return f"'{self.title}' — {self.author} ({self.year} г., {self.pages_count} стр., рейтинг: {self.rating})"


class PrintedBook(Book):
    """Печатная книга."""
    def __init__(self, title: str, author: str, year: int, pages_count: int, rating: float, cover_type: str):
        super().__init__(title, author, year, pages_count, rating)
        self.cover_type = cover_type  # Твердый / Мягкий переплет

    def __str__(self):
        return super().__str__() + f" [Печатная, обложка: {self.cover_type}]"


class EBook(Book):
    """Электронная книга."""
    def __init__(self, title: str, author: str, year: int, pages_count: int, rating: float, file_size_mb: float):
        super().__init__(title, author, year, pages_count, rating)
        self.file_size_mb = file_size_mb

    def __str__(self):
        return super().__str__() + f" [Электронная, размер: {self.file_size_mb} МБ]"