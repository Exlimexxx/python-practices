"""Подключение к MongoDB и встроенная in-memory реализация.

Серверы MongoDB в учебной среде могут быть недоступны. Чтобы приложение
оставалось работоспособным (требование п. 31 методички — обработка отсутствия
MongoDB), модуль содержит:

* connect_mongo() — реальное подключение через PyMongo с проверкой ping;
* InMemoryDatabase / InMemoryCollection — резервное документное хранилище
  с API insert/find/update/delete/aggregate и подмножеством операторов запросов
  MongoDB ($eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $regex, $exists, $all,
  $size, $elemMatch, $and, $or, $nor), проекциями, сортировкой и pipeline
  агрегации ($match, $group, $sort, $project, $limit, $skip, $unwind, $count).

Оба варианта предоставляют одинаковый интерфейс коллекции, поэтому
MongoRepository работает с ними единообразно.
"""
from __future__ import annotations

import re
import threading
from copy import deepcopy
from typing import Any, Iterable, Iterator

from .errors import InvalidIdentifierError

#: Разделитель пути вложенного поля.
_DOT = "."


# ---------------------------------------------------------------------------
# Движок запросов (используется in-memory реализацией)
# ---------------------------------------------------------------------------
def _resolve_path(doc: Any, path: str) -> tuple[bool, Any]:
    """Вернуть (найдено, значение) для пути вида "director.name".

    Если на пути встречается список документов, значения собираются в список.
    """
    parts = path.split(_DOT)
    current = doc
    for index, part in enumerate(parts):
        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, list):
            rest = _DOT.join(parts[index:])
            collected: list[Any] = []
            for item in current:
                if isinstance(item, dict) and part in item:
                    found, value = _resolve_path(item, rest)
                    if found:
                        collected.append(value)
                elif part.isdigit():
                    try:
                        collected.append(item[int(part)])
                    except (ValueError, IndexError):
                        pass
            return (bool(collected), collected or None)
        else:
            return False, None
    return True, current


def _eq_match(value: Any, expected: Any) -> bool:
    """Равенство с поддержкой массивов (MongoDB-семантика)."""
    if isinstance(value, list):
        if any(item == expected for item in value):
            return True
        return value == expected
    return value == expected


def _cmp(value: Any, expected: Any) -> int | None:
    """Сравнить два скаляра; None, если сравнение невозможно."""
    try:
        if isinstance(value, (int, float)) and isinstance(expected, (int, float)):
            return (value > expected) - (value < expected)
        if isinstance(value, str) and isinstance(expected, str):
            return (value > expected) - (value < expected)
        return (value > expected) - (value < expected)  # универсальный путь
    except TypeError:
        return None


def _compare_match(value: Any, op: str, expected: Any) -> bool:
    candidates = value if isinstance(value, list) else [value]
    for candidate in candidates:
        result = _cmp(candidate, expected)
        if result is None:
            continue
        if op == "$gt" and result > 0:
            return True
        if op == "$gte" and result >= 0:
            return True
        if op == "$lt" and result < 0:
            return True
        if op == "$lte" and result <= 0:
            return True
    return False


def _match_value(value: Any, condition: Any) -> bool:
    """Сопоставить значение поля условию (скаляру или словарю операторов)."""
    if isinstance(condition, dict) and any(str(k).startswith("$") for k in condition):
        for op, arg in condition.items():
            if op == "$eq":
                if not _eq_match(value, arg):
                    return False
            elif op == "$ne":
                if _eq_match(value, arg):
                    return False
            elif op in ("$gt", "$gte", "$lt", "$lte"):
                if not _compare_match(value, op, arg):
                    return False
            elif op == "$in":
                if not any(_eq_match(value, item) for item in arg):
                    return False
            elif op == "$nin":
                if any(_eq_match(value, item) for item in arg):
                    return False
            elif op == "$regex":
                flags = 0
                if isinstance(arg, dict):
                    pattern = arg.get("$regex", "")
                    if "i" in str(arg.get("$options", "")):
                        flags = re.IGNORECASE
                else:
                    pattern = arg
                candidates = value if isinstance(value, list) else [value]
                if not any(re.search(pattern, str(c)) for c in candidates if c is not None):
                    return False
            elif op == "$exists":
                present = value is not None
                if present != bool(arg):
                    return False
            elif op == "$all":
                if not isinstance(value, list) or not all(
                    any(item == expected for item in value) for expected in arg
                ):
                    return False
            elif op == "$size":
                if not isinstance(value, list) or len(value) != arg:
                    return False
            elif op == "$elemMatch":
                if not isinstance(value, list):
                    return False
                if not any(_matches(item, arg) if isinstance(item, dict) else _match_value(item, arg) for item in value):
                    return False
            elif op == "$not":
                if _match_value(value, arg):
                    return False
            else:  # неизвестный оператор — не совпадает
                return False
        return True
    return _eq_match(value, condition)


