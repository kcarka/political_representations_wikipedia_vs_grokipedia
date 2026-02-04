"""Main pipeline orchestration for Wikipedia and Grokipedia data collection.

Coordinates downloading of articles from Wikipedia and Grokipedia URLs, parsing
their HTML into structured JSON, and generating spans-only JSON files for analysis.

Usage:
    python run_pipeline.py [--sources <path>] [--out-dir <path>]

The pipeline reads from a unified CSV file with columns:
    Category, Subcategory, Name, Wikipedia_URL, Grokipedia_URL

The pipeline produces:
- Raw HTML files: wikipedia_raw_<i>.html, grokipedia_raw_<i>.html
- Parsed JSON: wikipedia_parsed.json, grokipedia_parsed.json
- Spans-only JSON: wikipedia_spans_<slug>.json, grokipedia_spans_<slug>.json
- Reference domains: wikipedia_references.json, grokipedia_references.json
"""

import argparse
import json
import os
import re
from typing import List, Set, Dict, Any
from urllib.parse import urlparse

import pandas as pd

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


def read_sources_csv(path: str) -> pd.DataFrame:
    """Read unified sources CSV file with metadata and URLs using pandas.
    
    Args:
        path: Path to sources.csv file.
    
    Returns:
        Pandas DataFrame with columns: Category, Subcategory, Name, 
        Wikipedia_URL, Grokipedia_URL. Column names are preserved as-is.
    
    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
    """
    df = pd.read_csv(path)
    # Strip whitespace from all columns
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def extract_domain_root(url: str) -> str:
    """Extract domain root from a URL without scheme and common prefixes.
    
    Converts https://www.theguardian.com/us-news/2023/... to theguardian.com
    Converts https://news.yahoo.com/article to yahoo.com
    Handles malformed domains like www..cnn.com
    
    Args:
        url: Full URL string.
    
    Returns:
        Domain root without scheme/www/news prefixes, or empty string if parsing fails.
    """
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            domain = parsed.netloc
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            # Remove news. prefix if present
            if domain.startswith("news."):
                domain = domain[5:]
            # Replace multiple consecutive dots with a single dot
            domain = re.sub(r'\.+', '.', domain)
            # Remove leading/trailing dots
            domain = domain.strip('.')
            return domain
        return ""
    except Exception:
        return ""


