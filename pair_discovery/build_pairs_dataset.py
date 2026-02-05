import argparse
import glob
import json
import os
import re
from typing import Any, Dict, List, Optional


def _safe_slug(title: str) -> str:
    # match repo's span filename convention (spaces -> underscores)
    return title.replace(" ", "_")


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _extract_texts_from_spans(obj: Any) -> List[str]:
    """
    Be permissive: spans json may be list[str], list[dict], or dict with 'spans' key.
    We normalize to list of paragraph-like strings.
    """
    if obj is None:
        return []
    if isinstance(obj, dict):
        # common keys: spans / paragraphs / text
        for k in ("spans", "paragraphs", "texts", "text"):
            if k in obj:
                return _extract_texts_from_spans(obj[k])
        return []
    if isinstance(obj, list):
        texts = []
        for item in obj:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    texts.append(s)
            elif isinstance(item, dict):
                # guess a text field
                for k in ("text", "content", "span", "paragraph"):
                    if k in item and isinstance(item[k], str):
                        s = item[k].strip()
                        if s:
                            texts.append(s)
                        break
        return texts
    if isinstance(obj, str):
        s = obj.strip()
        return [s] if s else []
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", type=str, default="data/seeds/pairs_meta.jsonl")
    ap.add_argument("--outputs_dir", type=str, default="data/outputs")
    ap.add_argument("--out", type=str, default="data/outputs/pairs_dataset.jsonl")
    args = ap.parse_args()

    meta = _load_jsonl(args.meta)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    n_ok = 0
    n_skip = 0
    skips: Dict[str, int] = {}

    with open(args.out, "w", encoding="utf-8") as fout:
        for rec in meta:
            title = rec.get("title")
            if not title:
                n_skip += 1
                skips["no_title"] = skips.get("no_title", 0) + 1
                continue

            slug = _safe_slug(title)
            wiki_spans_path = os.path.join(
                args.outputs_dir, f"wikipedia_spans_{slug}.json"
            )
            grok_spans_path = os.path.join(
                args.outputs_dir, f"grokipedia_spans_{slug}.json"
            )

            if not os.path.exists(wiki_spans_path) or not os.path.exists(
                grok_spans_path
            ):
                n_skip += 1
                skips["missing_spans_file"] = skips.get("missing_spans_file", 0) + 1
                continue

            wiki_spans_obj = _load_json(wiki_spans_path)
            grok_spans_obj = _load_json(grok_spans_path)

            wiki_paras = _extract_texts_from_spans(wiki_spans_obj)
            grok_paras = _extract_texts_from_spans(grok_spans_obj)

            if len(" ".join(wiki_paras)) < 300 or len(" ".join(grok_paras)) < 300:
                n_skip += 1
                skips["too_short_after_parse"] = (
                    skips.get("too_short_after_parse", 0) + 1
                )
                continue

            outrec = {
                "title": title,
                "type": rec.get("type", "unknown"),
                "type_confidence": rec.get("type_confidence"),
                "type_evidence": rec.get("type_evidence"),
                "wikipedia": {
                    "url": rec.get("wikipedia_url"),
                    "paragraphs": wiki_paras,
                    "text": "\n\n".join(wiki_paras),
                    "spans_file": wiki_spans_path.replace("\\", "/"),
                },
                "grokipedia": {
                    "url": rec.get("grokipedia_url"),
                    "paragraphs": grok_paras,
                    "text": "\n\n".join(grok_paras),
                    "spans_file": grok_spans_path.replace("\\", "/"),
                },
            }

            fout.write(json.dumps(outrec, ensure_ascii=False) + "\n")
            n_ok += 1

    print(f"[OK] wrote {n_ok} pairs to {args.out}")
    print(f"[SKIP] {n_skip} skipped. reasons={skips}")


if __name__ == "__main__":
    main()
