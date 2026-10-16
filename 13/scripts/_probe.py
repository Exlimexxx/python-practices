import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.mongodb import connect_mongo
db, mode, err = connect_mongo()
print("mode", mode, "err", err)
try:
    print("server", db.client.server_info().get("version"))
except Exception as e:
    print("no server_info", e)
coll = db["movie"]
print("count", coll.count_documents({}))
doc = coll.find_one({})
print("sample id", doc.get("_id"), type(doc.get("_id")).__name__, doc.get("title"))
print("collections", db.list_collection_names())
