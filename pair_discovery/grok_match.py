import re
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup

from .http_cache import HTTPCache, cached_get


@dataclass
class GrokMatch:
    title: str
    url: str
    ok: bool
    status_code: int
    reason: str


def title_to_grok_url(title: str) -> str:
    # Grokipedia commonly uses /page/Title_with_underscores
    slug = title.replace(" ", "_")
    return f"https://grokipedia.com/page/{slug}"


def has_nontrivial_main_text(html: str, min_chars: int = 600) -> bool:
    """
    Heuristic: strip scripts/styles/nav and check text length.
    We do NOT implement full extraction here; just a gatekeeper for pairing.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "aside", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return len(text) >= min_chars


def try_match_grokipedia(title: str, cache: HTTPCache, user_agent: str) -> GrokMatch:
    url = title_to_grok_url(title)
    headers = {"User-Agent": user_agent}
    fr = cached_get(url, cache, headers=headers, timeout=20, sleep_sec=1.0)
    if fr.status_code != 200:
        return GrokMatch(
            title=title,
            url=url,
            ok=False,
            status_code=fr.status_code,
            reason=f"http_{fr.status_code}",
        )
    if not fr.text or not has_nontrivial_main_text(fr.text):
        return GrokMatch(
            title=title,
            url=url,
            ok=False,
            status_code=fr.status_code,
            reason="empty_or_too_short",
        )
    return GrokMatch(
        title=title, url=url, ok=True, status_code=fr.status_code, reason="ok"
    )
