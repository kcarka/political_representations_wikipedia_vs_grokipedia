import os, re, json
from bs4 import BeautifulSoup

import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


# import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from scipy.stats import ttest_rel, wilcoxon

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ---------- Text utils ----------
def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def wiki_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Wikipedia main content
    content = soup.find("div", id="mw-content-text")
    if content is None:
        # fallback
        content = soup

    # remove tables, infoboxes, navboxes, etc.
    for tag in content.select(
        "table, style, script, sup.reference, div.reflist, ol.references"
    ):
        tag.decompose()

    ps = [normalize_ws(p.get_text(" ", strip=True)) for p in content.find_all("p")]
    ps = [p for p in ps if p]  # drop empty
    return normalize_ws(" ".join(ps))


def grok_parsed_to_text(grok_item: dict) -> str:
    spans = []
    for sec in grok_item.get("sections", []) or []:
        spans.extend(sec.get("spans", []) or [])
        for sub in sec.get("subsections", []) or []:
            spans.extend(sub.get("spans", []) or [])
    return normalize_ws(" ".join(spans))


def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


# ---------- Main ----------
def main():
    import os, re, json
    from pathlib import Path
    import pandas as pd


def read_lines(path: Path):
    if not path.exists():
        return []
    return [
        x.strip()
        for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip() and not x.strip().startswith("#")
    ]


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def wiki_html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    content = soup.find("div", id="mw-content-text") or soup

    for tag in content.select(
        "table, style, script, sup.reference, div.reflist, ol.references"
    ):
        tag.decompose()

    ps = [normalize_ws(p.get_text(" ", strip=True)) for p in content.find_all("p")]
    ps = [p for p in ps if p and len(p.split()) >= 8]
    return normalize_ws(" ".join(ps))


def grok_parsed_to_text(grok_item: dict) -> str:
    spans = []
    for sec in grok_item.get("sections", []) or []:
        spans.extend(sec.get("spans", []) or [])
        for sub in sec.get("subsections", []) or []:
            spans.extend(sub.get("spans", []) or [])
    return normalize_ws(" ".join(spans))


def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s))


def main():
    # ✅ Always use the script location to locate the root directory to avoid path errors.
    BASE_DIR = Path(__file__).resolve().parent.parent
    out_dir = BASE_DIR / "data" / "outputs"
    seeds_dir = BASE_DIR / "data" / "seeds"
    results_dir = BASE_DIR / "results"
    results_dir.mkdir(exist_ok=True)

    wiki_urls = read_lines(seeds_dir / "wikipedia_urls.txt")
    grok_urls = read_lines(seeds_dir / "grokipedia_urls.txt")

    # grok parsed
    grok_parsed_path = out_dir / "grokipedia_parsed.json"
    grok_parsed = json.loads(grok_parsed_path.read_text(encoding="utf-8"))
    assert isinstance(grok_parsed, list), "grokipedia_parsed.json should be a list."

    # pairs
    # Quantity: Take the smallest of the three to ensure it does not exceed the limit.
    n_pairs = min(len(grok_parsed), len(wiki_urls), len(grok_urls))
    if n_pairs < 1:
        raise RuntimeError(
            "No pairs found. Check seeds files and grokipedia_parsed.json."
        )

        # sentiment analyzer

        sia = SentimentIntensityAnalyzer()
    else:
        import nltk

        nltk.download("vader_lexicon", quiet=True)
        sia = SentimentIntensityAnalyzer()

    rows = []
    for i in range(n_pairs):
        wiki_html_path = out_dir / f"wikipedia_raw_{i}.html"
        if not wiki_html_path.exists():
            # If any of the intermediate 'i's are missing, skip them
            continue

        wiki_html = wiki_html_path.read_text(encoding="utf-8", errors="ignore")
        wiki_text = wiki_html_to_text(wiki_html)

        grok_text = grok_parsed_to_text(grok_parsed[i])

        sent_wiki = sia.polarity_scores(wiki_text)["compound"]
        sent_grok = sia.polarity_scores(grok_text)["compound"]

        sent_wiki = sia.polarity_scores(wiki_text)["compound"]
        sent_grok = sia.polarity_scores(grok_text)["compound"]

        rows.append(
            {
                "pair_id": i,
                "wiki_url": wiki_urls[i],
                "grok_url": grok_urls[i],
                "n_words_wiki": word_count(wiki_text),
                "n_words_grok": word_count(grok_text),
                "sent_wiki": sent_wiki,
                "sent_grok": sent_grok,
                "delta_sent": sent_grok - sent_wiki,
            }
        )

    df = pd.DataFrame(rows)
    out_csv = results_dir / "baseline_pairwise.csv"
    df.to_csv(out_csv, index=False)
    from scipy.stats import ttest_rel, wilcoxon

    # Filter out NaN (to prevent some pages from being extracted as empty)
    mask = df["sent_wiki"].notna() & df["sent_grok"].notna()
    sent_wiki = df.loc[mask, "sent_wiki"]
    sent_grok = df.loc[mask, "sent_grok"]
    delta = df.loc[mask, "delta_sent"]

    # paired t-test
    t_stat, t_p = ttest_rel(sent_grok, sent_wiki)

    # Wilcoxon
    # If all delta values ​​are the same or the sample size is too small, an error will occur, so protection is implemented.
    w_stat, w_p = (None, None)
    if len(delta) >= 2 and delta.nunique() > 1:
        try:
            w_stat, w_p = wilcoxon(delta)
        except Exception:
            w_stat, w_p = (None, None)

    stats_df = pd.DataFrame(
        [
            {
                "metric": "vader_compound",
                "n_pairs_used": int(mask.sum()),
                "mean_sent_wiki": float(sent_wiki.mean()),
                "mean_sent_grok": float(sent_grok.mean()),
                "mean_delta": float(delta.mean()),
                "median_delta": float(delta.median()),
                "t_stat": float(t_stat),
                "t_p": float(t_p),
                "wilcoxon_stat": None if w_stat is None else float(w_stat),
                "wilcoxon_p": None if w_p is None else float(w_p),
            }
        ]
    )

    stats_path = results_dir / "baseline_stats.csv"
    stats_df.to_csv(stats_path, index=False)

    fig_dir = results_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    plt.figure()
    plt.hist(delta, bins=10)
    plt.xlabel("Delta sentiment (Grok - Wiki)")
    plt.ylabel("Count")
    plt.title("Article-level sentiment difference (VADER compound)")
    fig_path = fig_dir / "delta_sent_hist.png"
    plt.savefig(fig_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved figure to {fig_path}")

    print(f"✅ Saved stats summary to {stats_path}")

    print(f"✅ Saved pairwise results to {out_csv}")
    print(f"Pairs scored: {len(df)}")


if __name__ == "__main__":
    main()
