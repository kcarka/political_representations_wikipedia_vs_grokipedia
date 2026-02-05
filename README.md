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
pip install vaderSentiment
```
If PowerShell blocks script execution, enable local scripts once:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

### Step 5: Deactivate the Virtual Environment (Optional)

When you are finished working in the virtual environment, you can deactivate it by running:

```bash
deactivate
```

This returns you to your system Python environment.

## Pipeline Quickstart

The initial data pipeline implements:
- Scraping matched article pairs from provided Wikipedia and Grokipedia URLs
- Extracting main text content and cited references
- Cleaning text (lowercasing, stopword removal, lemmatization via `nltk`)
- Mapping reference URLs to media domains and example bias/factuality scores

### Configure seeds

Provide matched URL pairs by line order:
- Line N in [data/seeds/wikipedia_urls.txt](data/seeds/wikipedia_urls.txt) pairs with line N in [data/seeds/grokipedia_urls.txt](data/seeds/grokipedia_urls.txt)
- Example:
  - Wikipedia line 1: `https://en.wikipedia.org/wiki/Donald_Trump`
  - Grokipedia line 1: `https://grokipedia.com/page/Donald_Trump`
- Optional: extend media score mappings at [data/media_scores.json](data/media_scores.json)

### Run the pipeline

```bash
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python run_pipeline.py
```

Outputs will be saved to `data/outputs/`:
- `pairs.json` — matched article pairs with cleaned text and annotated references

Notes:
- Wikipedia scraping uses direct page fetch plus MediaWiki API fallbacks to extract article text from `mw-parser-output`.
- Grokipedia scraping is generic HTML extraction. If Grokipedia has a specific structure, update `pipeline/scrape.py` accordingly.
- Pairs with empty text in either article are skipped.
