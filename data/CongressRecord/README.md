# Congressional Record Dataset

## Overview

This directory contains linguistic data extracted from the U.S. Congressional Record, spanning from the 43rd to the 114th Congress. The dataset enables quantitative analysis of political language and partisan rhetoric through structured bigram (two-word phrase) analysis.

## Vocabulary Files

These files contain cleaned and processed bigrams used in Congressional speech analysis.

### master_list.txt

**Purpose**: Complete inventory of all extracted bigrams with quality classification labels.

**Content**: All bigrams with associated quality flags indicating exploitability for analysis.

**Classification Labels**:
- `bad_syntax`: Bigrams with syntactic irregularities that compromise linguistic validity
- `number`: Bigrams containing numerical tokens (e.g., "year 2020")
- `foreign`: Bigrams containing non-English terms

**Use Case**: Reference for data quality control and filtering decisions.

### vocab.txt

**Purpose**: Curated vocabulary of valid bigrams suitable for ideological analysis.

**Content**: Thousands of stemmed bigrams that have passed syntactic and procedural validation.

**Key Properties**:
- Free of syntactic irregularities
- Stemmed for linguistic normalization (e.g., "running", "runs" → "run")
- Excludes procedural/parliamentary language
- Contains no inherent ideological information

**Use Case**: Primary vocabulary for building NLP models and filtering article content.

### procedural.txt

**Purpose**: Exclusion list for procedural, parliamentary, and structural language.

**Content**: Bigrams that reflect parliamentary procedures rather than substantive political positions.

**Examples of Procedural Language**:
- "mr speaker", "madam president"
- "motion to", "propose to"
- "committee on", "bill to"

**Use Case**: Data cleaning and filtering—these phrases are excluded when diagnosing article ideology to prevent false bias signals from legislative mechanics rather than political content.

**Importance**: Critical for distinguishing between genuine partisan language and neutral procedural discourse.

## Phrase Partisanship Data

### Structure

The `phrase_partisanship/` directory contains one file per Congress (43rd through 114th), with filenames following the pattern: `partisan_phrases_NNN.txt`

### Content Format

Each file contains bigrams paired with **partisanship scores** that quantify the partisan associations of phrases based on usage frequency in Congressional speeches.

**File Structure**:
- Format: Pipe-delimited (`|`)
- Columns: `phrase | partisanship`

### Interpretation of Scores

**Partisanship Score Scale**: [-1, 1]

- **Positive values**: Phrases used more frequently by Republican speakers
  - Higher values = Stronger Republican association
  - Example: "free market" (hypothetical)

- **Negative values**: Phrases used more frequently by Democratic speakers
  - Lower values = Stronger Democratic association
  - Example: "social safety" (hypothetical)

- **Values near 0**: Bipartisan language with minimal partisan skew

### Methodology

The partisanship scores are derived by:
1. Counting frequency of each bigram in Republican vs. Democratic speeches
2. Retrieve a partisan slant metric based
3. Normalizing scores to the [-1, 1] range for interpretability

### Usage Notes

- **Multiple Congresses**: Averaging scores across multiple Congressional sessions (e.g., 110th-114th) produces robust, time-stable partisan measures less susceptible to single-session anomalies
- **Context Matters**: Partisanship scores reflect *how* Congress uses language, not absolute semantic meaning
- **Bigram Focus**: Two-word phrases capture semantic relationships better than single words while remaining computationally tractable

## Application

These data files are used in conjunction with the [Gentzkow-Shapiro methodology](../bias_localization/README.md) to measure and localize political bias in external text sources (e.g., Wikipedia articles, Grokipedia content) by identifying which partisan phrases appear and weighting them by frequency.

## Related Resources

- **Source**: Gentzkow, M., Shapiro, J. M., & Taddy, M. (2020). Congressional Record for the 43rd-114th Congresses: Parsed Speeches and Phrase Counts. Stanford Data Repository.
- **URL**: https://data.stanford.edu/congress_text