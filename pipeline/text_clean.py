"""Text cleaning utilities for normalizing parsed HTML content.

This module provides functions to clean and normalize text extracted from Wikipedia
and Grokipedia HTML, removing citations, handling escaped quotes, and collapsing
whitespace.
"""

import html
import re

_CITATION_PATTERN = re.compile(r"\[\s*(?:citation needed|\d+(?:\s*[;,]\s*\d+)*|[a-zA-Z])\s*\]", re.IGNORECASE)
"""Regex pattern matching Wikipedia-style citations like [1], [d], or [citation needed]."""


def clean_span_text(text: str) -> str:
    """Normalize parsed text spans before storage.
    
    Performs the following normalization steps:
    1. Unescape HTML entities (e.g., &nbsp; -> space)
    2. Replace non-breaking spaces with regular spaces
    3. Remove escaped quotes (backslash before \" or ')
    4. Remove Wikipedia-style citations (e.g., [247], [d], [citation needed])
    5. Collapse multiple whitespace characters into single spaces
    6. Strip leading/trailing whitespace
    
    Args:
        text: Raw text string from parsed HTML, potentially containing HTML entities,
              escaped quotes, and citation markers.
    
    Returns:
        Cleaned text string suitable for storage and analysis.
    """
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    # Remove backslashes before quotes using regex
    text = re.sub(r'\\(["\'])', r'\1', text)
    text = _CITATION_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
