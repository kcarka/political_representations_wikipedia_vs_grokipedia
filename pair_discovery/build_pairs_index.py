import argparse
import json
import os
import time
from dataclasses import asdict
from typing import List, Dict

from tqdm import tqdm
from .type_classifier import classify_title

from .http_cache import HTTPCache
from .wiki_discover import discover_titles_from_category
from .grok_match import try_match_grokipedia


def wiki_title_to_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--category", type=str, default="Category:Politics of the United States"
    )
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", type=str, default="data/indices/pairs_index.jsonl")
    ap.add_argument("--manifest", type=str, default="data/indices/manifest.json")
    ap.add_argument("--cache_dir", type=str, default="data/cache")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    os.makedirs(os.path.dirname(args.manifest), exist_ok=True)

    cache = HTTPCache(args.cache_dir, ttl_days=30)
    user_agent = "FairnessAI-PairDiscovery/0.1 (research; contact: local)"

    from .wiki_discover import discover_titles_from_category_recursive

    titles = discover_titles_from_category_recursive(
        args.category, limit_pages=args.limit, max_depth=2, user_agent=user_agent
    )

    total = 0
    matched = 0
    failures: Dict[str, int] = {}

    started = time.time()
    with open(args.out, "w", encoding="utf-8") as f:
        for t in tqdm(titles, desc="Pairing titles"):
            total += 1
            grok = try_match_grokipedia(t, cache, user_agent=user_agent)
            if not grok.ok:
                failures[grok.reason] = failures.get(grok.reason, 0) + 1
                continue

            ty = classify_title(t)
            record = {
                "title": t,
                "type": ty.type,
                "type_confidence": ty.confidence,
                "type_evidence": ty.evidence,
                "wikipedia_url": wiki_title_to_url(t),
                "grokipedia_url": grok.url,
                "pairing": {
                    "method": "exact_title_to_slug",
                    "confidence": 1.0,
                    "grok_status": grok.status_code,
                },
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            matched += 1

    elapsed = time.time() - started

    manifest = {
        "category": args.category,
        "limit": args.limit,
        "total_titles_considered": total,
        "pairs_matched": matched,
        "match_rate": (matched / total) if total else 0.0,
        "failure_reasons": failures,
        "cache_dir": args.cache_dir,
        "out_index": args.out,
        "generated_at_unix": time.time(),
        "elapsed_sec": elapsed,
    }

    with open(args.manifest, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)

    print(f"[OK] wrote {matched} pairs to {args.out}")
    print(f"[OK] manifest: {args.manifest}")


if __name__ == "__main__":
    main()
