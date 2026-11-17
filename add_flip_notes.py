"""Add an AI reviewer's reading (Claude, via Claude Code) for the 20 PRO/CON flips.
These are SUGGESTIONS for a human to confirm, not final labels."""
import pandas as pd

notes = {
    "ICEB-2026-0100-0571": ("CON", "Sarcastic: 'announce that they no longer want international students'."),
    "ICEB-2026-0100-2973": ("CON", "'Get rid of this' - wants the rule gone."),
    "ICEB-2026-0100-1387": ("PRO", "'I like this idea in general' - supports with a caveat about cost pass-through."),
    "ICEB-2026-0100-5554": ("UNCLEAR", "Likely sarcasm about 'cheap positions for foreigners'; direction ambiguous."),
    "ICEB-2026-0100-7264": ("CON", "Technical legal comment challenging the fee's statutory authority; asks for changes."),
    "ICEB-2026-0100-4706": ("UNCLEAR", "Explicitly mixed: 'on the one hand... on the other hand'."),
    "ICEB-2026-0100-1761": ("UNCLEAR", "Says 'in favor of this proposal' but the reasoning is pro-immigrant; likely misread the rule."),
    "ICEB-2026-0100-0668": ("UNCLEAR", "Rant calling rule ineffective and the administration corrupt; no clear position on the fees."),
    "ICEB-2026-0100-0399": ("UNCLEAR", "'Shut the entire thing down' - unclear whether 'thing' is OPT (PRO) or the rule (CON)."),
    "ICEB-2026-0100-0055": ("PRO", "'This should end' refers to OPT; protect native-born graduates."),
    "ICEB-2026-0100-1683": ("PRO", "Fees too high, but wants OPT eliminated altogether - more restrictive than the rule."),
    "ICEB-2026-0100-7860": ("UNCLEAR", "Organizational letter proposing its own program; read the attachment before coding."),
    "ICEB-2026-0100-0251": ("CON", "Supports OPT reform but opposes this rule's core design (universities paying)."),
    "ICEB-2026-0100-0459": ("UNCLEAR", "Anti-immigrant tone but says 'DON'T PASS THIS BILL'; contradictory."),
    "ICEB-2026-0100-3239": ("CON", "Sarcastic: 'more communistic than anything we had back home. Good job!'"),
    "ICEB-2026-0100-3238": ("CON", "Sarcastic: will take expertise to Europe; 'America is indeed failing'."),
    "ICEB-2026-0100-0826": ("CON", "Sarcastic: 'If you wanna keep talents outside US, this is a nice idea.'"),
    "ICEB-2026-0100-0114": ("PRO", "Son couldn't find a job; 'This is EVIL' refers to OPT competition."),
    "ICEB-2026-0100-1783": ("PRO", "Says 'everyone else supports the proposal' - aligns with supporters."),
    "ICEB-2026-0100-6552": ("UNCLEAR", "'Great idea. Innovation will be able to continue' - likely sarcasm, can't be sure."),
}
r = pd.read_csv("review_disagreements_tiebreak.csv")
r.insert(11, "claude_suggested", r["Document ID"].map(lambda k: notes.get(k, ("", ""))[0]))
r.insert(12, "claude_note", r["Document ID"].map(lambda k: notes.get(k, ("", ""))[1]))
r.insert(13, "human_final", "")
r.to_csv("review_disagreements_tiebreak.csv", index=False)
f = r[r.tier == "flip"]
print("flips: majority vote vs Claude reading")
print(pd.crosstab(f.majority_stance, f.claude_suggested))
