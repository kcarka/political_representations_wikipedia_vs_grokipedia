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
                      extract_path / "partisan_phrases_110.txt",
                      extract_path / "partisan_phrases_109.txt",
                      extract_path / "partisan_phrases_108.txt",
                      extract_path / "partisan_phrases_107.txt",
                      extract_path / "partisan_phrases_106.txt",
                      extract_path / "partisan_phrases_105.txt"]
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
    mean_ideology = np.mean(ideologies)
    std_ideology = np.std(ideologies)
    ideologies = [(i - mean_ideology) / std_ideology for i in ideologies] # z-score
    #ideologies = [(ideology - min_ideology) / (max_ideology - min_ideology) * 2 - 1 for ideology in ideologies] # min-max normalization
    # Create dataframe
    data = {
        "phrases": phrases,
        "ideologies": ideologies
    }
    df = pd.DataFrame(data)
    print(df.head())
    print("Number of bigrams in the vocabulary:", df.shape[0])
    return df


def preprocessing_entity(content, df_congress):
    """
    Preprocess entity text data:
    - Lowercase the text.
    - Tokenize the text into phrases.
    - Remove punctuation and special characters.
    - Remove common words (stop words).
    - Stemming : strips words down to shared linguistic roots with Porter Stemmer
    - Build bigrams
    - Calculate relative frequency of each phrase in the entity.
    - Calculate TF-IDF for each phrase in the entity.

    Input:
    - Raw text of the entity.
    - Congressional Records vocabulary: DataFrame

    Output:
    - Dataframe of the entity with columns: 'phrase', 'relative_frequence', 'tf-idf' for each bigrams.
    """
    # Lowercase
    lowercased_text = content.lower()
    # Tokenization: split the text into non-alphanumeric characters, suppressing punctuation.
    tokens = re.findall(r"\w+",lowercased_text)
    #print(f"Tokens: {tokens[:10]}")
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
    unique_phrases = list(dict.fromkeys(bigram_phrases))
    # /!\ Remove extreme rare bigrams ? No the Democrat vocabulary is more sparse than the Republican.
    # Relative frequency fpa (p = phrase, a = article) = frequency of phrase p appearing in article a / all frequencies of phrases in article a
    relative_frequencies = []
    bias_score = []
    #print(df_congress["phrases"])
    for phrase in unique_phrases:
        count = bigram_phrases.count(phrase)
        relative_frequencies.append(count / len(bigram_phrases))
        bias_score.append(df_congress.loc[df_congress["phrases"] == phrase, "ideologies"].iloc[0])
    
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
        'phrases': unique_phrases,
        'relative_frequency': relative_frequencies,
        'tf-idf': tfidf_scores,
        'score': bias_score
    })

    return df_article



def estimate_ideology_entity(df_entity):
    """
    Estimate ideology for the entity:
    - Obtain the ideology estimation.
    - Conclude the political party.

    Input:
    - Dataframe with columns: 'phrase', 'relative_frequence', 'score' for each entity.

    Output:
    - bias : Ideology estimation for the entity.
    - orientation: Political party conclusion for the entity.
    """
    bias = np.dot(df_entity['relative_frequency'], df_entity['score'])/ sum(df_entity['relative_frequency'])
    orientation = "Neutral"
    if bias > 0:
        print("Right-leaning bias - more Republican oriented entity.")
        orientation = "Republican"
    elif bias == 0:
        print("Neutral entity.")
    else:
        print("Left-leaning bias - more Democrat oriented entity.")
        orientation = "Democrat"
    return bias, orientation

def ideology_color(x):
    """
    Return the ideology color associated with political party.
    Republican - blue
    Democrat - red
    Neutral - gray
    """
    if x > 0:
        return "blue"   # Republican
    elif x < 0:
        return "red"    # Democrat
    else:
        return "gray"   # Neutral

def plot_distribution_congress(df_congress):
    """
    Visualize the distribution of ideological score in the Congressional Records' vocabulary.

    Input:
    - DataFrame with columns: 'phrase', 'ideology' for each bigrams.

    Output: void
    """
    colors = df_congress["ideologies"].apply(ideology_color)
    x = np.arange(len(df_congress))
    plt.figure()
    plt.scatter(x, df_congress["ideologies"], c=colors, alpha=0.6)
    plt.axhline(0)
    plt.xlabel("Bigrams (vocabulary index)")
    plt.ylabel("Ideology score")
    plt.title("Distribution of Bigrams by Political Ideology")
    plt.show()

    plt.figure()
    plt.hist(df_congress["ideologies"], bins=50)
    plt.axvline(0)
    plt.xlabel("Ideology score")
    plt.ylabel("Number of bigrams")
    plt.title("Ideological Distribution of Congressional Bigrams")
    plt.show()

def plot_distribution_entity(df_entity, entity_name = ""):
    colors = df_entity["score"].apply(ideology_color)
    x = np.arange(len(df_entity))
    plt.figure()
    plt.scatter(x, df_entity["score"], c=colors, alpha=0.6)
    plt.axhline(0)
    plt.xlabel("Bigrams (vocabulary index)")
    plt.ylabel("Ideology score")
    plt.title(f"Distribution of {entity_name} Bigrams by Political Ideology")
    plt.show()

    plt.figure()
    plt.hist(df_entity["score"], bins=50)
    plt.axvline(0)
    plt.xlabel("Ideology score")
    plt.ylabel("Number of bigrams")
    plt.title(f"Ideological Distribution of {entity_name} Bigrams")
    plt.show()
    return




def main():
    # Import Congressional Records
    df_congress = import_extract_Congress_Record_vocabulary()
    plot_distribution_congress(df_congress)

    # --- Tests ---
    
    # Import corpus
    corpus_path = {
        DATA_DIR/ "tests/chat_gpt_example_gen.txt",
        DATA_DIR/ "tests/donald_trump.txt"
    }
    content = []
    for article_path in corpus_path:
        with open(article_path, "r", encoding="utf-8") as f:
            content_article = f.read()
        content.append(content_article)
    content_corpus = ''.join(content)
    # Import article
    content_article = content[0]
    # Get paragraph
    content_paragraph = [p.strip() for p in content_article.split("\n\n") if p.strip()]

    # Get sentences
    content_sentence = [ s.strip() for s in content_article.split(".") if s.strip()]

    
    # Test corpus
    df_corpus = preprocessing_entity(content_corpus, df_congress)
    print(df_corpus.head())
    print("Number of bigrams:", df_corpus["phrases"].shape)
    bias, orientation = estimate_ideology_entity(df_corpus)
    plot_distribution_entity(df_corpus, entity_name="Corpus")

    # Test article-level
    df_article = preprocessing_entity(content_article, df_congress)
    print(df_article.head())
    print("Number of bigrams:", df_article["phrases"].shape)
    bias, orientation = estimate_ideology_entity(df_article)
    plot_distribution_entity(df_article, entity_name="Article")

    # Test paragraph-level
    df_paragraph = [ preprocessing_entity(paragraph, df_congress) for paragraph in content_paragraph]
    print("Paragraph | Number of bigrams \n")
    for i, p in enumerate(df_paragraph):
        print(f"    {i}    |   {p["phrases"].shape}")

    # Test sentence-level
    df_sentence = [ preprocessing_entity(sentence, df_congress) for sentence in content_sentence]
    print("Sentence | Number of bigrams \n")
    for i, s in enumerate(df_sentence):
        print(f"    {i}    |   {s["phrases"].shape}")

if __name__ == "__main__":
    main()
    