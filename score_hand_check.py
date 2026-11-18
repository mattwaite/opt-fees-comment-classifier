"""Score the human hand check (human_check_completed.csv, exported from the reporter's Google Sheet)
against the model labels in human_check_sample_KEY.csv. Rows the reporter left blank (attachment rows,
which she didn't have the files for) are excluded. Prints agreement with Wilson 95% intervals."""
from math import sqrt
import pandas as pd


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), c + h


h = pd.read_csv("human_check_completed.csv")
h = h[h["Document ID"].notna()][["Document ID", "stance_source", "human_label"]]  # drop her summary rows
k = pd.read_csv("human_check_sample_KEY.csv")
m = h.merge(k, on="Document ID", validate="one_to_one")
c = m[m.human_label.notna()]
print(f"sample {len(m)}, coded {len(c)}, left blank {m.human_label.isna().sum()} "
      f"({m[m.human_label.isna()].stance_source.value_counts().to_dict()})")
print(pd.crosstab(c.final_stance, c.human_label, rownames=["model"], colnames=["human"], margins=True))
opp = {"PRO": "CON", "CON": "PRO"}
rows = [("any disagreement", (c.final_stance != c.human_label).sum(), len(c)),
        ("opposite direction (PRO<->CON)", (c.human_label == c.final_stance.map(opp)).sum(), len(c))]
for s in ["PRO", "CON"]:
    x = c[c.final_stance == s]
    rows.append((f"model {s} not confirmed by human", (x.human_label != s).sum(), len(x)))
for name, kk, n in rows:
    lo, hi = wilson(kk, n)
    print(f"{name}: {kk}/{n} = {kk/n:.1%}  (95% CI {lo:.1%}-{hi:.1%})")
print(c[c.final_stance != c.human_label][["Document ID", "final_stance", "human_label"]].to_string(index=False))
