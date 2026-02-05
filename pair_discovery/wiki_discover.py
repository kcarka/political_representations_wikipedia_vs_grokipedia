import time
from collections import deque
from typing import List, Dict, Any, Optional, Set
import requests

WIKI_API = "https://en.wikipedia.org/w/api.php"


def _is_bad_title(title: str) -> bool:
    bad_prefixes = ("List of", "Outline of", "Timeline of", "Index of")
    if title.startswith(bad_prefixes):
        return True
    if ":" in title:  # namespaces
        return True
    return False


def _categorymembers_once(
    category: str, *, cmtype: str, limit: int, user_agent: str
) -> List[Dict[str, Any]]:
    """Fetch one category's members (page or subcat)."""
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    out: List[Dict[str, Any]] = []
    cont: Optional[str] = None

    while len(out) < limit:
        params: Dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": min(200, limit - len(out)),
            "cmtype": cmtype,  # "page" or "subcat"
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont

        # retry a few times
        last_err = None
        for _ in range(4):
            try:
                r = requests.get(WIKI_API, params=params, headers=headers, timeout=20)
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(1.5)
                    continue
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                last_err = e
                time.sleep(1.5)
        else:
            raise last_err  # type: ignore

        out.extend(data.get("query", {}).get("categorymembers", []))
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break

        time.sleep(0.3)

    return out


def discover_titles_from_category_recursive(
    root_category: str,
    *,
    limit_pages: int = 200,
    max_depth: int = 5,
    user_agent: str = "FairnessAI-PairDiscovery/0.1 (contact: local)",
) -> List[str]:
    """
    Recursively walk subcategories up to max_depth and collect article pages.
    This fixes the '0it' issue when a category mainly contains subcategories.
    """
    q = deque([(root_category, 0)])
    seen_cats: Set[str] = set([root_category])
    pages: List[str] = []
    seen_pages: Set[str] = set()

    while q and len(pages) < limit_pages:
        cat, depth = q.popleft()

        # 1) collect pages from this category
        members_page = _categorymembers_once(
            cat, cmtype="page", limit=500, user_agent=user_agent
        )
        for m in members_page:
            title = m.get("title", "")
            if title and (not _is_bad_title(title)) and title not in seen_pages:
                seen_pages.add(title)
                pages.append(title)
                if len(pages) >= limit_pages:
                    break

        if len(pages) >= limit_pages:
            break

        # 2) if depth allows, enqueue subcats
        if depth < max_depth:
            members_sub = _categorymembers_once(
                cat, cmtype="subcat", limit=500, user_agent=user_agent
            )
            for m in members_sub:
                subcat = m.get("title", "")
                if (
                    subcat
                    and subcat.startswith("Category:")
                    and subcat not in seen_cats
                ):
                    seen_cats.add(subcat)
                    q.append((subcat, depth + 1))

    return pages[:limit_pages]


# Backward-compatible wrapper (keeps old name working)
def discover_titles_from_category(
    category: str,
    limit: int = 200,
    cmtype: str = "page",
    user_agent: str = "FairnessAI-PairDiscovery/0.1 (contact: local)",
):
    # ignore cmtype here; recursive discovery returns pages
    return discover_titles_from_category_recursive(
        root_category=category,
        limit_pages=limit,
        max_depth=2,
        user_agent=user_agent,
    )
