"""Запускает pytest и сохраняет реальный вывод в demo/pytest.txt."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "demo" / "pytest.txt"
PYTHON = sys.executable


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass

    env = os.environ.copy()
    env["CACHE_BACKEND"] = "memory"
    env["DATABASE_URL"] = "sqlite:///./test_movies.db"
    env["LOG_LEVEL"] = "WARNING"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    command = [PYTHON, "-m", "pytest", "tests", "-v", "--no-header", "-p", "no:cacheprovider"]
    process = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = process.stdout + process.stderr
    OUT.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "Запуск: python -m pytest tests -v\n"
        "Рабочий каталог: work/practice14\n"
        f"Код возврата pytest: {process.returncode}\n"
        + "=" * 78
        + "\n\n"
    )
    OUT.write_text(header + output, encoding="utf-8")
    print(output)
    print(f"Код возврата: {process.returncode}. Сохранено в {OUT}")


if __name__ == "__main__":
    main()
