def add_book(books):
    title = input("Введите название книги: ")
    author = input("Введите автора: ")
    year = int(input("Введите год издания: "))
    pages = int(input("Введите количество страниц: "))

    book = {
        "title": title,
        "author": author,
        "year": year,
        "pages": pages
    }
    books.append(book)
    print("Книга успешно добавлена!")


def show_books(books):
    if not books:
        print("Список книг пуст.")
        return
    print("\n--- Список всех книг ---")
    for i, b in enumerate(books, 1):
        print(f"{i}. '{b['title']}' — {b['author']} ({b['year']} г.), {b['pages']} стр.")


def search_by_author(books):
    author_query = input("Введите имя автора для поиска: ").strip().lower()
    found = [b for b in books if author_query in b['author'].lower()]
    show_books(found)


def filter_by_year(books):
    year_limit = int(input("Показать книги, изданные после года: "))
    filtered = [b for b in books if b['year'] > year_limit]
    show_books(filtered)


def show_stats(books):
    if not books:
        print("Нет данных для статистики.")
        return
    total_pages = sum(b['pages'] for b in books)
    avg_pages = total_pages / len(books)
    max_book = max(books, key=lambda x: x['pages'])

    print(f"\n--- Статистика ---")
    print(f"Средняя толщина книги: {avg_pages:.1f} стр.")
    print(f"Самая объёмная книга: '{max_book['title']}' ({max_book['pages']} стр.)")


def show_unique_authors(books):
    authors = {b['author'] for b in books}
    print("\nУникальные авторы в базе:")
    for a in authors:
        print(f"- {a}")


def sort_books(books):
    sorted_list = sorted(books, key=lambda x: x['pages'], reverse=True)
    print("\nКниги, отсортированные по убыванию количества страниц:")
    show_books(sorted_list)


def main():
    books = []
    while True:
        print("\n===== МЕНЮ =====")
        print("1. Добавить книгу")
        print("2. Показать все книги")
        print("3. Поиск по автору")
        print("4. Фильтрация по году издания")
        print("5. Сортировка по страницам")
        print("6. Показать статистику")
        print("7. Показать уникальных авторов")
        print("0. Выход")

        choice = input("Выберите пункт: ")

        if choice == "1":
            add_book(books)
        elif choice == "2":
            show_books(books)
        elif choice == "3":
            search_by_author(books)
        elif choice == "4":
            filter_by_year(books)
        elif choice == "5":
            sort_books(books)
        elif choice == "6":
            show_stats(books)
        elif choice == "7":
            show_unique_authors(books)
        elif choice == "0":
            print("Завершение работы.")
            break
        else:
            print("Неверный ввод, повторите attempt.")


if __name__ == "__main__":
    main()