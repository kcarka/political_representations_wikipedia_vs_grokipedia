import argparse
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

VALID_TYPES = {"biography", "institution", "law", "event"}


def read_jsonl(path: str) -> List[dict]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def key(rec: dict) -> Tuple[str, str]:
    # robust de-dup key: prefer urls
    return (rec.get("wikipedia_url", ""), rec.get("grokipedia_url", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bio", default="data/indices/index_bio.jsonl")
    ap.add_argument("--event", default="data/indices/index_event.jsonl")
    ap.add_argument("--law", default="data/indices/index_law.jsonl")
    ap.add_argument("--inst", default="data/indices/index_inst.jsonl")
    ap.add_argument("--quota", type=int, default=30, help="target per type")
    ap.add_argument("--out", default="data/indices/pairs_index_balanced.jsonl")
    ap.add_argument("--manifest", default="data/indices/manifest_balanced.json")
    args = ap.parse_args()

    sources = {
        "biography": args.bio,
        "event": args.event,
        "law": args.law,
        "institution": args.inst,
    }

    # Load & label
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for t, path in sources.items():
        if not os.path.exists(path):
            print(f"[WARN] missing {t} index: {path}")
            continue
        recs = read_jsonl(path)
        for r in recs:
            # Force bucket type by source file to ensure balanced sampling
            r["type"] = t
            buckets[t].append(r)

    # De-dup across all
    seen = set()
    deduped: Dict[str, List[dict]] = defaultdict(list)
    for t, recs in buckets.items():
        for r in recs:
            k = key(r)
            if k in seen:
                continue
            seen.add(k)
            deduped[t].append(r)

    # Quota sample (deterministic: keep first N)
    chosen: List[dict] = []
    stats = {}
    for t in ["biography", "institution", "law", "event"]:
        recs = deduped.get(t, [])
        take = recs[: args.quota]
        chosen.extend(take)
        stats[t] = {"available": len(recs), "selected": len(take)}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in chosen:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "quota_per_type": args.quota,
        "sources": sources,
        "stats": stats,
        "total_selected": len(chosen),
    }
    with open(args.manifest, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)

    print(f"[OK] wrote balanced index: {args.out}")
    print(json.dumps(manifest["stats"], indent=2))


if __name__ == "__main__":
    main()
