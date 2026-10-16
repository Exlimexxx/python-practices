"""Корневой conftest: делает пакет app импортируемым при запуске pytest."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
