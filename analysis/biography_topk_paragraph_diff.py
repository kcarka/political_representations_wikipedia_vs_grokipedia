import json
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATASET = r"data\outputs\pairs_dataset.jsonl"
TOPK = 10
MIN_LEN = 50

analyzer = SentimentIntensityAnalyzer()

def span_to_text(span):
    if isinstance(span, str):
        return span.strip()
    if isinstance(span, dict):
        for k in ("text", "content", "paragraph", "span"):
            if k in span and isinstance(span[k], str):
                return span[k].strip()
    return ""

def score(text: str) -> float:
    return analyzer.polarity_scores(text)["compound"]

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_path(rec, candidates):
    for k in candidates:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return None

results = []
missing_spans = 0
missing_fields = 0
kept_pairs = 0

with open(DATASET, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)

        if r.get("type") != "biography":
            continue
        kept_pairs += 1

        # ✅ 优先从 dataset 里读取 spans 路径（最可靠）
        wiki_spans_path = pick_path(r, [
            "wikipedia_spans_file", "wiki_spans_file", "wiki_spans_path",
            "wikipedia_spans", "wiki_spans"
        ])
        grok_spans_path = pick_path(r, [
            "grokipedia_spans_file", "grok_spans_file", "grok_spans_path",
            "grokipedia_spans", "grok_spans"
        ])

        # 有的实现把 spans_file 放在子对象里
        if wiki_spans_path is None and isinstance(r.get("wikipedia"), dict):
            wiki_spans_path = r["wikipedia"].get("spans_file")
        if grok_spans_path is None and isinstance(r.get("grokipedia"), dict):
            grok_spans_path = r["grokipedia"].get("spans_file")

        if wiki_spans_path is None or grok_spans_path is None:
            missing_fields += 1
            continue

        # 兼容用 / 的路径
        wiki_spans_path = wiki_spans_path.replace("/", "\\")
        grok_spans_path = grok_spans_path.replace("/", "\\")

        if not (os.path.exists(wiki_spans_path) and os.path.exists(grok_spans_path)):
            missing_spans += 1
            continue

        wiki_spans = load_json(wiki_spans_path)
        grok_spans = load_json(grok_spans_path)

        title = r.get("title") or r.get("wikipedia_title") or os.path.basename(wiki_spans_path)

        # 保守对齐：按 index 取最短
        n = min(len(wiki_spans), len(grok_spans))

        for i in range(n):
            w = span_to_text(wiki_spans[i])
            g = span_to_text(grok_spans[i])


            if len(w) < MIN_LEN or len(g) < MIN_LEN:
                continue

            dw = score(w)
            dg = score(g)
            delta = dg - dw

            results.append({
                "title": title,
                "para_id": i,
                "delta": delta,
                "wiki_score": dw,
                "grok_score": dg,
                "wiki_text": w,
                "grok_text": g,
                "wiki_spans_file": wiki_spans_path,
                "grok_spans_file": grok_spans_path,
            })

results.sort(key=lambda x: x["delta"])  # 最负在前
topk = results[:TOPK]

out_path = r"data\outputs\biography_topk_negative_paragraphs.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(topk, f, indent=2, ensure_ascii=False)

print(f"[OK] biography pairs seen: {kept_pairs}")
print(f"[OK] missing spans fields in dataset: {missing_fields}")
print(f"[OK] spans paths not found on disk: {missing_spans}")
print(f"[OK] paragraph candidates collected: {len(results)}")
print(f"[OK] wrote Top-{TOPK} → {out_path}")
