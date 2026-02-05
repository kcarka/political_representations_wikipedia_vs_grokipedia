import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=str, default="data/indices/pairs_index.jsonl")
    ap.add_argument("--out_dir", type=str, default="data/seeds")
    ap.add_argument("--max_pairs", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    wiki_path = os.path.join(args.out_dir, "wikipedia_urls.txt")
    grok_path = os.path.join(args.out_dir, "grokipedia_urls.txt")
    meta_path = os.path.join(args.out_dir, "pairs_meta.jsonl")

    n = 0
    with open(args.index, "r", encoding="utf-8") as fin, open(
        wiki_path, "w", encoding="utf-8"
    ) as fw, open(grok_path, "w", encoding="utf-8") as fg, open(
        meta_path, "w", encoding="utf-8"
    ) as fm:

        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)

            fw.write(rec["wikipedia_url"] + "\n")
            fg.write(rec["grokipedia_url"] + "\n")

            meta = {
                "title": rec.get("title"),
                "type": rec.get("type"),
                "type_confidence": rec.get("type_confidence"),
                "type_evidence": rec.get("type_evidence"),
                "wikipedia_url": rec.get("wikipedia_url"),
                "grokipedia_url": rec.get("grokipedia_url"),
                "pairing": rec.get("pairing", {}),
            }
            fm.write(json.dumps(meta, ensure_ascii=False) + "\n")

            n += 1
            if args.max_pairs and n >= args.max_pairs:
                break

    print(f"[OK] wrote {n} pairs to:")
    print(f"  - {wiki_path}")
    print(f"  - {grok_path}")
    print(f"  - {meta_path}")


if __name__ == "__main__":
    main()
