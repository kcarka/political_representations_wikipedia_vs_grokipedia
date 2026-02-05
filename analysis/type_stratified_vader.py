import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
from scipy.stats import wilcoxon, ttest_rel
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATASET = "data/outputs/pairs_dataset.jsonl"
OUT_CSV = "data/outputs/type_stratified_vader.csv"

analyzer = SentimentIntensityAnalyzer()

REPL = {
    "鈥": "-",
    "—": "-",
    "–": "-",
    "“": '"',
    "”": '"',
    "„": '"',
    "‘": "'",
    "’": "'",
    "…": "...",
}


def normalize_text(s: str) -> str:
    if not s:
        return ""
    for k, v in REPL.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def vader_compound(text: str) -> float:
    text = normalize_text(text)
    if not text:
        return 0.0
    return float(analyzer.polarity_scores(text)["compound"])


def load_pairs(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def safe_type(t: str) -> str:
    if t in {"biography", "institution", "law", "event"}:
        return t
    return "unknown"


def main():
    rows = []
    for rec in load_pairs(DATASET):
        title = rec.get("title", "")
        t = safe_type(rec.get("type", "unknown"))

        wtxt = (rec.get("wikipedia", {}) or {}).get("text", "")
        gtxt = (rec.get("grokipedia", {}) or {}).get("text", "")

        w = vader_compound(wtxt)
        g = vader_compound(gtxt)
        delta = g - w

        rows.append(
            {
                "title": title,
                "type": t,
                "wiki_vader": w,
                "grok_vader": g,
                "delta_grok_minus_wiki": delta,
                "wiki_len": len(wtxt),
                "grok_len": len(gtxt),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        print("[ERR] No rows loaded. Check data/outputs/pairs_dataset.jsonl")
        return

    # Save per-article table
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"[OK] wrote per-article table: {OUT_CSV}")

    # Type-stratified stats (paired)
    print("\n=== Type-stratified paired tests (Δ = grok - wiki) ===")
    for t, sub in df.groupby("type"):
        if t == "unknown":
            continue
        # need at least 5 to be meaningful
        if len(sub) < 5:
            print(f"\n[{t}] n={len(sub)} (too small; skipping tests)")
            continue

        deltas = sub["delta_grok_minus_wiki"].to_numpy()
        wiki = sub["wiki_vader"].to_numpy()
        grok = sub["grok_vader"].to_numpy()

        # Paired t-test (mean difference)
        t_stat, t_p = ttest_rel(grok, wiki, nan_policy="omit")

        # Wilcoxon signed-rank (median difference)
        # handle all-zero case
        try:
            w_stat, w_p = wilcoxon(deltas)
        except ValueError:
            w_stat, w_p = float("nan"), float("nan")

        print(f"\n[{t}] n={len(sub)}")
        print(
            f"  mean(wiki)={wiki.mean():.4f}  mean(grok)={grok.mean():.4f}  mean(Δ)={deltas.mean():.4f}"
        )
        print(f"  median(Δ)={float(pd.Series(deltas).median()):.4f}")
        print(f"  paired t-test:   p={t_p:.4g}")
        print(f"  wilcoxon test:   p={w_p:.4g}")

    # Overall
    wiki = df["wiki_vader"].to_numpy()
    grok = df["grok_vader"].to_numpy()
    deltas = df["delta_grok_minus_wiki"].to_numpy()
    t_stat, t_p = ttest_rel(grok, wiki, nan_policy="omit")
    try:
        w_stat, w_p = wilcoxon(deltas)
    except ValueError:
        w_stat, w_p = float("nan"), float("nan")

    print("\n[overall]")
    print(
        f"  n={len(df)} mean(Δ)={deltas.mean():.4f} median(Δ)={float(pd.Series(deltas).median()):.4f}"
    )
    print(f"  paired t-test: p={t_p:.4g}")
    print(f"  wilcoxon:     p={w_p:.4g}")


if __name__ == "__main__":
    main()
