"""Classify public comments on the DHS OPT Fees proposed rule (ICEB-2026-0100) as PRO / CON / UNCLEAR
using a local LM Studio model. Confidence = the model's token probability for the chosen label,
renormalised across the three labels (from logprobs), not a self-reported number.

Usage: python3 classify.py [--model ID] [--workers N] [--limit N] [--out FILE]
Resumable: rows already in the output file are skipped.
"""
import argparse, csv, json, math, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

csv.field_size_limit(sys.maxsize)
URL = "http://localhost:1234/v1/chat/completions"

SYSTEM = """You classify public comments submitted on a proposed federal rule.

THE RULE: DHS/ICE proposed rule "Optional Practical Training Fees" (Oct 2026). It would charge schools a fee of $70,000 for an international (F-1) student's first OPT recommendation and $30,000 for each later recommendation, including STEM OPT extensions.

Labels:
- PRO = the commenter supports the rule. This INCLUDES commenters who want the fees, want even higher fees, or want OPT/STEM OPT restricted, curtailed or eliminated (they think the rule doesn't go far enough), e.g. to protect American workers.
- CON = the commenter opposes the rule: wants it withdrawn, the fees reduced/removed, or OPT preserved; argues it harms international students, universities, innovation or the economy.
- UNCLEAR = no stance can be determined (e.g. "see attached", off-topic, empty, or truly mixed with no lean).

Judge the commenter's position on the rule, not their tone. Reply with exactly one word: PRO, CON, or UNCLEAR."""

LABELS = ("PRO", "CON", "UNCLEAR")


def norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def classify(text, model, max_chars=6000):
    body = {
        "model": model,
        "reasoning_effort": "none",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Comment:\n\"\"\"\n" + text[:max_chars] + "\n\"\"\"\n\nLabel (PRO, CON, or UNCLEAR):"},
        ],
        "max_tokens": 4,
        "temperature": 0,
        "logprobs": True,
        "top_logprobs": 10,
    }
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.load(r)
            break
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    ch = d["choices"][0]
    raw = (ch["message"].get("content") or "").strip()
    probs = {k: 0.0 for k in LABELS}
    lp = (ch.get("logprobs") or {}).get("content") or []
    lp = [e for e in lp if e["token"].strip()]  # skip empty/template tokens
    if lp:
        for t in lp[0]["top_logprobs"]:
            tok = t["token"].strip().upper()
            for k in LABELS:
                # first-token prefixes: "UN"/"UNC" for UNCLEAR, "CON"/"PRO" exact
                if tok == k or (k == "UNCLEAR" and tok in ("UN", "UNC", "UNCLE")):
                    probs[k] += math.exp(t["logprob"])
    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}
        label = max(probs, key=probs.get)
    else:  # no usable logprobs: fall back to raw text
        label = next((k for k in LABELS if raw.upper().startswith(k[:3])), "UNCLEAR")
        probs[label] = float("nan")
    return label, probs, raw, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-26b-a4b-qat")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample-seed", type=int, default=None, help="random sample of --limit unique comments")
    ap.add_argument("--input", default="mwe-1z5p-yhxg.csv")
    ap.add_argument("--out", default="classified_comments.csv")
    a = ap.parse_args()

    with open(a.input, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["Document Type"] == "Public Submission"]

    # dedupe identical text -> classify once
    groups = {}
    for r in rows:
        groups.setdefault(norm(r["Comment"]), []).append(r)
    texts = list(groups)
    if a.sample_seed is not None:
        import random
        random.Random(a.sample_seed).shuffle(texts)
    if a.limit:
        texts = texts[: a.limit]

    fields = ["Document ID", "stance", "confidence", "p_pro", "p_con", "p_unclear", "label_mass",
              "has_attachment", "duplicate_count", "model", "First Name", "Last Name",
              "Organization Name", "State/Province", "Posted Date", "Comment"]
    done = set()
    if os.path.exists(a.out):
        with open(a.out, newline="", encoding="utf-8") as f:
            done = {r["Document ID"] for r in csv.DictReader(f)}
    todo = [t for t in texts if any(r["Document ID"] not in done for r in groups[t])]
    print(f"{len(rows)} submissions, {len(groups)} unique texts, {len(todo)} to classify with {a.model}", flush=True)

    new = not os.path.exists(a.out)
    fout = open(a.out, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(fout, fieldnames=fields)
    if new:
        w.writeheader()

    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(classify, t if t else "(empty)", a.model): t for t in todo}
        for i, fu in enumerate(as_completed(futs), 1):
            t = futs[fu]
            try:
                label, p, raw, mass = fu.result()
            except Exception as e:
                print("ERROR", repr(e)[:200], flush=True)
                continue
            for r in groups[t]:
                if r["Document ID"] in done:
                    continue
                w.writerow({
                    "Document ID": r["Document ID"], "stance": label,
                    "confidence": round(p[label], 4),
                    "p_pro": round(p["PRO"], 4), "p_con": round(p["CON"], 4), "p_unclear": round(p["UNCLEAR"], 4),
                    "label_mass": round(mass, 4),
                    "has_attachment": bool(r["Attachment Files"].strip()),
                    "duplicate_count": len(groups[t]), "model": a.model,
                    **{k: r[k] for k in ["First Name", "Last Name", "Organization Name", "State/Province", "Posted Date", "Comment"]},
                })
            fout.flush()
            if i % 100 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"{i}/{len(todo)}  {i/el:.2f}/s  eta {(len(todo)-i)/(i/el)/60:.1f} min", flush=True)
    fout.close()


if __name__ == "__main__":
    main()
