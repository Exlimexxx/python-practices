import sys, pathlib, traceback
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.mongodb import connect_mongo
from app.repository import MongoRepository
from app.seed import build_movies, seed
db, m, e = connect_mongo("mongodb://127.0.0.1:1", "x", timeout_ms=300)
r = MongoRepository(db["movie"])
seed(build_movies(), r)
pipeline = [
    {"$unwind": "$genres"},
    {"$group": {"_id": "$genres", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
]
try:
    out = r.aggregate(pipeline)
    print("OK", out[:3])
except Exception:
    traceback.print_exc()
