"""
Parser for Wikipedia HTML structure.

Structure:
- Main content in <div class="mw-content-container">
- h2 headings define top-level sections (e.g., Early life and education, Business career)
- h3 headings define subsections (e.g., Real estate, Licensing the Trump name)
- Text is in <p> tags between headings
- References in <ol class="references">
"""

from typing import Any, Dict, List
from bs4 import BeautifulSoup, Tag
from pipeline.text_clean import clean_span_text


def parse_wikipedia_article(html: str) -> Dict[str, Any]:
    """
    Parse Wikipedia HTML into sections and references based on actual structure:
    - h2 headings define top-level sections (wrapped in div.mw-heading mw-heading2)
    - h3 headings define subsections (wrapped in div.mw-heading mw-heading3)
    - h4 headings define sub-subsections (wrapped in div.mw-heading mw-heading4)
    - Paragraph text appears after headings as siblings
    - References reside in <ol class="references">
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find main content container
    content_container = soup.find("div", class_="mw-content-container")
    if not content_container:
        print("[parse_wiki] Warning: mw-content-container not found, using full soup")
        content_container = soup

    sections: List[Dict[str, Any]] = []
    
    # Get all h2 heading wrapper divs
    h2_wrapper_divs = content_container.find_all("div", class_="mw-heading2")
    
    for h2_wrapper_idx, h2_wrapper in enumerate(h2_wrapper_divs):
        h2 = h2_wrapper.find("h2", recursive=False)
        if not h2:
            continue
            
        section_title = h2.get_text(" ", strip=True)
        print(f"\n[parse_wiki] Section (h2): {section_title}")
        
        section_paragraphs: List[str] = []
        subsections: List[Dict[str, Any]] = []
        
        # Determine the range: from this h2 wrapper to the next h2 wrapper (or end)
        next_h2_wrapper = h2_wrapper_divs[h2_wrapper_idx + 1] if h2_wrapper_idx + 1 < len(h2_wrapper_divs) else None
        
        # Iterate through siblings from h2_wrapper until we hit the next h2_wrapper
        for sib in h2_wrapper.next_siblings:
            # Stop at next h2 wrapper
            if isinstance(sib, Tag) and sib == next_h2_wrapper:
                break
            
            if not isinstance(sib, Tag):
                continue
            
            # Check if this is an h3 wrapper div
            if sib.name == "div" and "mw-heading3" in sib.get("class", []):
                h3 = sib.find("h3", recursive=False)
                if h3:
                    subsection_title = h3.get_text(" ", strip=True)
                    print(f"[parse_wiki]   Subsection (h3): {subsection_title}")
                    
                    sub_dict = {
                        "title": subsection_title,
                        "paragraphs": [],
                        "subsections": [],
                    }
                    
                    # Find the next h3 or h2 wrapper to know where this h3's scope ends
                    next_h3_wrapper = None
                    for sibling in sib.next_siblings:
                        if isinstance(sibling, Tag):
                            if ("mw-heading3" in sibling.get("class", []) or 
                                "mw-heading2" in sibling.get("class", [])):
                                next_h3_wrapper = sibling
                                break
                    
                    # Collect h4 subsubsections and paragraphs within this h3's scope
                    for h3_sib in sib.next_siblings:
                        if h3_sib == next_h3_wrapper:
                            break
                        
                        if not isinstance(h3_sib, Tag):
                            continue
                        
                        # Check for h4 wrapper
                        if h3_sib.name == "div" and "mw-heading4" in h3_sib.get("class", []):
                            h4 = h3_sib.find("h4", recursive=False)
                            if h4:
                                h4_title = h4.get_text(" ", strip=True)
                                print(f"[parse_wiki]     Sub-subsection (h4): {h4_title}")
                                sub_dict["subsections"].append({
                                    "title": h4_title,
                                    "paragraphs": [],
                                })
                            continue
                        
                        # Collect paragraphs
                        if h3_sib.name == "p":
                            text = h3_sib.get_text(" ", strip=True)
                            text = clean_span_text(text)
                            if text:
                                print(f"[parse_wiki]       paragraph text (first 80 chars): {text[:80]}")
                                # Add to last h4 if it exists, otherwise to h3 level
                                if sub_dict["subsections"]:
                                    sub_dict["subsections"][-1]["paragraphs"].append(text)
                                else:
                                    sub_dict["paragraphs"].append(text)
                            continue
                    
                    subsections.append(sub_dict)
                continue
            
            # If paragraph tag at h2 level, it's a content block
            if sib.name == "p":
                text = sib.get_text(" ", strip=True)
                text = clean_span_text(text)
                if text:
                    print(f"[parse_wiki]     paragraph text (first 80 chars): {text[:80]}")
                    section_paragraphs.append(text)
                continue
        
        sections.append({
            "title": section_title,
            "paragraphs": section_paragraphs,
            "subsections": subsections,
        })
    
    references = _extract_references(soup)
    
    return {
        "sections": sections,
        "references": references,
    }


def _extract_references(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract references from Wikipedia's inline <span class="reference-text"> elements.
    These are embedded within the content container throughout the article.
    Returns list of dicts with "url" and "text" keys, matching Grokipedia format.
    """
    refs: List[Dict[str, str]] = []
    
    # Find main content container
    content_container = soup.find("div", class_="mw-content-container")
    if not content_container:
        print("[parse_wiki] Warning: mw-content-container not found for reference extraction")
        return refs
    
    # Find all inline reference spans
    reference_spans = content_container.find_all("span", class_="reference-text")
    
    if not reference_spans:
        print("[parse_wiki] Warning: No reference-text spans found")
        return refs
    
    for span in reference_spans:
        # Look for external URL in <a rel="nofollow" class="external text">
        external_link = span.find("a", class_="external text", rel="nofollow")
        href = external_link.get("href") if external_link else None
        
        # Get full citation text from the span
        text = span.get_text(" ", strip=True)
        
        refs.append({
            "url": href,
            "text": text,
        })
    
    print(f"[parse_wiki] Found {len(refs)} references from reference-text spans")
    return refs