def extract_reference_domains(articles: List[dict], urls: List[str], out_dir: str, platform_name: str) -> None:
    """Extract and save domain roots from references indexed by URL.
    
    Creates a JSON list where index i contains unique domain roots from references
    for the article originally crawled from urls[i].
    
    Args:
        articles: List of parsed article dictionaries with 'url' and 'references' keys.
        urls: List of seed URLs used for scraping.
        out_dir: Output directory for JSON file.
        platform_name: Platform name for naming output file ('wikipedia' or 'grokipedia').
    """
    # Initialize reference list for each URL index
    references_by_url_index: List[Set[str]] = [set() for _ in range(len(urls))]
    
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
                if domain_root:
                    references_by_url_index[url_idx].add(domain_root)
        
        print(
            f"[{platform_name}] Article {article_idx} (URL index {url_idx}): "
            f"{len(references_by_url_index[url_idx])} unique domain roots"
        )
    
    # Convert sets to sorted lists for JSON serialization
    references_list = [sorted(list(domain_set)) for domain_set in references_by_url_index]
    
    # Save to output JSON
    output_path = os.path.join(out_dir, f"{platform_name}_references.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(references_list, f, ensure_ascii=False, indent=2)
    
    print(f"[{platform_name}] Saved reference domains to {output_path}")


def analyze_political_leaning(df: pd.DataFrame, out_dir: str) -> None:
    """Analyze political leaning of Wikipedia and Grokipedia reference sources.
    
    For each article in sources.csv, examines the political bias distribution of cited
    references by mapping reference domains against the mbfc.csv media bias database.
    Categorizes references as Left, Center, Right, or Other (not found in database).
    
    Compares reference bias distributions between Wikipedia and Grokipedia to assess
    differences in source selection and representational balance.
    
    Args:
        df: pandas DataFrame with columns: Name, Category, Subcategory, Wikipedia_URL, Grokipedia_URL
        out_dir: Output directory containing wikipedia_references.json and grokipedia_references.json
    
    Process:
        1. Loads mbfc.csv (Media Bias/Fact Check database) mapping domains to bias
        2. Loads reference domain lists from wikipedia_references.json and grokipedia_references.json
        3. For each reference domain, looks up its bias classification from mbfc.csv
        4. Normalizes bias categories: left/left-center → Left, center/neutral → Center,
                                      right/right-center → Right, unmapped → Other
        5. Aggregates reference counts by bias for each article
        6. Logs unmapped domains to console for debugging
        7. Exports results to political_leaning.csv
    
    Output columns (political_leaning.csv):
        - Name: Article name
        - Category: Article category (Politician/Institution/Law)
        - Subcategory: Specific subcategory
        - Wikipedia_Left/Center/Right/Other: Reference counts by bias
        - Grokipedia_Left/Center/Right/Other: Reference counts by bias
    
    Note:
        Unmapped domains (not in mbfc.csv) are categorized as "Other" and printed to console.
    """
    print("Loading media bias database from mbfc.csv...")
    
    # Load media bias database
    mbfc_path = "data/mbfc.csv"
    if not os.path.exists(mbfc_path):
        print(f"Error: Media bias database not found at {mbfc_path}")
        return
    
    mbfc_df = pd.read_csv(mbfc_path)
    print(f"Loaded {len(mbfc_df)} media sources from {mbfc_path}")
    
    # Build domain-to-bias mapping
    domain_to_bias = {}
    for _, row in mbfc_df.iterrows():
        source = row.get("source", "").strip()
        bias = row.get("bias", "unknown").strip().lower()
        
        # Normalize bias to Left/Center/Right
        if "left" in bias:
            normalized_bias = "Left"
        elif "right" in bias:
            normalized_bias = "Right"
        elif "center" in bias or "neutral" in bias:
            normalized_bias = "Center"
        else:
            normalized_bias = "Other"
        
        domain_to_bias[source] = normalized_bias
    
    print(f"Mapped {len(domain_to_bias)} domains to political bias")
    
    # Load reference domain lists indexed by source
    wiki_refs_path = os.path.join(out_dir, "wikipedia_references.json")
    grok_refs_path = os.path.join(out_dir, "grokipedia_references.json")
    
    wiki_refs = []
    grok_refs = []
    
    if os.path.exists(wiki_refs_path):
        with open(wiki_refs_path, "r", encoding="utf-8") as f:
            wiki_refs = json.load(f)
        print(f"Loaded {len(wiki_refs)} Wikipedia reference lists")
    
    if os.path.exists(grok_refs_path):
        with open(grok_refs_path, "r", encoding="utf-8") as f:
            grok_refs = json.load(f)
        print(f"Loaded {len(grok_refs)} Grokipedia reference lists")
    
    # Analyze political leaning for each source
    results = []
    not_found_domains = set()  # Track domains not in mbfc.csv
    
    for idx, row in df.iterrows():
        name = row["Name"]
        category = row["Category"]
        subcategory = row.get("Subcategory", "")
        
        # Count biases for Wikipedia references
        wiki_left, wiki_center, wiki_right, wiki_other = 0, 0, 0, 0
        if idx < len(wiki_refs):
            for domain in wiki_refs[idx]:
                bias = domain_to_bias.get(domain)
                if bias is None:
                    not_found_domains.add(domain)
                    wiki_other += 1
                elif bias == "Left":
                    wiki_left += 1
                elif bias == "Center":
                    wiki_center += 1
                elif bias == "Right":
                    wiki_right += 1
                else:
                    wiki_other += 1
        
        # Count biases for Grokipedia references
        grok_left, grok_center, grok_right, grok_other = 0, 0, 0, 0
        if idx < len(grok_refs):
            for domain in grok_refs[idx]:
                bias = domain_to_bias.get(domain)
                if bias is None:
                    not_found_domains.add(domain)
                    grok_other += 1
                elif bias == "Left":
                    grok_left += 1
                elif bias == "Center":
                    grok_center += 1
                elif bias == "Right":
                    grok_right += 1
                else:
                    grok_other += 1
        
        results.append({
            "Name": name,
            "Category": category,
            "Subcategory": subcategory,
            "Wikipedia_Left": wiki_left,
            "Wikipedia_Center": wiki_center,
            "Wikipedia_Right": wiki_right,
            "Wikipedia_Other": wiki_other,
            "Grokipedia_Left": grok_left,
            "Grokipedia_Center": grok_center,
            "Grokipedia_Right": grok_right,
            "Grokipedia_Other": grok_other,
        })
        
        print(f"[{idx}] {name}: Wiki(L={wiki_left}, C={wiki_center}, R={wiki_right}), "
              f"Grok(L={grok_left}, C={grok_center}, R={grok_right})")
    
    # Report domains not found in mbfc.csv
    # if not_found_domains:
    #     print(f"\n--- Domains NOT found in mbfc.csv (categorized as 'Other'): {len(not_found_domains)} ---")
    #     for domain in sorted(not_found_domains):
    #         print(f"  - {domain}")
    # else:
    #     print("\n✓ All reference domains found in mbfc.csv!")
    
    # Create DataFrame and save
    df_result = pd.DataFrame(results)
    output_path = os.path.join(out_dir, "political_leaning.csv")
    df_result.to_csv(output_path, index=False)
    
    print(f"\nSaved political leaning analysis to {output_path}")
    print(f"Total entries: {len(df_result)}")


def main():
    """Main entry point for the data collection and analysis pipeline.
    
    Orchestrates the complete workflow:
    1. Reads unified sources CSV with Wikipedia/Grokipedia URL pairs
    2. Optionally downloads and parses articles (or reuses existing parsed JSON with --skip-crawl)
    3. Extracts reference domain roots from parsed articles
    4. Analyzes media bias distribution by mapping reference domains to mbfc.csv classifications
    5. Generates political_leaning.csv with bias distribution across Wikipedia and Grokipedia
    
    Command-line arguments:
        --sources: Path to CSV file with columns: Category, Subcategory, Name, Wikipedia_URL, Grokipedia_URL
                  Default: data/seeds/sources.csv
        --out-dir: Output directory for parsed JSON and analysis CSV files
                  Default: data/outputs
        --skip-crawl: Skip downloading/parsing; reuse existing wikipedia_parsed.json and grokipedia_parsed.json
                     Default: False (perform full download and parse)
    
    Expected files:
        - data/seeds/sources.csv: Source list with URLs (required)
        - data/mbfc.csv: Media Bias/Fact Check database with columns: source, bias, factual_reporting (required for analysis)
        - data/outputs/wikipedia_parsed.json: Cached parsed Wikipedia (only used with --skip-crawl)
        - data/outputs/grokipedia_parsed.json: Cached parsed Grokipedia (only used with --skip-crawl)
    
    Output files:
        - political_leaning.csv: Bias distribution analysis (Left/Center/Right reference counts)
        - wikipedia_parsed.json: Hierarchical Wikipedia articles with sections and references
        - grokipedia_parsed.json: Hierarchical Grokipedia articles with sections and references
        - wikipedia_references.json: Domain lists indexed by source row
        - grokipedia_references.json: Domain lists indexed by source row
        - wikipedia_spans_<idx>_<name>.json: Clean paragraph text per article
        - grokipedia_spans_<idx>_<name>.json: Clean span text per article
    
    Note:
        Missing reference domains in mbfc.csv are logged and categorized as "Other" in the output.
    """
    parser = argparse.ArgumentParser(description="Download and parse articles from Wikipedia and Grokipedia, analyze reference distribution.")
    parser.add_argument("--sources", default="data/seeds/sources.csv", help="Path to unified sources CSV file")
    parser.add_argument("--out-dir", default="data/outputs", help="Output directory for results")
    parser.add_argument("--skip-crawl", action="store_true", help="Skip downloading and parsing; reuse existing parsed JSON files")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Read unified sources CSV
    if not os.path.exists(args.sources):
        print(f"Error: Sources file not found at {args.sources}")
        return
    
    df = read_sources_csv(args.sources)
    print(f"Read {len(df)} sources from {args.sources}")
    print(f"Columns: {list(df.columns)}")
    
    # Extract Wikipedia and Grokipedia URLs in order
    wiki_urls = df["Wikipedia_URL"].tolist()
    grok_urls = df["Grokipedia_URL"].tolist()
    
    parsed_wiki: List[Dict[str, Any]] = []
    parsed_grok: List[Dict[str, Any]] = []

    # Skip crawl: load existing parsed JSON
    if args.skip_crawl:
        print("\n--- Loading existing parsed data (skipping crawl) ---")
        wiki_parsed_path = os.path.join(args.out_dir, "wikipedia_parsed.json")
        grok_parsed_path = os.path.join(args.out_dir, "grokipedia_parsed.json")
        
        if os.path.exists(wiki_parsed_path):
            with open(wiki_parsed_path, "r", encoding="utf-8") as f:
                parsed_wiki = json.load(f)
            print(f"Loaded {len(parsed_wiki)} Wikipedia articles from {wiki_parsed_path}")
        
        if os.path.exists(grok_parsed_path):
            with open(grok_parsed_path, "r", encoding="utf-8") as f:
                parsed_grok = json.load(f)
            print(f"Loaded {len(parsed_grok)} Grokipedia articles from {grok_parsed_path}")
    else:
        # Normal flow: download and parse
        print(f"\nProcessing {len(wiki_urls)} Wikipedia and {len(grok_urls)} Grokipedia articles...")
        
        # Process Wikipedia
        print("\n--- Downloading Wikipedia articles ---")
        for i, row in df.iterrows():
            url = row["Wikipedia_URL"]
            name = row["Name"]
            category = row["Category"]
            subcategory = row["Subcategory"]
            
            print(f"[{i}] Fetching Wikipedia: {name}")
            articles = scrape_wikipedia_from_urls([url])
            if not articles or not articles[0].raw_html:
                print(f"  Skip: no article returned")
                continue
            
            raw_html = articles[0].raw_html
            # out_path = os.path.join(args.out_dir, f"wikipedia_raw_{i}.html")
            # with open(out_path, "w", encoding="utf-8") as f:
            #     f.write(raw_html)
            # print(f"  Saved raw HTML (len={len(raw_html)})")

            # Parse content
            parsed = parse_wikipedia_article(raw_html)
            parsed["url"] = url
            parsed["index"] = i
            parsed["category"] = category
            parsed["subcategory"] = subcategory
            parsed["name"] = name
            parsed_wiki.append(parsed)
            print(f"  Parsed: {len(parsed.get('sections', []))} sections, {len(parsed.get('references', []))} references")

        # Process Grokipedia
        print("\n--- Downloading Grokipedia articles ---")
        for i, row in df.iterrows():
            url = row["Grokipedia_URL"]
            name = row["Name"]
            category = row["Category"]
            subcategory = row["Subcategory"]
            
            print(f"[{i}] Fetching Grokipedia: {name}")
            articles = scrape_grokipedia_from_urls([url])
            if not articles or not articles[0].raw_html:
                print(f"  Skip: no article returned")
                continue
            
            raw_html = articles[0].raw_html
            # out_path = os.path.join(args.out_dir, f"grokipedia_raw_{i}.html")
            # with open(out_path, "w", encoding="utf-8") as f:
            #     f.write(raw_html)
            # print(f"  Saved raw HTML (len={len(raw_html)})")

            # Parse content
            parsed = parse_grokipedia_article(raw_html)
            parsed["url"] = url
            parsed["index"] = i
            parsed["category"] = category
            parsed["subcategory"] = subcategory
            parsed["name"] = name
            parsed_grok.append(parsed)
            print(f"  Parsed: {len(parsed.get('sections', []))} sections, {len(parsed.get('references', []))} references")

        # Save parsed Wikipedia JSON if any
        if parsed_wiki:
            parsed_path = os.path.join(args.out_dir, "wikipedia_parsed.json")
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(parsed_wiki, f, ensure_ascii=False, indent=2)
            print(f"\nSaved parsed Wikipedia JSON to {parsed_path} ({len(parsed_wiki)} articles)")

            # Also write paragraphs-only files per article
            for item in parsed_wiki:
                name = item.get("name", "page").replace(" ", "_")
                idx = item.get("index", 0)
                
                # Aggregate all paragraphs from sections, subsections, and sub-subsections
                paragraphs: List[str] = []
                for section in item.get("sections", []) or []:
                    paragraphs.extend(section.get("paragraphs", []) or [])
                    for sub in section.get("subsections", []) or []:
                        paragraphs.extend(sub.get("paragraphs", []) or [])
                        for subsub in sub.get("subsections", []) or []:
                            paragraphs.extend(subsub.get("paragraphs", []) or [])

                paragraphs_filename = f"wikipedia_spans_{idx}_{name}.json"
                paragraphs_path = os.path.join(args.out_dir, paragraphs_filename)
                with open(paragraphs_path, "w", encoding="utf-8") as f:
                    json.dump(paragraphs, f, ensure_ascii=False, indent=2)
                print(f"Saved Wikipedia spans to {paragraphs_filename} (count={len(paragraphs)})")

        # Save parsed Grokipedia JSON if any
        if parsed_grok:
            parsed_path = os.path.join(args.out_dir, "grokipedia_parsed.json")
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(parsed_grok, f, ensure_ascii=False, indent=2)
            print(f"\nSaved parsed Grokipedia JSON to {parsed_path} ({len(parsed_grok)} articles)")

            # Also write spans-only files per article
            for item in parsed_grok:
                name = item.get("name", "page").replace(" ", "_")
                idx = item.get("index", 0)
                
                # Aggregate all spans from sections and subsections
                spans: List[str] = []
                for section in item.get("sections", []) or []:
                    spans.extend(section.get("spans", []) or [])
                    for sub in section.get("subsections", []) or []:
                        spans.extend(sub.get("spans", []) or [])

                spans_filename = f"grokipedia_spans_{idx}_{name}.json"
                spans_path = os.path.join(args.out_dir, spans_filename)
                with open(spans_path, "w", encoding="utf-8") as f:
                    json.dump(spans, f, ensure_ascii=False, indent=2)
                print(f"Saved Grokipedia spans to {spans_filename} (count={len(spans)})")
        
        # Extract and save reference domain roots indexed by source index
        print("\n--- Extracting reference domain roots ---")
        if parsed_wiki:
            extract_reference_domains(parsed_wiki, wiki_urls, args.out_dir, "wikipedia")
        if parsed_grok:
            extract_reference_domains(parsed_grok, grok_urls, args.out_dir, "grokipedia")
    
    # Analyze reference distribution
    print("\n--- Analyzing reference distribution ---")
    analyze_political_leaning(df, args.out_dir)
    
    print("\nPipeline complete!")


if __name__ == "__main__":
    main()