def _matches(doc: dict[str, Any], query: dict[str, Any] | None) -> bool:
    """Проверить соответствие документа запросу MongoDB."""
    if not query:
        return True
    for key, condition in query.items():
        if key == "$and":
            if not all(_matches(doc, sub) for sub in condition):
                return False
        elif key == "$or":
            if not any(_matches(doc, sub) for sub in condition):
                return False
        elif key == "$nor":
            if any(_matches(doc, sub) for sub in condition):
                return False
        else:
            found, value = _resolve_path(doc, key)
            if not found:
                if isinstance(condition, dict) and "$exists" in condition:
                    if bool(condition["$exists"]):
                        return False
                    continue
                return False
            if not _match_value(value, condition):
                return False
    return True


def _apply_projection(doc: dict[str, Any], projection: dict[str, Any] | None) -> dict[str, Any]:
    """Применить проекцию (выборку нужных полей)."""
    if not projection:
        return deepcopy(doc)
    including = [k for k, v in projection.items() if v and k != "_id"]
    if including:
        result = {k: deepcopy(v) for k, v in doc.items() if k in including}
        if projection.get("_id", 1) and "_id" in doc:
            result["_id"] = doc["_id"]
        return result
    result = deepcopy(doc)
    for key in projection:
        if not projection[key]:
            if _DOT in key:
                head = key.split(_DOT)[0]
                result.pop(head, None)
            else:
                result.pop(key, None)
    return result


def _sort_key(doc: dict[str, Any], field: str) -> tuple[int, Any]:
    found, value = _resolve_path(doc, field)
    if not found or value is None:
        return (1, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, (int, float)):
        return (0, value)
    return (0, str(value))


def _sort_docs(docs: list[dict[str, Any]], sort_spec: Any) -> list[dict[str, Any]]:
    """Отсортировать документы согласно спецификации pymongo."""
    if not sort_spec:
        return docs
    if isinstance(sort_spec, str):
        sort_spec = [(sort_spec, 1)]
    elif isinstance(sort_spec, dict):  # $sort в aggregation pipeline задаётся словарём
        sort_spec = list(sort_spec.items())
    result = list(docs)
    for field, direction in reversed(list(sort_spec)):
        result.sort(key=lambda d, f=field: _sort_key(d, f), reverse=int(direction) < 0)
    return result


# ---------------------------------------------------------------------------
# In-memory коллекция
# ---------------------------------------------------------------------------
class InsertOneResult:
    """Аналог pymongo.results.InsertOneResult."""

    def __init__(self, inserted_id: Any) -> None:
        self.inserted_id = inserted_id


class UpdateResult:
    """Аналог pymongo.results.UpdateResult."""

    def __init__(self, matched: int, modified: int, upserted_id: Any = None) -> None:
        self.matched_count = matched
        self.modified_count = modified
        self.upserted_id = upserted_id


class DeleteResult:
    """Аналог pymongo.results.DeleteResult."""

    def __init__(self, deleted: int) -> None:
        self.deleted_count = deleted


