from typing import Protocol, runtime_checkable


@runtime_checkable
class Reportable(Protocol):
    """Протокол для объектов, способных формировать текстовый отчёт."""

    def get_report_data(self) -> str:
        ...


def generate_single_report(item: Reportable) -> str:
    """Функция, принимающая объект через интерфейс Protocol."""
    return f"[ОТЧЁТ ПО ОБЪЕКТУ]: {item.get_report_data()}"