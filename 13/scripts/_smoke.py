import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.main import build_app
service, info = build_app()
print(info)
print(service.get_movie(1).summary())
print("total:", service.statistics()["total"])