class InMemoryCollection:
    """Документная коллекция в оперативной памяти с API, близким к PyMongo."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._docs: list[dict[str, Any]] = []
        self._indexes: dict[str, list[tuple[str, int]]] = {}
        self._unique_fields: set[str] = set()
        self._auto_id = 0
        self._lock = threading.RLock()

    # ------------------------------------------------------------- служебное
    def _next_id(self) -> int:
        self._auto_id += 1
        return self._auto_id

    def _check_unique(self, doc: dict[str, Any], ignore_id: Any = None) -> None:
        for field in self._unique_fields:
            _, value = _resolve_path(doc, field)
            for existing in self._docs:
                if existing.get("_id") == ignore_id:
                    continue
                _, other = _resolve_path(existing, field)
                if other == value:
                    raise InvalidIdentifierError(
                        f"Нарушение уникального индекса по полю {field!r}: {value!r}"
                    )

    # ------------------------------------------------------------------ CRUD
    def insert_one(self, document: dict[str, Any]) -> InsertOneResult:
        with self._lock:
            doc = deepcopy(document)
            if "_id" not in doc or doc["_id"] is None:
                doc["_id"] = self._next_id()
            self._check_unique(doc)
            self._docs.append(doc)
            return InsertOneResult(doc["_id"])

    def insert_many(self, documents: Iterable[dict[str, Any]]) -> list[Any]:
        return [self.insert_one(d).inserted_id for d in documents]

    def find_one(self, query: dict[str, Any] | None = None, projection: dict[str, Any] | None = None) -> dict[str, Any] | None:
        with self._lock:
            for doc in self._docs:
                if _matches(doc, query):
                    return _apply_projection(doc, projection)
        return None

    def find(
        self,
        query: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
        sort: Any = None,
        limit: int = 0,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        with self._lock:
            docs = [deepcopy(d) for d in self._docs if _matches(d, query)]
        docs = _sort_docs(docs, sort)
        if skip:
            docs = docs[skip:]
        if limit:
            docs = docs[:limit]
        return [_apply_projection(d, projection) for d in docs]

    def count_documents(self, query: dict[str, Any] | None = None) -> int:
        with self._lock:
            return sum(1 for d in self._docs if _matches(d, query))

    def distinct(self, field: str, query: dict[str, Any] | None = None) -> list[Any]:
        values: list[Any] = []
        with self._lock:
            for doc in self._docs:
                if not _matches(doc, query):
                    continue
                _, value = _resolve_path(doc, field)
                if isinstance(value, list):
                    for item in value:
                        if item not in values:
                            values.append(item)
                elif value is not None and value not in values:
                    values.append(value)
        return values

    def update_one(self, query: dict[str, Any], update: dict[str, Any], upsert: bool = False) -> UpdateResult:
        with self._lock:
            for doc in self._docs:
                if _matches(doc, query):
                    updated = self._apply_update(doc, update)
                    self._check_unique(updated, ignore_id=doc.get("_id"))
                    doc.clear()
                    doc.update(updated)
                    return UpdateResult(1, 1)
            if upsert:
                base: dict[str, Any] = {}
                for key, value in query.items():
                    if not key.startswith("$") and not isinstance(value, dict):
                        base[key] = value
                new_doc = self._apply_update(base, update, is_insert=True)
                self._docs.append(new_doc)
                return UpdateResult(0, 0, new_doc["_id"])
        return UpdateResult(0, 0)

    def update_many(self, query: dict[str, Any], update: dict[str, Any]) -> UpdateResult:
        modified = 0
        with self._lock:
            for doc in self._docs:
                if _matches(doc, query):
                    updated = self._apply_update(doc, update)
                    doc.clear()
                    doc.update(updated)
                    modified += 1
        return UpdateResult(modified, modified)

    def _apply_update(self, doc: dict[str, Any], update: dict[str, Any], is_insert: bool = False) -> dict[str, Any]:
        result = deepcopy(doc)
        for operator, payload in update.items():
            if operator == "$set":
                for key, value in payload.items():
                    _set_path(result, key, deepcopy(value))
            elif operator == "$inc":
                for key, value in payload.items():
                    found, current = _resolve_path(result, key)
                    _set_path(result, key, (current if found else 0) + value)
            elif operator == "$push":
                for key, value in payload.items():
                    found, current = _resolve_path(result, key)
                    if not found or current is None:
                        current = []
                    current.append(deepcopy(value))
                    _set_path(result, key, current)
            elif operator == "$pull":
                for key, value in payload.items():
                    found, current = _resolve_path(result, key)
                    if isinstance(current, list):
                        _set_path(result, key, [x for x in current if x != value])
            elif operator == "$addToSet":
                for key, value in payload.items():
                    found, current = _resolve_path(result, key)
                    if not isinstance(current, list):
                        current = []
                    if value not in current:
                        current.append(deepcopy(value))
                    _set_path(result, key, current)
            elif operator == "$unset":
                for key in payload:
                    result.pop(key, None)
            elif not operator.startswith("$"):
                result[operator] = deepcopy(payload)
        if is_insert and "_id" not in result:
            result["_id"] = self._next_id()
        if "$setOnInsert" in update and is_insert:
            for key, value in update["$setOnInsert"].items():
                _set_path(result, key, deepcopy(value))
        return result

    def delete_one(self, query: dict[str, Any]) -> DeleteResult:
        with self._lock:
            for index, doc in enumerate(self._docs):
                if _matches(doc, query):
                    self._docs.pop(index)
                    return DeleteResult(1)
        return DeleteResult(0)

    def delete_many(self, query: dict[str, Any] | None = None) -> DeleteResult:
        with self._lock:
            before = len(self._docs)
            self._docs = [d for d in self._docs if not _matches(d, query)]
            return DeleteResult(before - len(self._docs))

    # --------------------------------------------------------------- индексы
    def create_index(self, keys: Any, unique: bool = False, name: str | None = None) -> str:
        if isinstance(keys, str):
            spec = [(keys, 1)]
        elif isinstance(keys, list) and keys and isinstance(keys[0], str):
            spec = [(k, 1) for k in keys]
        else:
            spec = [(str(k), int(v)) for k, v in keys]
        index_name = name or "_".join(f"{k}_{v}" for k, v in spec)
        self._indexes[index_name] = spec
        if unique:
            for field_name, _ in spec:
                self._unique_fields.add(field_name)
        return index_name

    def index_information(self) -> dict[str, dict[str, Any]]:
        info = {"_id_": {"key": [("_id", 1)], "v": 2}}
        for index_name, spec in self._indexes.items():
            info[index_name] = {"key": spec, "v": 2}
        return info

    def drop(self) -> None:
        with self._lock:
            self._docs.clear()

    # ------------------------------------------------------------ агрегация
    def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self._lock:
            docs: list[dict[str, Any]] = [deepcopy(d) for d in self._docs]
        for stage in pipeline:
            if not isinstance(stage, dict) or not stage:
                continue
            operator, payload = next(iter(stage.items()))
            if operator == "$match":
                docs = [d for d in docs if _matches(d, payload)]
            elif operator == "$sort":
                docs = _sort_docs(docs, payload)
            elif operator == "$limit":
                docs = docs[: int(payload)]
            elif operator == "$skip":
                docs = docs[int(payload):]
            elif operator == "$project":
                docs = [_apply_projection(d, payload) for d in docs]
            elif operator == "$unwind":
                docs = _unwind(docs, payload)
            elif operator == "$group":
                docs = _group(docs, payload)
            elif operator == "$count":
                docs = [{str(payload): len(docs)}]
            else:
                raise NotImplementedError(f"Стадия агрегации {operator!r} не поддерживается")
        return docs


def _set_path(doc: dict[str, Any], path: str, value: Any) -> None:
    """Установить значение по пути, создавая вложенные словари."""
    parts = path.split(_DOT)
    current = doc
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value


def _unwind(docs: list[dict[str, Any]], payload: Any) -> list[dict[str, Any]]:
    """Стадия $unwind для строкового пути или словаря."""
    path = payload
    preserve = False
    if isinstance(payload, dict):
        path = payload.get("path", "")
        preserve = bool(payload.get("preserveNullAndEmptyArrays", False))
    path = str(path).lstrip("$")
    result: list[dict[str, Any]] = []
    for doc in docs:
        found, value = _resolve_path(doc, path)
        if found and isinstance(value, list) and value:
            for item in value:
                new_doc = deepcopy(doc)
                _set_path(new_doc, path, deepcopy(item))
                result.append(new_doc)
        elif preserve:
            result.append(doc)
    return result


def _group(docs: list[dict[str, Any]], payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Стадия $group с аккумуляторами $sum, $avg, $min, $max, $push, $addToSet."""
    id_expr = payload.get("_id")
    groups: dict[Any, dict[str, Any]] = {}
    for doc in docs:
        key = _eval_expr(doc, id_expr)
        key_hash = key if isinstance(key, (str, int, float, type(None))) else str(key)
        bucket = groups.setdefault(key_hash, {"_id": key, "_items": []})
        bucket["_items"].append(doc)

    result: list[dict[str, Any]] = []
    for bucket in groups.values():
        items: list[dict[str, Any]] = bucket.pop("_items")
        out: dict[str, Any] = {"_id": bucket["_id"]}
        for field, accumulator in payload.items():
            if field == "_id":
                continue
            if not isinstance(accumulator, dict):
                continue
            op, arg = next(iter(accumulator.items()))
            values = [_eval_expr(item, arg) for item in items]
            values = [v for v in values if v is not None]
            if op == "$sum":
                out[field] = sum(v if isinstance(v, (int, float)) else 0 for v in values)
            elif op == "$avg":
                numbers = [v for v in values if isinstance(v, (int, float))]
                out[field] = round(sum(numbers) / len(numbers), 2) if numbers else None
            elif op == "$min":
                out[field] = min(values) if values else None
            elif op == "$max":
                out[field] = max(values) if values else None
            elif op == "$push":
                out[field] = values
            elif op == "$addToSet":
                unique: list[Any] = []
                for v in values:
                    if v not in unique:
                        unique.append(v)
                out[field] = unique
            elif op == "$first":
                out[field] = values[0] if values else None
            elif op == "$last":
                out[field] = values[-1] if values else None
            elif op == "$count":
                out[field] = len(items)
        result.append(out)

    sort_spec = payload.get("__sort__")
    if sort_spec:
        result = _sort_docs(result, sort_spec)
    return result


def _eval_expr(doc: dict[str, Any], expression: Any) -> Any:
    """Вычислить выражение агрегации: "$field", литерал или словарь-оператор."""
    if isinstance(expression, str) and expression.startswith("$"):
        found, value = _resolve_path(doc, expression[1:])
        return value if found else None
    if isinstance(expression, dict):
        op, arg = next(iter(expression.items()))
        if op == "$literal":
            return arg
        if op == "$ifNull":
            found, value = _resolve_path(doc, str(arg[0]).lstrip("$")) if isinstance(arg[0], str) else (False, None)
            return value if found and value is not None else arg[1]
        if op == "$size":
            value = _eval_expr(doc, arg)
            return len(value) if isinstance(value, list) else 0
        if op == "$toUpper":
            value = _eval_expr(doc, arg)
            return str(value).upper() if value is not None else None
        if op in ("$multiply", "$add", "$subtract", "$divide"):
            values = [_eval_expr(doc, item) for item in arg]
            numbers = [v for v in values if isinstance(v, (int, float))]
            if len(numbers) != len(values):
                return None
            if op == "$multiply":
                result = 1
                for number in numbers:
                    result *= number
                return result
            if op == "$add":
                return sum(numbers)
            if op == "$subtract":
                return numbers[0] - sum(numbers[1:]) if numbers else None
            if op == "$divide":
                return numbers[0] / numbers[1] if len(numbers) == 2 and numbers[1] else None
        if op == "$floor":
            value = _eval_expr(doc, arg)
            return int(value) if isinstance(value, (int, float)) else None
    return expression


# ---------------------------------------------------------------------------
# In-memory база данных
# ---------------------------------------------------------------------------
class InMemoryDatabase:
    """Простая in-memory база данных: коллекции по имени."""

    def __init__(self, name: str = "cinema") -> None:
        self.name = name
        self._collections: dict[str, InMemoryCollection] = {}

    def __getitem__(self, collection_name: str) -> InMemoryCollection:
        if collection_name not in self._collections:
            self._collections[collection_name] = InMemoryCollection(collection_name)
        return self._collections[collection_name]

    def list_collection_names(self) -> list[str]:
        return list(self._collections)

    def drop_collection(self, collection_name: str) -> None:
        self._collections.pop(collection_name, None)


# ---------------------------------------------------------------------------
# Подключение к настоящему MongoDB
# ---------------------------------------------------------------------------
def connect_mongo(
    uri: str = "mongodb://127.0.0.1:27017",
    db_name: str = "cinema",
    timeout_ms: int = 800,
    allow_fallback: bool = True,
) -> tuple[Any, str, str | None]:
    """Подключиться к MongoDB, при недоступности вернуть in-memory реализацию.

    Возвращает кортеж (база, режим, сообщение_об_ошибке), где режим принимает
    значения "mongodb" или "memory".
    """
    error: str | None = None
    try:
        from pymongo import MongoClient  # импорт внутри функции: pymongo не обязателен

        client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        client.admin.command("ping")  # реальная проверка соединения
        return client[db_name], "mongodb", None
    except Exception as exc:  # pymongo.errors.*, ImportError, timeout и т. п.
        error = f"{type(exc).__name__}: {exc}"
        if not allow_fallback:
            from .errors import StorageUnavailableError

            raise StorageUnavailableError(f"MongoDB недоступна ({error})") from exc
    return InMemoryDatabase(db_name), "memory", error
