import os
from models import Book
from services import BookCatalog
from storage import load_from_json, save_to_json, export_to_csv
from exceptions import DuplicateISBNError, BookNotFoundError

JSON_PATH = "data.json"
CSV_PATH = "data.csv"


def print_menu():
    print("\n=== ЭЛЕКТРОННЫЙ КАТАЛОГ КНИГ ===")
    print("1. Показать все книги")
    print("2. Добавить книгу")
    print("3. Найти книгу по ISBN")
    print("4. Найти книги по автору")
    print("5. Удалить книгу по ISBN")
    print("6. Отсортировать книги")
    print("7. Сохранить в JSON")
    print("8. Экспортировать в CSV")
    print("0. Выход")


def main():
    catalog = BookCatalog()

    # Загрузка данных при запуске
    raw_data = load_from_json(JSON_PATH)
    for item in raw_data:
        try:
            catalog.add_book(Book.from_dict(item))
        except DuplicateISBNError:
            pass

    while True:
        print_menu()
        choice = input("Выберите пункт меню: ").strip()

        if choice == "1":
            if not catalog.books:
                print("Каталог пуст.")
            else:
                for b in catalog.books:
                    print(b)

        elif choice == "2":
            try:
                isbn = input("Введите ISBN: ").strip()
                title = input("Введите название: ").strip()
                author = input("Введите автора: ").strip()
                year = int(input("Введите год издания: "))
                pages = int(input("Введите кол-во страниц: "))

                new_book = Book(isbn, title, author, year, pages)
                catalog.add_book(new_book)
                print("Книга успешно добавлена!")
            except ValueError:
                print("Ошибка: год и количество страниц должны быть целыми числами!")
            except DuplicateISBNError as e:
                print(f"Ошибка бизнес-логики: {e}")

        elif choice == "3":
            isbn = input("Введите ISBN для поиска: ").strip()
            try:
                book = catalog.find_by_isbn(isbn)
                print("Найдена книга:", book)
            except BookNotFoundError as e:
                print(e)

        elif choice == "4":
            author = input("Введите имя автора (или часть): ").strip()
            found = catalog.find_by_author(author)
            if found:
                for b in found:
                    print(b)
            else:
                print("Книги этого автора не найдены.")

        elif choice == "5":
            isbn = input("Введите ISBN книги для удаления: ").strip()
            try:
                catalog.delete_by_isbn(isbn)
                print("Книга успешно удалена!")
            except BookNotFoundError as e:
                print(e)

        elif choice == "6":
            print("1 - по название, 2 - по году, 3 - по страницам")
            s_choice = input("Вариант сортировки: ").strip()
            if s_choice == "2":
                catalog.sort_books("year")
            elif s_choice == "3":
                catalog.sort_books("pages")
            else:
                catalog.sort_books("title")
            print("Каталог отсортирован!")

        elif choice == "7":
            data = [b.to_dict() for b in catalog.books]
            save_to_json(JSON_PATH, data)
            print(f"Данные сохранены в {JSON_PATH}")

        elif choice == "8":
            export_to_csv(CSV_PATH, catalog.books)
            print(f"Данные экспортированы в {CSV_PATH}")

        elif choice == "0":
            data = [b.to_dict() for b in catalog.books]
            save_to_json(JSON_PATH, data)
            print("Данные сохранены. До свидания!")
            break
        else:
            print("Некорректный пункт меню!")


if __name__ == "__main__":
    main()