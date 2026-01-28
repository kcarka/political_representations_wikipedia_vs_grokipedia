import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import nltk
nltk.download('punkt_tab')
nltk.download('stopwords')

import requests
import zipfile
import os
from pathlib import Path
import re

# Path of this file: pipeline/bias_localization/gentzkow_shapiro.py
CURRENT_FILE = Path(__file__).resolve()

# bias_localization/
BIAS_LOCALIZATION_DIR = CURRENT_FILE.parent

# pipeline/
PIPELINE_DIR = BIAS_LOCALIZATION_DIR.parent

# project root/
PROJECT_ROOT = PIPELINE_DIR.parent

# data/CongressRecord/
DATA_DIR = PROJECT_ROOT / "data" / "CongressRecord"



def import_extract_Congress_Record_vocabulary():

    print("Downloading Congress Record vocabulary dataset...")
    url = "https://stacks.stanford.edu/file/druid:md374tz9962/phrase_partisanship.zip"
    output_path =  DATA_DIR / "phrase_partisanship.zip"

    response = requests.get(url, stream=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print("Download completed.")

    extract_path = DATA_DIR /"phrase_partisanship"

    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(output_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    print("Extraction completed.")

    # Load the 5th last congress partisanship data
    congress_files = [extract_path / "partisan_phrases_114.txt", 
                      extract_path / "partisan_phrases_113.txt",
                      extract_path / "partisan_phrases_112.txt",
                      extract_path / "partisan_phrases_111.txt",
                      extract_path / "partisan_phrases_110.txt"]
    dataframes = [pd.read_csv(file, sep="|", header=0) for file in congress_files]
    phrases = []
    ideologies = []
    for dataframe in dataframes:
        for phrase, partisanship in zip(dataframe["phrase"], dataframe["partisanship"]):
            if phrase in phrases:
                ideologies[phrases.index(phrase)].append(partisanship)
            else:
                phrases.append(phrase)
                ideologies.append([partisanship])
    ideologies = [np.mean(ideology) for ideology in ideologies]
    # Standardize ideologies to have [-1, 1] range
    min_ideology = min(ideologies)
    max_ideology = max(ideologies)
    ideologies = [(ideology - min_ideology) / (max_ideology - min_ideology) * 2 - 1 for ideology in ideologies]
    # Create dataframe
    data = {
        "phrases": phrases,
        "ideologies": ideologies
    }
    df = pd.DataFrame(data)
    print(df.head())
    return df


def preprocessing_article(content, df_congress):
    """
    Preprocess article text data:
    - Lowercase the text.
    - Tokenize the text into phrases.
    - Remove punctuation and special characters.
    - Remove common words (stop words).
    - Stemming : strips words down to shared linguistic roots with Porter Stemmer
    - Build bigrams
    - Calculate relative frequency of each phrase in the article.
    - Calculate TF-IDF for each phrase in the article.

    Input:
    - Raw text of the article.

    Output:
    - Dataframe with columns: 'phrase', 'relative_frequence', 'tf-idf' for each article.
    """
    # Lowercase
    lowercased_text = content.lower()
    # Tokenization: split the text into non-alphanumeric characters, suppressing punctuation.
    tokens = re.findall(r"\w+",lowercased_text)
    print(f"Tokens: {tokens[:10]}")
    # Remove common words (stop words)
    stop_words = set(nltk.corpus.stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    # Stemming
    stemmer = nltk.stem.PorterStemmer()
    stem_tokens = [stemmer.stem(word) for word in tokens]
    # Build bigrams
    bigrams = nltk.bigrams(stem_tokens)
    bigram_phrases = [' '.join(bigram) for bigram in bigrams]
    # Select only phrases present in partisanship vocabulary
    bigram_phrases = [phrase for phrase in bigram_phrases if phrase in set(df_congress["phrases"])]
    # Unique phrases
    unique_phrases = set(bigram_phrases)
    # Relative frequency fpa (p = phrase, a = article) = frequency of phrase p appearing in article a / all frequencies of phrases in article a
    relative_frequencies = []
    for phrase in unique_phrases:
        count = bigram_phrases.count(phrase)
        relative_frequencies.append(count / len(bigram_phrases))
    
    # Calculate IDF-TF for each phrase
    vectorizer = TfidfVectorizer(vocabulary=df_congress["phrases"], ngram_range=(2, 2))
    tfidf_matrix = vectorizer.fit_transform([lowercased_text])
    # Map phrases to their TF-IDF scores
    tfidf_scores = []
    for phrase in unique_phrases:
        index = vectorizer.vocabulary_.get(phrase)
        tfidf_scores.append(tfidf_matrix[0, index])

    # Create dataframe
    df_article = pd.DataFrame(data={
        'phrase': bigram_phrases,
        'relative_frequence': relative_frequencies,
        'tf-idf': tfidf_scores
    })

    print(df_article.head())
    return df_article







def estimate_ideology_article():
    """
    Estimate ideology for each article:
    - Obtain the ideology estimation of the article.
    - Conclude the political party of the article.

    Input:
    - Dataframe with columns: 'phrase', 'relative_frequence' for each article.

    Output:
    - Ideology estimation for the article.
    - Political party conclusion for the article.
    """



def main():
    df_congress = import_extract_Congress_Record_vocabulary()
    article_test_path = DATA_DIR/ "tests/chat_gpt_example_gen.txt"
    with open(article_test_path, "r", encoding="utf-8") as f:
        content = f.read()
    df_article = preprocessing_article(content, df_congress)

if __name__ == "__main__":
    main()
    