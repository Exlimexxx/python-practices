import json
import csv
import os

def save_to_json(filepath: str, data: list):
    """Сохраняет список словарей в файл JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_from_json(filepath: str) -> list:
    """Загружает данные из JSON. Если файла нет, возвращает пустой список."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def export_to_csv(filepath: str, books: list):
    """Экспортирует список объектов Book в CSV-файл."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ISBN", "Название", "Автор", "Год", "Страниц"])
        for book in books:
            writer.writerow([book.isbn, book.title, book.author, book.year, book.pages_count])