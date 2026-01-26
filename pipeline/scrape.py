import json
import re
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 20

@dataclass
class Article:
    id: str
    url: str
    title: str
    source: str  # 'wikipedia' | 'grokipedia'
    categories: List[str]
    topic: Optional[str]
    raw_html: Optional[str]
    text: str
    references: List[Dict]


def _safe_get(url: str, source: str = "wiki") -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp
        print(f"[{source}] GET {url} -> {resp.status_code}")
        return None
    except requests.RequestException as exc:
        print(f"[{source}] GET {url} failed: {exc}")
        return None


def _extract_title_from_url(url: str) -> Optional[str]:
    if "/wiki/" not in url:
        return None
    title = url.split("/wiki/", 1)[1]
    return title


def _fetch_wikipedia_html_rest(title: str) -> Optional[str]:
    rest_url = f"https://en.wikipedia.org/api/rest_v1/page/html/{title}"
    try:
        r = requests.get(rest_url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.text
        print(f"[wiki] REST {title} -> {r.status_code}")
    except requests.RequestException as exc:
        print(f"[wiki] REST {title} failed: {exc}")
        return None
    return None


def _fetch_wikipedia_html_via_api(url: str) -> Optional[str]:
    """Fallback to MediaWiki API parse endpoint when direct GET is blocked (e.g., 403/429)."""
    title = _extract_title_from_url(url)
    if not title:
        return None
    params = {
        "action": "parse",
        "page": title.replace("_", " "),
        "prop": "text",
        "formatversion": 2,
        "redirects": 1,
        "format": "json",
    }
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php", params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        html = data.get("parse", {}).get("text")
        if not html:
            print(f"[wiki] parse API empty for {url}")
        return html
    except Exception as exc:
        print(f"[wiki] parse API failed for {url}: {exc}")
        return None



def _clean_text_from_soup(soup: BeautifulSoup) -> str:
    # Prefer main content container for Wikipedia; generic fallback for others
    main = soup.select_one("div.mw-parser-output") or soup.select_one("main") or soup.select_one("article")
    container = main or soup.body or soup
    print(f"[extract] using container: {container.name if container else 'None'}")
    
    # Remove tables, navboxes, infoboxes, scripts, styles
    for selector in [
        "table",
        "div.navbox",
        "table.infobox",
        "div#toc",
        "header",
        "footer",
        "aside",
        "script",
        "style",
        "nav",
        ".mw-editsection",
        ".reference",
    ]:
        for tag in soup.select(selector):
            tag.decompose()
    
    # First try: extract paragraphs from the container
    all_p = container.find_all("p", recursive=True)
    print(f"[extract] found {len(all_p)} <p> tags in container")
    
    if len(all_p) < 10:
        # Fallback: if few paragraphs, scan entire soup and also include div.mw-content-ltr, div[class*=content], etc.
        print(f"[extract] few paragraphs ({len(all_p)}), switching to full soup scan")
        all_p = soup.find_all("p", recursive=True)
        print(f"[extract] found {len(all_p)} <p> tags in full soup")
        
        # If still few, also grab text from divs with content-like classes
        if len(all_p) < 5:
            print(f"[extract] still few paragraphs, trying content divs")
            content_divs = soup.select("div.mw-content-ltr, div[class*=content], div[class*=body], div[class*=article]")
            print(f"[extract] found {len(content_divs)} content-like divs")
            for div in content_divs:
                all_p.extend(div.find_all("p", recursive=True))
            print(f"[extract] total <p> tags after content divs: {len(all_p)}")
        
        # If still very few, try aggressive: get all div text
        if len(all_p) < 3:
            print(f"[extract] aggressive fallback: extracting from all divs")
            all_divs = soup.find_all("div")
            print(f"[extract] found {len(all_divs)} total divs")
            div_texts = []
            for div in all_divs:
                text = div.get_text(" ", strip=True)
                if len(text.split()) >= 5:  # Only if substantial
                    div_texts.append(text)
            if div_texts:
                print(f"[extract] extracted {len(div_texts)} divs with 5+ words")
                return "\n".join(div_texts)
    
    paragraphs = [p.get_text(" ", strip=True) for p in all_p]
    print(f"[extract] extracted {len(paragraphs)} paragraphs, total chars: {sum(len(p) for p in paragraphs)}")
    
    # Filter short/noisy paragraphs
    paragraphs = [p for p in paragraphs if len(p.split()) >= 5]
    print(f"[extract] after filter (5+ words): {len(paragraphs)} paragraphs")
    
    return "\n".join(paragraphs)


def _extract_references(soup: BeautifulSoup) -> List[Dict]:
    refs: List[Dict] = []
    # Wikipedia references list
    ref_lists = soup.select("ol.references li")
    if not ref_lists:
        # Generic fallback: anchors in a references/external links section
        sections = soup.find_all(["section", "div", "h2", "h3"], string=re.compile("References|External links", re.I))
        anchors = []
        for sec in sections:
            anchors.extend(sec.find_all("a", href=True))
    else:
        anchors = []
        for li in ref_lists:
            anchors.extend(li.find_all("a", href=True))
    seen = set()
    for a in anchors:
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not href or not href.startswith("http"):
            continue
        key = (href, text)
        if key in seen:
            continue
        seen.add(key)
        refs.append({"url": href, "text": text})
    return refs


def _extract_categories_wikipedia(soup: BeautifulSoup) -> List[str]:
    cats = []
    catlinks = soup.select("div#mw-normal-catlinks ul li a")
    for a in catlinks:
        name = a.get_text(strip=True)
        if name:
            cats.append(name)
    return cats


def classify_topic(categories: List[str], text: str) -> Optional[str]:
    lcats = [c.lower() for c in categories]
    txt = text.lower()
    # Heuristic rules
    if any("birth" in c or "biograph" in c for c in lcats) or ("born" in txt and "is a" in txt[:200]):
        return "biography"
    if any("policy" in c or "legislation" in c or "law" in c for c in lcats):
        return "policy"
    if any("election" in c or "protest" in c or "campaign" in c or "event" in c for c in lcats):
        return "event"
    if any("agency" in c or "department" in c or "committee" in c or "institution" in c for c in lcats):
        return "institution"
    # Fallback: guess via keywords
    if re.search(r"\b(senator|representative|governor|president|mayor)\b", txt):
        return "biography"
    return None


def scrape_wikipedia_article(url: str) -> Optional[Article]:
    print(f"[wiki] fetching {url}")
    resp = _safe_get(url)
    html_content = None
    if resp:
        print(f"[wiki] GET ok {resp.status_code}, len={len(resp.text)}")
        html_content = resp.text
    if not html_content:
        title = _extract_title_from_url(url)
        if title:
            rest_html = _fetch_wikipedia_html_rest(title)
            if rest_html:
                print(f"[wiki] REST fallback len={len(rest_html)}")
                html_content = rest_html
    if not html_content:
        fallback_html = _fetch_wikipedia_html_via_api(url)
        if fallback_html:
            print(f"[wiki] parse API fallback len={len(fallback_html)}")
            html_content = fallback_html
    if not html_content:
        print(f"[wiki] failed to fetch {url}")
        return None
    
    # Return raw HTML without processing
    return Article(
        id=url,
        url=url,
        title="",
        source="wikipedia",
        categories=[],
        topic=None,
        raw_html=html_content,
        text="",
        references=[],
    )


def scrape_wikipedia_from_urls(urls: List[str], sleep_secs: float = 0.5) -> List[Article]:
    articles: List[Article] = []
    for url in urls:
        art = scrape_wikipedia_article(url)
        if art and (art.raw_html or art.text):
            articles.append(art)
        time.sleep(sleep_secs)
    return articles


def scrape_wikipedia_by_categories(categories: List[str], limit_per_cat: int = 20, sleep_secs: float = 0.5) -> List[Article]:
    articles: List[Article] = []
    session = requests.Session()
    session.headers.update(HEADERS)
    for cat in categories:
        # Use Wikipedia API to list category members
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat if cat.startswith("Category:") else f"Category:{cat}",
            "cmlimit": min(limit_per_cat, 50),
            "format": "json",
        }
        try:
            r = session.get("https://en.wikipedia.org/w/api.php", params=params, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            members = data.get("query", {}).get("categorymembers", [])
            for m in members:
                title = m.get("title")
                if not title:
                    continue
                url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                art = scrape_wikipedia_article(url)
                if art and art.text:
                    articles.append(art)
                time.sleep(sleep_secs)
        except Exception:
            # Skip category on error
            continue
    return articles


def scrape_grokipedia_from_urls(urls: List[str], sleep_secs: float = 0.5, save_debug_html: bool = True) -> List[Article]:
    articles: List[Article] = []
    for i, url in enumerate(urls):
        print(f"[grok] fetching {url}")
        resp = _safe_get(url, source="grok")
        if not resp:
            print(f"[grok] failed to fetch {url}")
            continue
        
        # Return raw HTML without processing
        articles.append(
            Article(
                id=url,
                url=url,
                title="",
                source="grokipedia",
                categories=[],
                topic=None,
                raw_html=resp.text,
                text="",
                references=[],
            )
        )
        time.sleep(sleep_secs)
    return articles


def save_articles_json(articles: List[Article], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(a) for a in articles], f, ensure_ascii=False, indent=2)
