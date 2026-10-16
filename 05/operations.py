from functools import reduce

def filter_books(books, predicate):
    """Функция высшего порядка: фильтрация элементов по предикату."""
    return list(filter(predicate, books))

def transform_books(books, mapper):
    """Функция высшего порядка: трансформация с использованием map()."""
    return list(map(mapper, books))

def sort_books_by_pages(books):
    """Сортировка с использованием sorted() и lambda-ключа."""
    return sorted(books, key=lambda b: b.pages_count, reverse=True)

def find_largest_book(books):
    """Поиск самой большой книги через reduce()."""
    if not books:
        return None
    return reduce(lambda a, b: a if a.pages_count > b.pages_count else b, books)

def check_author_exists(books, author_name: str) -> bool:
    """Проверка наличия книг автора через any()."""
    return any(author_name.lower() in b.author.lower() for b in books)

def get_titles_comprehension(books) -> list:
    """Пример List Comprehension."""
    return [b.title for b in books]