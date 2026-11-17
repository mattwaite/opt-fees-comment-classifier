"""Third-model tiebreak: run Qwen 3.8 27B (dense) on every row where Gemma and Qwen 35B-A3B disagree.
Uses the same input the other models saw (comment text, plus attachment text where available).
Adds qwen27b_stance / qwen27b_conf / majority_stance to review_disagreements.csv -> review_disagreements_tiebreak.csv
"""
import csv, os, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import classify, classify_attachments as ca

M = "qwen/qwen3.8-27b"
csv.field_size_limit(sys.maxsize)
rev = pd.read_csv("review_disagreements.csv")
src = {}
with open("mwe-1z5p-yhxg.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["Document ID"] in set(rev["Document ID"]):
            src[r["Document ID"]] = r
files = ca.find_files()


def build(did):
    r = src[did]
    text = classify.norm(r["Comment"])
    fs = files.get(did, [])
    att = "\n\n".join(t for t in (ca.extract(p).strip() for p in sorted(fs)) if t)
    att = re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", att))
    if len(att) >= 50:
        if len(att) > ca.HEAD + ca.TAIL:
            att = att[:ca.HEAD] + "\n[...]\n" + att[-ca.TAIL:]
        text = f"{text}\n\n--- ATTACHED DOCUMENT ---\n{att}"
    return text


with ThreadPoolExecutor(2) as ex:
    res = list(ex.map(lambda did: classify.classify(build(did), M, ca.HEAD + ca.TAIL + 2500), rev["Document ID"]))
rev.insert(8, "qwen27b_stance", [r[0] for r in res])
rev.insert(9, "qwen27b_conf", [round(r[1][r[0]], 4) for r in res])


def majority(row):
    c = Counter([row.gemma_stance, row.qwen_stance, row.qwen27b_stance]).most_common(1)[0]
    return c[0] if c[1] >= 2 else "NO_MAJORITY"


rev.insert(10, "majority_stance", rev.apply(majority, axis=1))
rev.to_csv("review_disagreements_tiebreak.csv", index=False)
print(pd.crosstab(rev.tier, rev.majority_stance))
