import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    from_cache: bool
    elapsed_sec: float


class HTTPCache:
    """
    Tiny on-disk cache for GET requests.
    Stores response text and metadata keyed by URL hash.
    """

    def __init__(self, cache_dir: str, ttl_days: int = 30):
        self.cache_dir = cache_dir
        self.ttl_sec = ttl_days * 24 * 3600
        os.makedirs(self.cache_dir, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _paths(self, url: str):
        key = self._key(url)
        return (
            os.path.join(self.cache_dir, f"{key}.json"),
            os.path.join(self.cache_dir, f"{key}.txt"),
        )

    def get(self, url: str) -> Optional[FetchResult]:
        meta_path, body_path = self._paths(url)
        if not (os.path.exists(meta_path) and os.path.exists(body_path)):
            return None

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            age = time.time() - meta.get("fetched_at", 0)
            if age > self.ttl_sec:
                return None
            with open(body_path, "r", encoding="utf-8", errors="ignore") as f:
                body = f.read()
            return FetchResult(
                url=url,
                status_code=int(meta.get("status_code", 0)),
                text=body,
                from_cache=True,
                elapsed_sec=float(meta.get("elapsed_sec", 0.0)),
            )
        except Exception:
            return None

    def put(self, url: str, status_code: int, text: str, elapsed_sec: float) -> None:
        meta_path, body_path = self._paths(url)
        meta = {
            "url": url,
            "status_code": status_code,
            "fetched_at": time.time(),
            "elapsed_sec": elapsed_sec,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        with open(body_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(text)


def cached_get(
    url: str,
    cache: HTTPCache,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    sleep_sec: float = 0.8,
) -> FetchResult:
    cached = cache.get(url)
    if cached is not None:
        return cached

    t0 = time.time()
    resp = requests.get(url, headers=headers, timeout=timeout)
    elapsed = time.time() - t0

    # polite throttling (important esp. for Grokipedia)
    time.sleep(sleep_sec)

    text = resp.text if resp.text is not None else ""
    cache.put(url=url, status_code=resp.status_code, text=text, elapsed_sec=elapsed)
    return FetchResult(
        url=url,
        status_code=resp.status_code,
        text=text,
        from_cache=False,
        elapsed_sec=elapsed,
    )
