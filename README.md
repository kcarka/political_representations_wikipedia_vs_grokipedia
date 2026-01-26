# Political domain representations Grokipedia vs. english Wikipedia

This repository implements a comparative analysis methodology for assessing political representation across two online encyclopedic platforms, **Wikipedia** and **Grokipedia**. Given the significant influence these platforms have on public opinions and their utilization in training large language models, our study seeks to disaggregate the nuanced differences in political coverage between them. Through systematic comparisons, we aim to uncover the underlying mechanisms of divergence in portrayals of political actors and events. 

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

