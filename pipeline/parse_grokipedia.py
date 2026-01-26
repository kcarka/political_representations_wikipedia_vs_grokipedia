from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag


def parse_grokipedia_article(html: str) -> Dict[str, Any]:
    """
    Parse Grokipedia HTML into sections and references based on actual structure:
    - h2 headings define top-level sections (e.g., Early Life)
    - h3 headings inside a section define subsections (e.g., Upbringing)
    - Text spans appear between headings (not as children)
    - Structure: h2 -> [spans...] -> h3 -> [spans...] -> h3 -> [spans...] -> h2 -> [spans...]
    - References reside in a div#references containing an <ol> list
    """
    soup = BeautifulSoup(html, "html.parser")

    sections: List[Dict[str, Any]] = []
    
    # Get all h2 headings
    h2_tags = soup.find_all("h2")
    
    for h2_idx, h2 in enumerate(h2_tags):
        section_title = h2.get_text(" ", strip=True)
        print(f"\n[parse] Section (h2): {section_title}")
        
        section_spans: List[str] = []
        subsections: List[Dict[str, Any]] = []
        
        # Determine the range: from this h2 to the next h2 (or end of document)
        next_h2 = h2_tags[h2_idx + 1] if h2_idx + 1 < len(h2_tags) else None
        
        current_sub: Optional[Dict[str, Any]] = None
        
        # Iterate through siblings from h2 until we hit the next h2
        for sib in h2.next_siblings:
            # Stop at next h2
            if isinstance(sib, Tag) and sib.name == "h2" and sib == next_h2:
                break
            
            if not isinstance(sib, Tag):
                continue
            
            # If h3, start a new subsection
            if sib.name == "h3":
                if current_sub:
                    subsections.append(current_sub)
                subsection_title = sib.get_text(" ", strip=True)
                print(f"[parse]   Subsection (h3): {subsection_title}")
                current_sub = {
                    "title": subsection_title,
                    "spans": [],
                }
                continue
            
            # If span with mb-4 class, it's a content block
            if sib.name == "span" and "mb-4" in sib.get("class", []):
                text = sib.get_text(" ", strip=True)
                if text:
                    print(f"[parse]     span text (first 80 chars): {text[:80]}")
                    if current_sub is not None:
                        current_sub["spans"].append(text)
                    else:
                        section_spans.append(text)
                continue
        
        # Flush last subsection
        if current_sub:
            subsections.append(current_sub)
        
        sections.append({
            "title": section_title,
            "spans": section_spans,
            "subsections": subsections,
        })
    
    references = _extract_references(soup)
    
    return {
        "sections": sections,
        "references": references,
    }


def _extract_references(soup: BeautifulSoup) -> List[Dict[str, str]]:
    refs: List[Dict[str, str]] = []
    ref_div = soup.find("div", id="references")
    if not ref_div:
        return refs
    ol = ref_div.find("ol")
    if not ol:
        return refs
    for li in ol.find_all("li", recursive=False):
        # grab first link if present
        a = li.find("a", href=True)
        href = a.get("href") if a else None
        text = li.get_text(" ", strip=True)
        refs.append({
            "url": href,
            "text": text,
        })
    return refs

