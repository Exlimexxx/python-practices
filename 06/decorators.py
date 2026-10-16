import time
from functools import wraps
from typing import Callable, Any


def log_call(func: Callable) -> Callable:
    """Декоратор №1: Журналирование вызова функции, параметров и результата."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        print(f"[LOG] Вызов функции '{func.__name__}' с аргументами: ({signature})")

        result = func(*args, **kwargs)
        print(f"[LOG] Функция '{func.__name__}' вернула: {result!r}")
        return result

    return wrapper


def measure_time(func: Callable) -> Callable:
    """Декоратор №2: Измерение времени выполнения функции."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time
        print(f"[PERFORMANCE] '{func.__name__}' выполнена за {elapsed:.6f} сек.")
        return result

    return wrapper


def repeat(count: int = 2) -> Callable:
    """Декоратор №3 (с параметром): Повторение выполнения функции N раз."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = None
            print(f"[REPEAT] Выполнение функции '{func.__name__}' {count} раз(а):")
            for i in range(1, count + 1):
                print(f"  --- Итерация {i}/{count} ---")
                result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator