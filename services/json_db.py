import json
def update(filename: str, predicate: Callable[[Dict[str, Any]], bool], updater: Callable[[Dict[str, Any]], Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update records matching predicate."""
    path = _full_path(filename)
    _ensure_file(path, [])
    lock = _get_lock(path)

    with lock:
        data = read(filename, default=[])
        updated = []
        for i, item in enumerate(data):
            if predicate(item):
                new_item = updater(item)
                new_item["updated_at"] = datetime.utcnow().isoformat()
                data[i] = new_item
                updated.append(new_item)

        write(filename, data)
        return updated


def filter_data(filename: str, predicate: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
    """Filter records based on predicate."""
    data = read(filename, default=[])
    return [item for item in data if predicate(item)]


def get_by_id(filename: str, record_id: str) -> Dict[str, Any] | None:
    data = read(filename, default=[])
    for item in data:
        if item.get("id") == record_id:
            return item
    return None


def upsert_singleton(filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Store a single object (for user.json)."""
    path = _full_path(filename)
    lock = _get_lock(path)

    with lock:
        now = datetime.utcnow().isoformat()
        payload = {
            **data,
            "updated_at": now,
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return payload


def read_singleton(filename: str, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    path = _full_path(filename)
    _ensure_file(path, default if default is not None else {})
    lock = _get_lock(path)

    with lock:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return default if default is not None else {}
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return default if default is not None else {}