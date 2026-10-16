"""Демонстрация измерения производительности MongoDB и Redis."""
from __future__ import annotations

from common import make_service, print_backends, setup_logging, title

setup_logging()


def main() -> None:
    service, info = make_service(reset=True, ttl=60)

    title("6. ИЗМЕРЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ: MONGODB vs REDIS (кэш)")
    print_backends(info)

    rows = service.benchmark((100, 1000, 10000))
    header = f"{'Запросов':>9} | {'MongoDB, с':>12} | {'Mongo, мс/зап':>14} | {'Redis, с':>10} | {'Redis, мс/зап':>14} | {'Ускорение':>9}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['requests']:>9} | {row['mongo_total_sec']:>12.6f} | {row['mongo_avg_ms']:>14.6f} | "
            f"{row['redis_total_sec']:>10.6f} | {row['redis_avg_ms']:>14.6f} | {str(row['speedup']):>9}"
        )
    print()
    print("Вывод: кэш Redis отвечает за единицы микросекунд, тогда как обращение к MongoDB")
    print("включает сетевой обмен и работу хранилища, поэтому на каждые 10 000 запросов")
    print("экономия заметна. Цель — не абсолютная победа Redis, а снижение нагрузки на БД.")


if __name__ == "__main__":
    main()
