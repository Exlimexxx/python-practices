class Book:
    def __init__(self, isbn: str, title: str, author: str, year: int, pages_count: int):
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year
        self.pages_count = pages_count

    def to_dict(self) -> dict:
        """Преобразует объект книги в словарь для сохранения в JSON."""
        return {
            "isbn": self.isbn,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "pages_count": self.pages_count
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Создает объект Book из словаря, прочитанного из JSON."""
        return cls(
            isbn=data["isbn"],
            title=data["title"],
            author=data["author"],
            year=data["year"],
            pages_count=data["pages_count"]
        )

    def __str__(self):
        return f"[{self.isbn}] '{self.title}' — {self.author} ({self.year} г., {self.pages_count} стр.)"