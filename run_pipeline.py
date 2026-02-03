"""Main pipeline orchestration for Wikipedia and Grokipedia data collection.

Coordinates downloading of articles from Wikipedia and Grokipedia URLs, parsing
their HTML into structured JSON, and generating spans-only JSON files for analysis.

Usage:
    python run_pipeline.py [--wiki-urls <path>] [--grok-urls <path>] [--out-dir <path>]

The pipeline produces:
- Raw HTML files: wikipedia_raw_<i>.html, grokipedia_raw_<i>.html
- Parsed JSON: wikipedia_parsed.json, grokipedia_parsed.json
- Spans-only JSON: wikipedia_spans_<slug>.json, grokipedia_spans_<slug>.json
"""

import argparse
import json
import os
from typing import List
from urllib.parse import urlparse

from pipeline.scrape import scrape_wikipedia_from_urls, scrape_grokipedia_from_urls
from pipeline.parse_grokipedia import parse_grokipedia_article
from pipeline.parse_wikipedia import parse_wikipedia_article


def read_lines(path: str) -> List[str]:
    """Read non-empty, non-comment lines from a text file.
    
    Args:
        path: File path to read from.
    
    Returns:
        List of stripped lines, excluding empty lines and those starting with '#'.
        Returns empty list if file doesn't exist.
    """
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def main():
    """Main entry point for the data collection pipeline.
    
    Orchestrates the full pipeline:
    1. Reads URLs from input files
    2. Downloads raw HTML from Wikipedia and Grokipedia
    3. Parses HTML into structured JSON
    4. Saves parsed JSON and spans-only JSON files
    5. Outputs file paths and counts
    """
    parser = argparse.ArgumentParser(description="Download raw HTML from Wikipedia and Grokipedia for analysis.")
    parser.add_argument("--wiki-urls", default="data/seeds/wikipedia_urls.txt")
    parser.add_argument("--grok-urls", default="data/seeds/grokipedia_urls.txt")
    parser.add_argument("--out-dir", default="data/outputs")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    wiki_urls = read_lines(args.wiki_urls)
    grok_urls = read_lines(args.grok_urls)

    if len(wiki_urls) != len(grok_urls):
        print(
            f"Warning: number of Wikipedia URLs ({len(wiki_urls)}) does not match "
            f"number of Grokipedia URLs ({len(grok_urls)}). "
            "Results may be misaligned if you assume positional pairing."
        )
    print(f"Downloading {len(wiki_urls)} Wikipedia pages and {len(grok_urls)} Grokipedia pages...")
    
    # Download raw HTML for both sources
    jobs = [
        ("Wikipedia", wiki_urls, scrape_wikipedia_from_urls, "wikipedia_raw_", True),
        ("Grokipedia", grok_urls, scrape_grokipedia_from_urls, "grokipedia_raw_", True),
    ]

    parsed_wiki: List[dict] = []
    parsed_grok: List[dict] = []

    for source_name, url_list, scraper, prefix, do_parse in jobs:
        for i, url in enumerate(url_list):
            print(f"Fetching {source_name}: {url}")
            articles = scraper([url])
            if not articles:
                print("  Skip: no article returned")
                continue
            raw_html = articles[0].raw_html
            if not raw_html:
                print("  Skip: empty raw_html")
                continue
            out_path = os.path.join(args.out_dir, f"{prefix}{i}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(raw_html)
            print(f"  Saved to {out_path} (len={len(raw_html)})")

            # Parse content if requested
            if do_parse:
                if source_name == "Wikipedia":
                    parsed = parse_wikipedia_article(raw_html)
                    parsed["url"] = url
                    parsed_wiki.append(parsed)
                elif source_name == "Grokipedia":
                    parsed = parse_grokipedia_article(raw_html)
                    parsed["url"] = url
                    parsed_grok.append(parsed)

    # Save parsed Wikipedia JSON if any
    if parsed_wiki:
        parsed_path = os.path.join(args.out_dir, "wikipedia_parsed.json")
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(parsed_wiki, f, ensure_ascii=False, indent=2)
        print(f"Saved parsed Wikipedia JSON to {parsed_path}")

        # Also write paragraphs-only files per personality (derived from URL)
        for item in parsed_wiki:
            url = item.get("url", "")
            slug = ""
            try:
                path = urlparse(url).path.rstrip("/")
                slug = path.split("/")[-1] if path else "page"
            except Exception:
                slug = "page"

            # Aggregate all paragraphs from sections, subsections, and sub-subsections
            paragraphs: List[str] = []
            for section in item.get("sections", []) or []:
                paragraphs.extend(section.get("paragraphs", []) or [])
                for sub in section.get("subsections", []) or []:
                    paragraphs.extend(sub.get("paragraphs", []) or [])
                    for subsub in sub.get("subsections", []) or []:
                        paragraphs.extend(subsub.get("paragraphs", []) or [])

            paragraphs_filename = f"wikipedia_spans_{slug}.json"
            paragraphs_path = os.path.join(args.out_dir, paragraphs_filename)
            with open(paragraphs_path, "w", encoding="utf-8") as f:
                json.dump(paragraphs, f, ensure_ascii=False, indent=2)
            print(f"Saved paragraphs to {paragraphs_path} (count={len(paragraphs)})")

    # Save parsed Grokipedia JSON if any
    if parsed_grok:
        parsed_path = os.path.join(args.out_dir, "grokipedia_parsed.json")
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(parsed_grok, f, ensure_ascii=False, indent=2)
        print(f"Saved parsed Grokipedia JSON to {parsed_path}")

        # Also write spans-only files per personality (derived from URL)
        for item in parsed_grok:
            url = item.get("url", "")
            slug = ""
            try:
                path = urlparse(url).path.rstrip("/")
                slug = path.split("/")[-1] if path else "page"
            except Exception:
                slug = "page"

            # Aggregate all spans from sections and subsections
            spans: List[str] = []
            for section in item.get("sections", []) or []:
                spans.extend(section.get("spans", []) or [])
                for sub in section.get("subsections", []) or []:
                    spans.extend(sub.get("spans", []) or [])

            spans_filename = f"grokipedia_spans_{slug}.json"
            spans_path = os.path.join(args.out_dir, spans_filename)
            with open(spans_path, "w", encoding="utf-8") as f:
                json.dump(spans, f, ensure_ascii=False, indent=2)
            print(f"Saved spans to {spans_path} (count={len(spans)})")
    
    print(f"Done. Inspect HTML files in {args.out_dir} to determine parsing strategy.")


if __name__ == "__main__":
    main()
