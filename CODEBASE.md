# Codebase Documentation

Complete overview of the Political Representation Analysis pipeline codebase.

---

## Project Overview

This pipeline analyzes political bias representation across Wikipedia and Grokipedia by:
1. Scraping matched article pairs from both platforms
2. Parsing hierarchical article structures (sections, subsections, paragraphs)
3. Extracting cited reference domains
4. Mapping references to media bias classifications (Left/Center/Right)
5. Generating comparative bias distribution analysis

---

## Directory Structure

```
.
├── README.md                      # Project overview and usage guide
├── requirements.txt               # Python package dependencies
├── run_pipeline.py               # Main pipeline orchestration script
├── extract_reference_domains.py  # Reference domain extraction utility
├── pipeline/                     # Core analysis modules
│   ├── __init__.py              # Package initialization
│   ├── scrape.py                # Wikipedia/Grokipedia web scraping
│   ├── parse_wikipedia.py       # Wikipedia HTML parser
│   ├── parse_grokipedia.py      # Grokipedia HTML parser
│   ├── text_clean.py            # Text normalization utilities
│   ├── preprocess.py            # NLP preprocessing (tokenization, lemmatization)
│   └── reference_mapping.py     # Media bias annotation utilities
└── data/
    ├── seeds/
    │   └── sources.csv          # Article URLs and metadata
    ├── mbfc.csv                 # Media Bias/Fact Check database
    └── outputs/
        ├── wikipedia_parsed.json        # Parsed Wikipedia articles
        ├── grokipedia_parsed.json       # Parsed Grokipedia articles
        ├── wikipedia_references.json    # Reference domains by source
        ├── grokipedia_references.json   # Reference domains by source
        └── political_leaning.csv        # Final bias distribution analysis
```

---

## Core Modules

### `run_pipeline.py` - Main Orchestration

**Purpose**: Coordinates entire pipeline workflow.

**Key Functions**:

- `read_sources_csv(path)` - Loads sources.csv with URL pairs and metadata
  - Returns pandas DataFrame with columns: Category, Subcategory, Name, Wikipedia_URL, Grokipedia_URL
  - Strips whitespace from all columns for consistency

