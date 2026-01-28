# Bias Localization Using the Gentzkow-Shapiro Method

## Overview

This module implements bias localization techniques based on the methodological framework established by **Gentzkow and Shapiro (2010)** and extended through the **Congressional Record dataset** compiled by Gentzkow, Shapiro, and Taddy (2020). The approach enables quantitative measurement and localization of political bias in textual content by leveraging partisan language patterns derived from historical Congressional speeches.

## Methodology

### Conceptual Foundation

The Gentzkow-Shapiro method measures political bias by identifying phrases that exhibit partisan usage patterns. The core insight is that certain bigrams (two-word phrases) are used with significantly different frequencies by Republican and Democratic speakers in the U.S. Congress. These "partisan phrases" serve as linguistic markers that can be used to assess the political slant of any given text.

**Key References:**
- Gentzkow, M., & Shapiro, J. M. (2010). What drives media slant? Evidence from U.S. daily newspapers. *Econometrica*, 78(1), 35–71.
- Gentzkow, M., Shapiro, J. M., & Taddy, M. (2020). Congressional Record for the 43rd-114th Congresses: Parsed Speeches and Phrase Counts. Stanford Data Repository. Retrieved from https://data.stanford.edu/congress_text

### Implementation in `gentzkow_shapiro.py`

The implementation consists of the following components:

#### 1. **Congressional Record Vocabulary Extraction**
```python
import_extract_Congress_Record_vocabulary()
```
- Downloads the phrase partisanship dataset from Stanford Data Repository
- Extracts partisan phrases from multiple Congressional sessions (110th-114th Congresses)
- Creates a master dataframe containing:
  - **phrases**: Stemmed bigrams from Congressional speeches
  - **ideologies**: Partisanship scores normalized to the [-1, 1] range
    - Negative values indicate Democratic-leaning language
    - Positive values indicate Republican-leaning language
- Averaging ideology scores across multiple Congresses produces robust, time-stable measurements

#### 2. **Text Preprocessing Pipeline**
```python
preprocessing_article(content, df_congress)
```

The preprocessing pipeline transforms raw article text into a structured analysis format through multiple linguistic processing steps:

**Normalization:**
- Lowercasing all text
- Tokenization using regex pattern matching (`\w+`)
- Removal of English stop words (common words with minimal semantic content)

**Linguistic Normalization:**
- **Stemming** using Porter Stemmer algorithm to reduce words to their linguistic roots
  - Example: "running", "runs", "ran" → "run"
  - Benefits: Captures variants of the same concept and reduces vocabulary sparsity

**Feature Extraction:**
- **Bigram Construction**: Creates ordered pairs of adjacent stemmed tokens
  - Bigrams capture phrase-level semantics better than unigrams
  - Example: "political representation" captures more meaning than isolated words

**Vocabulary Alignment:**
- Filters bigrams to only those present in the Congressional Record vocabulary
- Ensures only partisan phrases with established ideological scores are included

**Quantification:**
- **Relative Frequency**: Proportion of each phrase within the article's bigram set
  - Accounts for article length variations
  - Formula: count(phrase) / total_bigrams_in_article

- **TF-IDF Scoring**: Term Frequency-Inverse Document Frequency weighting
  - Emphasizes phrases that are both frequent in the article and distinctive
  - Reduces weight of overly common phrases

**Output:**
- DataFrame with columns:
  - `phrase`: The partisan bigram
  - `relative_frequency`: Normalized frequency within the article
  - `tf-idf`: Term Frequency-Inverse Document Frequency score

#### 3. **Ideology Estimation** (Framework for Extension)
```python
estimate_ideology_article()
```
This function provides a framework for aggregating phrase-level partisanship scores to produce an article-level ideology estimate. Implementation would typically:
- Aggregate ideology scores of detected partisan phrases weighted by relative frequency or TF-IDF
- Produce a single ideology score for the article on the [-1, 1] scale
- Classify the article as Democratic-leaning, Republican-leaning, or neutral based on threshold

## Key Features

- **Principled Measurement**: Built on peer-reviewed political research
- **Lexicon-Based Approach**: Transparent and interpretable (in contrast to black-box neural methods)
- **Time-Robust**: Leverages multiple Congressional sessions to identify stable partisan language patterns
- **Fine-Grained Analysis**: Identifies *which specific phrases* contribute to bias, enabling localization and explanation

## Data Requirements

- Corpus: Raw text files to be analyzed

## Related Work

This implementation aligns with the broader literature on:
- **Media Bias Measurement** (Gentzkow & Shapiro, 2010)
- **Computational Text Analysis** for Political Science
- **NLP-based Fairness Assessment** in digital information systems

## Future Extensions

Potential enhancements could include:
- Article-level ideology aggregation and classification
- Visualization of bias localization within documents
- Cross-platform comparison (Wikipedia vs. Grokipedia)
- Integration with other bias detection methodologies

**Author Note**: This implementation aims to produce a bias quantitative analysis without reproducing exactly the method of **Gentzkow and Shapiro (2010)**.
