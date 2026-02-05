import argparse, json, os

def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def key(r):
    return (r.get("wikipedia_url",""), r.get("grokipedia_url",""))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in1", required=True)
    ap.add_argument("--in2", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    seen=set()
    out=[]
    for p in [args.in1, args.in2]:
        if not os.path.exists(p):
            continue
        for r in read_jsonl(p):
            k=key(r)
            if k in seen:
                continue
            seen.add(k)
            out.append(r)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[OK] wrote {len(out)} records -> {args.out}")

if __name__ == "__main__":
    main()