- `extract_domain_root(url)` - Extracts normalized domain from URL
  - Removes scheme (https://), www/news prefixes
  - Handles malformed domains (multiple dots)
  - Example: `https://www.theguardian.com/article → theguardian.com`

- `extract_reference_domains(articles, urls, out_dir, source_name)` - Builds domain lists by source index
  - Processes parsed articles and maps reference domains
  - Indexes domains by source CSV row position
  - Saves to `wikipedia_references.json` or `grokipedia_references.json`

- `analyze_political_leaning(df, out_dir)` - Analyzes reference bias distribution
  - Loads `mbfc.csv` media bias database
  - Maps each reference domain to Left/Center/Right/Other classification
  - Aggregates counts per article across Wikipedia and Grokipedia
  - Logs unmapped domains to console for debugging
  - Outputs `political_leaning.csv` with bias distribution columns

- `main()` - Entry point handling CLI arguments
  - `--sources`: Path to sources.csv (default: data/seeds/sources.csv)
  - `--out-dir`: Output directory (default: data/outputs)
  - `--skip-crawl`: Reuse existing parsed JSON, skip download/parse
  - Orchestrates download → parse → extract → analyze workflow

---

### `pipeline/scrape.py` - Web Scraping

**Purpose**: Fetch and parse HTML from Wikipedia and Grokipedia.

**Data Structures**:

- `Article` - Dataclass representing a scraped article
  - `id`, `url`, `title`: Article identifiers
  - `source`: 'wikipedia' or 'grokipedia'
  - `categories`: Wikipedia category list
  - `topic`: Inferred topic classification
  - `raw_html`: Raw HTML content
  - `text`: Extracted plain text
  - `references`: List of reference dicts with 'url' and 'text' keys

**Key Functions**:

- `_safe_get(url, source)` - HTTP GET with error handling
  - Applies USER_AGENT and headers to avoid blocking
  - Returns None on failure, Response on success

- `_fetch_wikipedia_html_rest(title)` - REST API fallback for Wikipedia
  - Uses MediaWiki REST API when direct GET fails
  - Handles URL encoding and API errors

- `_fetch_wikipedia_html_via_api(url)` - Last-resort MediaWiki API parse
  - Calls `/w/api.php?action=parse` endpoint
  - Extracts HTML content from JSON response

- `_clean_text_from_soup(soup)` - Extracts clean text from HTML
  - Removes tables, navboxes, scripts, styles
  - Falls back through multiple extraction strategies

- `scrape_wikipedia_from_urls(urls)` - Downloads Wikipedia articles
  - Tries direct GET → REST API → MediaWiki parse API
  - Returns list of Article objects

- `scrape_grokipedia_from_urls(urls)` - Downloads Grokipedia articles
  - Generic HTML extraction (no API available)
  - Returns list of Article objects

---

### `pipeline/parse_wikipedia.py` - Wikipedia Parser

**Purpose**: Extract hierarchical structure from Wikipedia HTML.

**Key Functions**:

- `parse_wikipedia_article(html)` - Parse Wikipedia HTML into sections and references
  - Extracts from `<div class="mw-content-container">`
  - Builds nested structure: h2 sections → h3 subsections → h4 sub-subsections
  - Collects `<p>` paragraphs under each heading level
  - Extracts reference URLs from `<span class="reference-text">` elements
  - Cleans all text through `clean_span_text()`

**Output Structure**:

```json
{
  "sections": [
    {
      "title": "Early life",
      "paragraphs": ["paragraph text..."],
      "subsections": [
        {
          "title": "Childhood",
          "paragraphs": ["..."],
          "subsections": []
        }
      ]
    }
  ],
  "references": [
    {"url": "https://example.com", "text": "Reference text"}
  ]
}
```

---

### `pipeline/parse_grokipedia.py` - Grokipedia Parser

**Purpose**: Extract hierarchical structure from Grokipedia HTML.

**Key Functions**:

- `parse_grokipedia_article(html)` - Parse Grokipedia HTML into sections and references
  - Extracts h2 sections and h3 subsections
  - Collects text spans between headings
  - Extracts references from `<div id="references">` element
  - Returns same structure as Wikipedia parser for consistency

---

### `pipeline/text_clean.py` - Text Normalization

**Purpose**: Normalize extracted text for storage and analysis.

**Constants**:

- `_CITATION_PATTERN` - Regex matching Wikipedia citations like [1], [d], [citation needed]

**Key Functions**:

- `clean_span_text(text)` - Normalize parsed text spans
  - Unescape HTML entities (&nbsp; → space)
  - Remove escaped quotes (\" → ")
  - Remove Wikipedia citation markers [1], [247], [citation needed]
  - Collapse whitespace to single spaces
  - Strip leading/trailing whitespace

---

### `pipeline/preprocess.py` - NLP Preprocessing

**Purpose**: NLTK-based text preprocessing utilities.

**Key Functions**:

- `_ensure_stopwords()` - Retrieve English stopwords
  - Auto-downloads NLTK data on first use

- `_ensure_tokenize(text)` - Tokenize text into words
  - Auto-downloads NLTK punkt model on first use

- `download_nltk_resources()` - Pre-download NLTK packages
  - Prevents first-use delays
  - Downloads: punkt, stopwords, wordnet, omw-1.4

- `clean_text(text)` - Full preprocessing pipeline
  - Lowercase text
  - Tokenize into words
  - Remove non-alphabetic tokens
  - Remove English stopwords
  - Lemmatize to base form
  - Returns space-separated tokens

---

### `pipeline/reference_mapping.py` - Media Bias Annotation

**Purpose**: Load media bias database and annotate references.

**Key Functions**:

- `load_media_scores(path)` - Load media bias database from JSON
  - Expected format: `{"domain.com": {"name": "...", "bias": "left", "factuality": "high"}}`
  - Raises FileNotFoundError or JSONDecodeError on failure

- `domain_from_url(url)` - Extract domain from URL
  - Uses tldextract library for reliable parsing
  - Returns "domain.com" format or None

- `annotate_references(references, scores)` - Augment references with bias metadata
  - Adds fields: domain, media_name, bias, factuality
  - Handles missing sources gracefully (None values)

---

### `extract_reference_domains.py` - Utility Script

**Purpose**: Standalone script for extracting reference domains (used in legacy pipeline).

**Key Functions**:

- `extract_domain_root(url)` - Extract normalized domain from URL
- `process_platform()` - Process platform-specific parsed JSON files
- `main()` - CLI entry point for standalone execution

---

## Data Files

### `data/seeds/sources.csv`

**Purpose**: Source list with URLs and metadata for article pairs.

**Columns**:
- `Category`: Politician, Institution, or Law
- `Subcategory`: Specific type (Left/Right for politicians, Government/Financial/etc.)
- `Name`: Human-readable name
- `Wikipedia_URL`: Full Wikipedia article URL
- `Grokipedia_URL`: Full Grokipedia article URL

**Example**:
```
Politician,Left,Alexandria Ocasio-Cortez,https://en.wikipedia.org/wiki/Alexandria_Ocasio-Cortez,https://grokipedia.com/page/Alexandria_Ocasio-Cortez
```

---

### `data/mbfc.csv`

**Purpose**: Media Bias/Fact Check database for reference classification.

**Columns**:
- `source`: Domain name (e.g., "cnn.com", "nytimes.com")
- `bias`: Classification (left, center, right, left-center, right-center)
- `factual_reporting`: Factuality rating (high, mixed, low)

**Usage**: Reference domains are matched against this file to determine bias classification.

---

### Output Files (data/outputs/)

#### `wikipedia_parsed.json` / `grokipedia_parsed.json`
- Full parsed articles with hierarchical sections and references
- Array of article objects with metadata (url, index, category, subcategory, name, sections, references)

#### `wikipedia_references.json` / `grokipedia_references.json`
- List of domain lists indexed by source row
- Format: `[[domain1, domain2, ...], [domain3, ...], ...]`
- Index matches source CSV row position

#### `wikipedia_spans_<idx>_<name>.json` / `grokipedia_spans_<idx>_<name>.json`
- Clean paragraph/span text per article
- Array of text strings

#### `political_leaning.csv`
- Final bias distribution analysis

**Columns**:
- `Name`: Article name
- `Category`: Category type
- `Subcategory`: Specific subcategory
- `Wikipedia_Left/Center/Right/Other`: Reference count by bias for Wikipedia
- `Grokipedia_Left/Center/Right/Other`: Reference count by bias for Grokipedia

---

## Pipeline Workflow

```
1. CLI Arguments
   └─ --sources (default: data/seeds/sources.csv)
   └─ --out-dir (default: data/outputs)
   └─ --skip-crawl (skip download/parse, reuse existing JSON)

2. Read Sources CSV
   └─ Load DataFrame with URL pairs and metadata

3a. FULL PIPELINE (default):
   ├─ Download Wikipedia articles
   ├─ Download Grokipedia articles
   ├─ Parse Wikipedia HTML → hierarchical sections + references
   ├─ Parse Grokipedia HTML → hierarchical sections + references
   ├─ Save parsed JSON (wikipedia_parsed.json, grokipedia_parsed.json)
   └─ Save spans-only JSON files per article

3b. SKIP-CRAWL (--skip-crawl):
   └─ Load existing wikipedia_parsed.json and grokipedia_parsed.json

4. Extract Reference Domains
   ├─ For each article, extract reference URLs
   ├─ Normalize domains (remove scheme, www, news prefixes)
   └─ Save domain lists indexed by source (wikipedia_references.json, grokipedia_references.json)

5. Analyze Political Leaning
   ├─ Load mbfc.csv media bias database
   ├─ For each article, map reference domains to bias classification
   ├─ Normalize bias categories: left/left-center → Left, center/neutral → Center, right/right-center → Right, unmapped → Other
   ├─ Aggregate reference counts by bias per article
   ├─ Log unmapped domains to console
   └─ Export to political_leaning.csv
```

---

## Usage Examples

### Full Pipeline (Download + Parse + Analyze)
```bash
python run_pipeline.py
```

### Skip Crawl (Reuse Existing Parsed Data)
```bash
python run_pipeline.py --skip-crawl
```

### Custom Source and Output Paths
```bash
python run_pipeline.py --sources my_sources.csv --out-dir my_output
```

### With Skip Crawl and Custom Paths
```bash
python run_pipeline.py --skip-crawl --sources my_sources.csv --out-dir my_output
```

---

## Key Implementation Details

### Wikipedia Parsing
- **HTML Container**: `<div class="mw-content-container">`
- **Sections**: h2 headings (top-level sections)
- **Subsections**: h3 headings (nested under h2)
- **Sub-subsections**: h4 headings (nested under h3)
- **Paragraphs**: `<p>` tags grouped under nearest heading
- **References**: `<span class="reference-text">` elements with `<a class="external text">` URLs

### Grokipedia Parsing
- **Sections**: h2 headings
- **Subsections**: h3 headings within section
- **Text**: `<span class="mb-4">` elements between headings
- **References**: `<div id="references">` element containing reference list

### Reference Domain Normalization
1. Parse URL to extract netloc (domain)
2. Remove scheme (https://)
3. Remove www. prefix if present
4. Remove news. prefix if present
5. Replace multiple consecutive dots with single dot
6. Strip leading/trailing dots

**Example**: `https://www..news.theguardian.com/article/page` → `theguardian.com`

### Bias Classification
- **Left**: left, left-center bias classifications
- **Center**: center, neutral, least-biased classifications
- **Right**: right, right-center bias classifications
- **Other**: Unmapped domains not found in mbfc.csv (logged to console)

---

## Error Handling

- **Missing sources.csv**: Pipeline exits with error message
- **Missing mbfc.csv**: Analyzed skipped with warning
- **Download failures**: Individual article failures don't halt pipeline
- **Parse failures**: Articles with no content are skipped
- **Unmapped reference domains**: Categorized as "Other", listed in debug output

---

## Dependencies

See `requirements.txt`:
- **beautifulsoup4**: HTML parsing
- **requests**: HTTP requests
- **pandas**: DataFrame operations for CSV handling
- **tldextract**: Domain extraction
- **nltk**: Natural language tokenization and lemmatization

---

## Notes

- All text extraction cleaned through `clean_span_text()` removing HTML entities, escaped quotes, and citations
- Reference indexes match source CSV row position (0-indexed)
- Wikipedia scraping uses fallback chain: direct GET → REST API → MediaWiki parse API
- Grokipedia uses generic HTML extraction (no API available)
- Media bias categories normalized to Left/Center/Right for comparison
- Console output includes progress indicators and debug information for troubleshooting
