from models import Book
from exceptions import DuplicateISBNError, BookNotFoundError

class BookCatalog:
    def __init__(self):
        self.books = []

    def add_book(self, book: Book):
        """Добавляет книгу, проверяя уникальность ISBN."""
        for b in self.books:
            if b.isbn == book.isbn:
                raise DuplicateISBNError(f"Книга с ISBN {book.isbn} уже существует!")
        self.books.append(book)

    def find_by_isbn(self, isbn: str) -> Book:
        """Ищет книгу по ISBN."""
        for b in self.books:
            if b.isbn == isbn:
                return b
        raise BookNotFoundError(f"Книга с ISBN '{isbn}' не найдена.")

    def find_by_author(self, author: str) -> list:
        """Возвращает список книг определенного автора (без учета регистра)."""
        result = []
        for b in self.books:
            if author.lower() in b.author.lower():
                result.append(b)
        return result

    def delete_by_isbn(self, isbn: str):
        """Удаляет книгу по ISBN."""
        book = self.find_by_isbn(isbn)
        self.books.remove(book)

    def sort_books(self, key_field: str = "title"):
        """Сортирует список книг по выбранному полю."""
        if key_field == "year":
            self.books.sort(key=lambda b: b.year)
        elif key_field == "pages":
            self.books.sort(key=lambda b: b.pages_count)
        else:
            self.books.sort(key=lambda b: b.title.lower())