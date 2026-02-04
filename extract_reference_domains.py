"""Extract domain roots from parsed references and organize by URL index.

Creates JSON files mapping URL indices to lists of domain roots extracted from
references, enabling analysis of source representation differences between
Wikipedia and Grokipedia.

Output files:
- data/outputs/wikipedia_references.json
- data/outputs/grokipedia_references.json
"""

import json
import os
from typing import List
from urllib.parse import urlparse


def read_lines(path: str) -> List[str]:
    """Read non-empty, non-comment lines from a text file."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def extract_domain_root(url: str) -> str:
    """Extract domain root from URL, normalized for comparison.
    
    Extracts just the netloc (domain) from a URL and normalizes it.
    Example: https://www.theguardian.com/us-news/2023/article -> theguardian.com
    
    Args:
        url: Full URL string.
    
    Returns:
        Normalized domain name (no scheme, no path) or empty string if parsing fails.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return ""
    except Exception:
        return ""


def process_platform(
    parsed_json_path: str,
    urls_txt_path: str,
    output_json_path: str,
    platform_name: str,
) -> None:
    """Process references for a platform and save domain roots indexed by URL.
    
    Args:
        parsed_json_path: Path to parsed JSON (wikipedia_parsed.json or grokipedia_parsed.json).
        urls_txt_path: Path to seed URLs file (wikipedia_urls.txt or grokipedia_urls.txt).
        output_json_path: Path where output JSON should be saved.
        platform_name: Name for logging ('Wikipedia' or 'Grokipedia').
    """
    # Read seed URLs to establish index mapping
    urls = read_lines(urls_txt_path)
    print(f"[{platform_name}] Read {len(urls)} seed URLs from {urls_txt_path}")
    
    # Read parsed JSON
    if not os.path.exists(parsed_json_path):
        print(f"[{platform_name}] Error: {parsed_json_path} not found")
        return
    
    with open(parsed_json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    print(f"[{platform_name}] Read {len(articles)} parsed articles from {parsed_json_path}")
    
    # Initialize reference list for each URL index
    references_by_url_index: List[List[str]] = [[] for _ in range(len(urls))]
    
    # Process each article
    for article_idx, article in enumerate(articles):
        article_url = article.get("url", "")
        
        # Find which URL index this article corresponds to
        url_idx = None
        for i, seed_url in enumerate(urls):
            if article_url.strip() == seed_url.strip():
                url_idx = i
                break
        
        if url_idx is None:
            print(f"[{platform_name}] Warning: article URL not found in seed URLs: {article_url}")
            continue
        
        # Extract domain roots from references
        references = article.get("references", [])
        for ref in references:
            ref_url = ref.get("url")
            if ref_url:
                domain_root = extract_domain_root(ref_url)
                if domain_root and domain_root not in references_by_url_index[url_idx]:
                    references_by_url_index[url_idx].append(domain_root)
        
        print(
            f"[{platform_name}] Article {article_idx} (URL index {url_idx}): "
            f"{len(references_by_url_index[url_idx])} unique domain roots"
        )
    
    # Save to output JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(references_by_url_index, f, ensure_ascii=False, indent=2)
    
    print(f"[{platform_name}] Saved reference domains to {output_json_path}")


def main():
    """Main entry point for reference domain extraction."""
    wiki_parsed = "data/outputs/wikipedia_parsed.json"
    grok_parsed = "data/outputs/grokipedia_parsed.json"
    wiki_urls = "data/seeds/wikipedia_urls.txt"
    grok_urls = "data/seeds/grokipedia_urls.txt"
    out_dir = "data/outputs"
    
    os.makedirs(out_dir, exist_ok=True)
    
    # Process Wikipedia
    process_platform(
        wiki_parsed,
        wiki_urls,
        os.path.join(out_dir, "wikipedia_references.json"),
        "Wikipedia",
    )
    
    # Process Grokipedia
    process_platform(
        grok_parsed,
        grok_urls,
        os.path.join(out_dir, "grokipedia_references.json"),
        "Grokipedia",
    )
    
    print("\nDone! Reference domain files created.")


if __name__ == "__main__":
    main()
