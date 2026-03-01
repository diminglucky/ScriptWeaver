"""Cache helpers extracted from enhancements mixin."""

import hashlib
import json
import logging
import time
from pathlib import Path
from tkinter import messagebox
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """File-based cache with max-size cleanup."""

    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size_mb * 1024 * 1024
        self.index_file = self.cache_dir / "index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.index = loaded if isinstance(loaded, dict) else {}
            except Exception as e:
                logger.warning("load cache index failed, resetting: %s", e)
                self.index = {}
        else:
            self.index = {}

    def _save_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False)

    def _get_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    @staticmethod
    def _is_expired(meta: Dict[str, Any]) -> bool:
        ttl = meta.get("ttl")
        created = meta.get("created")
        if ttl is None or created is None:
            return False
        try:
            ttl_value = int(ttl)
        except Exception:
            return False
        if ttl_value < 0:
            ttl_value = 0
        return (float(created) + ttl_value) <= time.time()

    def _delete_by_cache_key(self, cache_key: str, save_index: bool = True):
        if cache_key in self.index:
            del self.index[cache_key]
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception as e:
                logger.debug("delete cache file failed [%s]: %s", cache_key, e)
        if save_index:
            self._save_index()

    def get(self, key: str) -> Optional[Any]:
        cache_key = self._get_key(key)
        meta = self.index.get(cache_key)
        if not meta:
            return None

        if self._is_expired(meta):
            self._delete_by_cache_key(cache_key)
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            self._delete_by_cache_key(cache_key)
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and self._is_expired(data):
                self._delete_by_cache_key(cache_key)
                return None
            self.index[cache_key]["last_access"] = time.time()
            self.index[cache_key]["size"] = cache_file.stat().st_size
            self._save_index()
            return data.get("value") if isinstance(data, dict) else None
        except Exception as e:
            logger.debug("read cache entry failed [%s]: %s", key, e)
            self._delete_by_cache_key(cache_key)
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        cache_key = self._get_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            ttl_value = int(ttl)
        except Exception:
            ttl_value = 3600
        if ttl_value < 0:
            ttl_value = 0

        now = time.time()
        data = {"key": key, "value": value, "created": now, "ttl": ttl_value}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        self.index[cache_key] = {
            "key": key,
            "created": now,
            "last_access": now,
            "ttl": ttl_value,
            "size": cache_file.stat().st_size,
        }
        self._save_index()
        self._cleanup_if_needed()

    def delete(self, key: str):
        self._delete_by_cache_key(self._get_key(key))

    def clear(self):
        for cache_key in list(self.index.keys()):
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
        self.index = {}
        self._save_index()

    def _cleanup_if_needed(self):
        total_size = sum(item.get("size", 0) for item in self.index.values())
        if total_size > self.max_size:
            sorted_items = sorted(self.index.items(), key=lambda x: x[1].get("last_access", 0))
            while total_size > self.max_size * 0.8 and sorted_items:
                cache_key, item = sorted_items.pop(0)
                self._delete_by_cache_key(cache_key, save_index=False)
                total_size -= int(item.get("size", 0) or 0)
            self._save_index()


class CacheMixin:
    """Mixin wrappers around cache manager."""

    def _init_cache(self):
        self.cache = CacheManager()

    def get_cached(self, key: str) -> Optional[Any]:
        if hasattr(self, "cache"):
            return self.cache.get(key)
        return None

    def set_cached(self, key: str, value: Any, ttl: int = 3600):
        if hasattr(self, "cache"):
            self.cache.set(key, value, ttl)

    def clear_cache(self):
        if hasattr(self, "cache"):
            self.cache.clear()
            messagebox.showinfo("成功", "缓存已清除")
