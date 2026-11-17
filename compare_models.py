"""Join the Gemma and Qwen classifications and flag disagreements.

Output: comments_two_model_classification.csv
  final_stance  = the label both models agree on; "REVIEW" when they disagree
  agreement     = "agree" / "disagree"
  tier          = high      : both agree on PRO/CON and both confidences >= 0.90
                  agree_low : both agree, but at least one confidence < 0.90
                  flip      : one says PRO, the other CON (most important to hand-check)
                  soft      : one says UNCLEAR, the other PRO/CON
Also writes review_disagreements.csv (all disagreements, flips first).
"""
import pandas as pd

G = "classified_comments_final.csv"
Q = "classified_comments_qwen_final.csv"  # Qwen 3.6 35B-A3B
HIGH = 0.90

g = pd.read_csv(G)
q = pd.read_csv(Q)[["Document ID", "stance", "confidence", "p_pro", "p_con", "p_unclear"]]
d = g.rename(columns={"stance": "gemma_stance", "confidence": "gemma_conf", "p_pro": "gemma_p_pro",
                      "p_con": "gemma_p_con", "p_unclear": "gemma_p_unclear"}).merge(
    q.rename(columns={"stance": "qwen_stance", "confidence": "qwen_conf", "p_pro": "qwen_p_pro",
                      "p_con": "qwen_p_con", "p_unclear": "qwen_p_unclear"}), on="Document ID", how="left",
    validate="one_to_one")
assert d["qwen_stance"].notna().all(), "some rows missing a Qwen label"

same = d.gemma_stance == d.qwen_stance
d["agreement"] = same.map({True: "agree", False: "disagree"})
d["final_stance"] = d.gemma_stance.where(same, "REVIEW")
flip = (~same) & d.gemma_stance.isin(["PRO", "CON"]) & d.qwen_stance.isin(["PRO", "CON"])
d["tier"] = "soft"
d.loc[flip, "tier"] = "flip"
d.loc[same, "tier"] = "agree_low"
d.loc[same & (d.gemma_conf >= HIGH) & (d.qwen_conf >= HIGH) & d.gemma_stance.isin(["PRO", "CON"]), "tier"] = "high"
d.loc[same & (d.gemma_stance == "UNCLEAR"), "tier"] = "agree_unclear"

lead = ["Document ID", "final_stance", "tier", "agreement", "gemma_stance", "gemma_conf", "qwen_stance", "qwen_conf",
        "stance_source", "has_attachment", "duplicate_count"]
d = d[lead + [c for c in d.columns if c not in lead and c != "model"]]
d.to_csv("comments_two_model_classification.csv", index=False)

rev = d[~same].copy()
rev["_o"] = rev.tier.map({"flip": 0, "soft": 1})
rev.sort_values(["_o", "gemma_conf"], ascending=[True, False]).drop(columns="_o").to_csv(
    "review_disagreements.csv", index=False)

print("rows", len(d), " agreement", round(same.mean(), 4))
print(pd.crosstab(d.gemma_stance, d.qwen_stance, rownames=["gemma"], colnames=["qwen"], margins=True))
print(d.tier.value_counts())
print(d.final_stance.value_counts())
