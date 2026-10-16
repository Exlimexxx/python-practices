"""Общая настройка pytest для лабораторной работы №9.

Добавляет каталог проекта в sys.path, чтобы тесты могли импортировать
models, repository, service, protocol, server и client как обычные модули.
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
