import hashlib
import json
from pathlib import Path
from utils.config import CACHE_DIR


def compute_checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_cache(checksum: str) -> dict | None:
    cache_file = CACHE_DIR / f"{checksum}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def write_cache(checksum: str, data: dict) -> None:
    cache_file = CACHE_DIR / f"{checksum}.json"
    cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_cache(checksum: str | None = None) -> int:
    if checksum:
        cache_file = CACHE_DIR / f"{checksum}.json"
        if cache_file.exists():
            cache_file.unlink()
            return 1
        return 0
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
        count += 1
    return count
