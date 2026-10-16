import sys
from models import PrintedBook, EBook
from operations import (
    filter_books, transform_books, sort_books_by_pages,
    find_largest_book, check_author_exists, get_titles_comprehension
)
from generators import books_by_period_generator, BookIterator

def init_sample_data():
    return [
        PrintedBook("Война и мир", "Лев Толстой", 1869, 1300, 4.9, "Твердый"),
        EBook("Преступление и наказание", "Фёдор Достоевский", 1866, 670, 4.8, 2.5),
        PrintedBook("Мастер и Маргарита", "Михаил Булгаков", 1967, 480, 4.95, "Твердый"),
        EBook("1984", "Джордж Оруэлл", 1949, 328, 4.7, 1.2),
        PrintedBook("Герой нашего времени", "Михаил Лермонтов", 1840, 224, 4.6, "Мягкий"),
    ]

def demonstrate_lazy_evaluation():
    print("\n--- Демонстрация ленивых вычислений (генератор vs список) ---")
    n = 500_000
    list_res = [x * x for x in range(n)]
    gen_res = (x * x for x in range(n))

    print(f"Размер списка из {n} элементов в памяти: {sys.getsizeof(list_res)} байт")
    print(f"Размер генератора в памяти: {sys.getsizeof(gen_res)} байт")
    print("Вывод: генератор занимает считаные байты, так как вычисляет элементы на лету.")

def print_menu():
    print("\n===== МЕНЮ (ЛАБОРАТОРНАЯ №5) =====")
    print("1. Показать все книги")
    print("2. Отфильтровать книги по рейтингу (> 4.7)")
    print("3. Получить список названий (map)")
    print("4. Отсортировать книги по количеству страниц")
    print("5. Найти самую большую книгу (reduce)")
    print("6. Проверить наличие книг автора (any)")
    print("7. Запустить генератор книг по периоду годов (1850 - 1950)")
    print("8. Продемонстрировать собственный итератор")
    print("9. Показать разницу генератора и списка (память)")
    print("0. Выход")

def main():
    books = init_sample_data()

    while True:
        print_menu()
        choice = input("Выберите пункт: ").strip()

        if choice == "1":
            print("\nСписок книг:")
            for b in books:
                print(b)

        elif choice == "2":
            min_rating = 4.75
            filtered = filter_books(books, lambda b: b.rating >= min_rating)
            print(f"\nКниги с рейтингом >= {min_rating}:")
            for b in filtered:
                print(b)

        elif choice == "3":
            titles_map = transform_books(books, lambda b: b.title.upper())
            titles_comp = get_titles_comprehension(books)
            print("\nНазвания в верхнем регистре (через map):", titles_map)
            print("Названия (через list comprehension):", titles_comp)

        elif choice == "4":
            sorted_b = sort_books_by_pages(books)
            print("\nКниги, отсортированные по убыванию страниц:")
            for b in sorted_b:
                print(b)

        elif choice == "5":
            largest = find_largest_book(books)
            print("\nСамая большая книга:", largest)

        elif choice == "6":
            author = input("Введите имя автора для проверки: ").strip()
            exists = check_author_exists(books, author)
            if exists:
                print(f"Да, книги автора '{author}' есть в каталоге.")
            else:
                print(f"Книг автора '{author}' не найдено.")

        elif choice == "7":
            print("\nКниги, изданные с 1850 по 1950 год (через generator):")
            for b in books_by_period_generator(books, 1850, 1950):
                print(b)

        elif choice == "8":
            print("\nОбход с помощью собственного BookIterator:")
            iterator = BookIterator(books)
            for b in iterator:
                print(b)

        elif choice == "9":
            demonstrate_lazy_evaluation()

        elif choice == "0":
            print("Завершение работы.")
            break
        else:
            print("Неверный ввод.")

if __name__ == "__main__":
    main()