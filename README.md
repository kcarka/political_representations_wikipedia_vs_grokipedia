# Political domain representations in Grokipedia vs. english Wikipedia

This repository implements a comparative analysis methodology for assessing political representation across two online encyclopedic platforms, **Wikipedia** and **Grokipedia**. Given the significant influence these platforms have on public opinions and their utilization in training large language models, our study seeks to disaggregate the nuanced differences in political coverage between them. Through systematic comparisons, we aim to uncover the underlying mechanisms of divergence in portrayals of political actors and events. 

## Table of Contents
- [Research Questions](#research-questions)
- [Modules Overview](#modules-overview)
  - [Data Selection and Preparation](#1-data-selection-and-preparation)
  - [Bias Localization Module](#2-bias-localization-module)
  - [Type Consistency Module](#3-type-consistency-module)
  - [Reference Module](#4-reference-module)
  - [Statistical Validation](#5-statistical-validation)
  - [Synthesis and Research Question Mapping](#6-synthesis-and-research-question-mapping)
- [Installation Instructions](#installation-instructions)
 - [Pipeline Quickstart](#pipeline-quickstart)
 - [Installation Instructions](#Installation-Instructions)

## Research Questions

Our analysis focuses on three key research questions that guide the exploration of content differences between Grokipedia and Wikipedia:

1. **RQ1:** Where do divergences mainly arise? Are they concentrated in specific claims or sections, or spread across the article?
   
2. **RQ2:** Are divergences consistent across types of political articles, or do they vary systematically by category?
   
3. **RQ3:** How do sourcing practices, including quantity, political orientation, credibility or factuality, and diversity or overlap, shape perceived neutrality and help explain content differences?

## Modules Overview

The implementation consists of a modular pipeline designed to facilitate detailed analysis across multiple dimensions. Each module corresponds to specific components of the research methodology outlined in the report. Below are the key modules included in our implementation:

### 1. Data Selection and Preparation
- **Task:** Collect and pair matched U.S. political articles from Grokipedia and Wikipedia based on topical similarity.
- **Functions:**
  - Web scraping to gather political articles.
  - Data cleaning and preprocessing, including lowercasing, stopword removal, and lemmatization.

### 2. Bias Localization Module
- **Task:** Identify where divergences appear within articles at varying levels of granularity (article, paragraph, sentence).
- **Functions:**
  - Compute slant scores and sentiment analyses using methods like VADER.
  - Implement Named Entity Recognition (NER) to analyze mention patterns of political actors and institutions.

### 3. Type Consistency Module
- **Task:** Evaluate whether observed divergences remain significant across different political article categories (e.g., biographies, policies, events, institutions).
- **Functions:**
  - Classify articles by type.
  - Conduct statistical tests (Wilcoxon signed-rank tests) to assess consistency across categories.

### 4. Reference Module
- **Task:** Analyze sourcing practices and their impact on perceived neutrality.
- **Functions:**
  - Map cited sources to bias scores from the News Media Bias and Factuality dataset.
  - Compute average bias of references for each article and analyze correlations with article-level slant.

### 5. Statistical Validation
- **Task:** Validate findings using statistical methods to ensure robustness in results.
- **Functions:**
  - Apply paired t-tests and Wilcoxon signed-rank tests to compare overall slant and sentiment between matched articles.

### 6. Synthesis and Research Question Mapping
- **Task:** Combine insights from all analytical modules to comprehensively address the research questions.
- **Functions:**
  - Aggregate findings to see where divergences primarily arise, assess structural consistency, and clarify sourcing influences.
 

## Installation Instructions

Follow these steps to set up a virtual environment and install the required packages for this project:

### Step 1: Clone the Repository

First, clone the repository to your local machine:

```bash
git clone <repository_url>
cd <repository_directory>
```

### Step 2: Create a Virtual Environment

Next, create a virtual environment using the `venv` module. This helps to manage dependencies without interfering with your system Python installation:

```bash
python -m venv venv
```

This command creates a new directory called `venv` in your project folder.

### Step 3: Activate the Virtual Environment

Activate the virtual environment with the following command, depending on your operating system:

- **On Windows:**
  ```bash
  venv\Scripts\activate
  ```

- **On macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

### Step 4: Install Required Packages

Once the virtual environment is activated, install the necessary packages from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### Step 5: Deactivate the Virtual Environment (Optional)

When you are finished working in the virtual environment, you can deactivate it by running:

```bash
deactivate
```

This returns you to your system Python environment.

## Pipeline Quickstart

This repository now supports an **index-based, type-stratified pipeline**
that supersedes the earlier seed-based URL pairing approach.
The new pipeline enables scalable, balanced, and reproducible comparisons
between Grokipedia and English Wikipedia.

---

### Overview of the Updated Pipeline

The current pipeline implements the following stages:

1. **Category-based article discovery from Wikipedia**
2. **Automatic pairing with Grokipedia pages**
3. **Type-stratified quota balancing**
4. **Article scraping and parsing**
5. **Paragraph-level alignment**
6. **Statistical and qualitative bias analysis**

The earlier manual seed files (`wikipedia_urls.txt`, `grokipedia_urls.txt`)
are no longer required for the main analysis.

---

### Step 1: Discover Matched Article Pairs by Political Type

Articles are discovered via Wikipedia category crawling and assigned to one of
four semantic types:

- **biography** (political actors)
- **institution** (political organizations, systems)
- **law** (constitutional and statutory texts)
- **event** (elections, controversies, crises)

Example: discovering political biographies

```powershell
python -m pair_discovery.build_pairs_index `
  --category "Category:American politicians" `
  --limit 120 `
  --out data\indices\index_bio.jsonl `
  --manifest data\indices\manifest_bio.json
```

Example: discovering legal domain articles
```powershell
python -m pair_discovery.build_pairs_index `
  --category "Category:United States constitutional law" `
  --limit 120 `
  --out data\indices\index_law.jsonl `
  --manifest data\indices\manifest_law.json
```
Equivalent commands can be run for institutions and events.

### Step 2: Merge Indices with Type-Balanced Quotas

To avoid dominance by any single article type, discovered indices are merged
using quota-based stratification:
```powershell
python -m pair_discovery.merge_and_quota_index `
  --bio data\indices\index_bio.jsonl `
  --inst data\indices\index_inst.jsonl `
  --law data\indices\index_law.jsonl `
  --event data\indices\index_event.jsonl `
  --quota 30 `
  --out data\indices\pairs_index_balanced.jsonl `
  --manifest data\indices\manifest_balanced.json
```
This produces a balanced index suitable for cross-type comparison.

### Step 3: Export Paired Seeds and Scrape Articles

The balanced index is converted into paired URLs and used to fetch articles
from both platforms:
```powershell
python -m pair_discovery.export_seeds_from_index `
  --index data\indices\pairs_index_balanced.jsonl `
  --out_dir data\seeds `
  --max_pairs 0

python run_pipeline.py
```
This step downloads raw HTML and parses article content and structure.

### Step 4: Build Paragraph-Level Paired Dataset

Parsed articles are aligned into paragraph-level pairs:
```powershell
python -m pair_discovery.build_pairs_dataset `
  --meta data\seeds\pairs_meta.jsonl `
  --outputs_dir data\outputs `
  --out data\outputs\pairs_dataset.jsonl
```
Each entry contains: article title、semantic type、source platform、paragraph text、paragraph position

### Step 5: Type-Stratified Sentiment Analysis

Sentiment scores are computed using VADER and compared in a paired setting:
```
python analysis/type_stratified_vader.py
```
Output:
```
data/outputs/type_stratified_vader.csv
```
This module reports type-specific mean differences, paired t-tests, and
Wilcoxon signed-rank tests between Wikipedia and Grokipedia.

### Step 6: Qualitative Bias Localization (Biographies)

To localize divergence within articles, paragraph-level evidence is extracted
from biographies:
```
python analysis/biography_topk_paragraph_diff.py
```
Output:
```
data/outputs/biography_topk_negative_paragraphs.json
```
This file highlights Top-K paragraphs exhibiting the largest sentiment gaps,
enabling qualitative inspection of narrative framing differences.

### Reproducibility Notes

Generated data (data/outputs, data/indices, data/cache) are excluded via .gitignore.

All analyses are deterministic given fixed indices.

This study relies exclusively on the index-based, type-stratified pipeline described above.

