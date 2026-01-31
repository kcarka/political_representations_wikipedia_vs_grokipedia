import html
import re

_CITATION_PATTERN = re.compile(r"\[\s*(?:citation needed|\d+(?:\s*[;,]\s*\d+)*|[a-zA-Z])\s*\]", re.IGNORECASE)


def clean_span_text(text: str) -> str:
    """Normalize parsed text spans before storage."""
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    # Remove backslashes before quotes using regex
    text = re.sub(r'\\(["\'])', r'\1', text)
    text = _CITATION_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
