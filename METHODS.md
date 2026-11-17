# Methods: classifying public comments on the DHS "Optional Practical Training Fees" proposed rule

Docket ICEB-2026-0100 (91 FR 64566, published Oct. 8, 2026). The proposed rule would charge schools $70,000 for an F-1 student's first OPT recommendation and $30,000 for each later recommendation, including STEM OPT extensions.

## Data

- **Source:** the docket's bulk comment export from Regulations.gov (`mwe-1z5p-yhxg.csv`), 8,955 rows. 8,953 are public submissions; the other two are the rule and a notice.
- **Coverage:** this export includes only comments the agency had posted at the time it was downloaded. It may not include every comment the agency received.
- **Attachments:** 650 submissions had attached files. Many said only "See attached file(s)". All 748 attachment files were downloaded as PDFs, and their text was extracted with `pdftotext`. 35 submissions' attachments had no extractable text (probably scanned images). Those were classified on the comment text alone and are marked that way in the data.
- **Duplicates:** identical comment texts (ignoring whitespace) were classified once and the label applied to every copy. Comments with attachments were each classified on their own attachment, so "See attached" placeholders aren't counted as duplicates. That leaves 8,503 distinct texts across the 8,953 submissions. Near-identical form letters with small edits were classified separately.

## Classification

Each comment was classified by **two open-weight language models from different developers**, both run on a laptop through LM Studio. All automated classification ran on that machine. Separately, Claude, a cloud-based AI assistant from Anthropic, read the disagreements and the hand-check samples described below, which sent that comment text to Anthropic. All of these comments are public records.

| Role | Model |
|---|---|
| Classifier A | Google Gemma 4 26B-A4B (QAT 4-bit) |
| Classifier B | Alibaba Qwen 3.6 35B-A3B (8-bit) |
| Tiebreaker (disagreements only) | Alibaba Qwen 3.8 27B |

**Prompt.** Both models received the same instructions, which describe the rule and three labels:

- **PRO:** supports the rule. This includes commenters who want higher fees or want OPT restricted or eliminated, i.e. who think the rule doesn't go far enough.
- **CON:** opposes the rule: wants it withdrawn, the fees reduced or removed, or OPT preserved.
- **UNCLEAR:** no position can be determined.

The models were told to judge the commenter's position on the rule, not their tone. The full prompt is in `classify.py`.

**Attachment rows.** For comments with attachments, the model saw the comment text plus the first 6,000 and last 1,500 characters of the attachment text. Opening and closing paragraphs are where a letter usually states its position.

**Confidence.** The models ran at temperature 0 with their reasoning ("thinking") mode turned off, so each answered with a single label. Confidence is the probability the model gave to its chosen label, read directly from its output and spread across just the three labels. The model did not report its own confidence. These scores are **not calibrated**: both models are above 0.99 on most comments, so a high score alone shouldn't be read as proof. **Agreement between two independent models is the main evidence.**

## Results

| Result | Submissions | Share |
|---|---|---|
| Both models: CON | 7,915 | 88.4% |
| Both models: PRO | 920 | 10.3% |
| Both models: UNCLEAR | 61 | 0.7% |
| Models disagree (needs human review) | 57 | 0.6% |
| **Total** | **8,953** | |

- The models agreed on **99.4%** of submissions.
- **8,762 submissions (97.9%)** are in the "high" tier: both models gave the same PRO or CON label, each with confidence of at least 0.90.
- Even if all 57 disagreements went one way, CON would be between 88.4% and 89.0% of all submissions, and PRO between 10.3% and 10.9%.
- Counting each distinct text once instead of every submission: 7,646 CON, 745 PRO, 55 UNCLEAR, 57 disagreements.
- **Form letters:** 7 texts were submitted 10 or more times each, for 221 submissions in all: 146 PRO and 75 CON. So about 16% of all PRO submissions come from those 7 form letters.
- 73 submissions got a final label even though at least one model was below 0.90 confidence (tier `agree_low`). Nobody has reviewed these individually.

## Checks

1. **Pilot agreement:** before the full run, Qwen 3.8 27B classified a stratified sample of 200 comments (120 CON, 60 PRO, 20 UNCLEAR as labeled by Gemma). It agreed on 120 of 120 CON and 59 of 60 PRO.
2. **Keyword check:** of 1,158 distinct comments beginning "I oppose" or "I strongly oppose," Gemma labeled 1,155 CON. Two of the others were correctly labeled PRO: those commenters oppose the OPT program itself, so they support the fees.
3. **Claude's reading of agreed labels (an AI check, not a human one):** Claude read random samples of 45 short comments both models labeled PRO and 45 both labeled CON, and found no errors. Short comments are where sarcasm and ambiguity are most likely.
4. **Disagreements:** the 57 disagreements went to the tiebreaker model, and the 20 where one model said PRO and the other said CON were read by Claude. **The main failure is sarcasm.** For example, "this is more communistic than anything we had back home. Good job!" fooled multiple models, and in several flips the two-of-three majority vote was wrong. For that reason, **disagreements are not resolved automatically.** They are in `review_disagreements_tiebreak.csv` with each model's label, the majority vote, Claude's suggested reading (for the 20 flips) and an empty `human_final` column for a reporter to fill in.

5. **Human verification (to do):** `human_check_sample.csv` holds a blind random sample of 100 high-tier PRO and 100 high-tier CON submissions, with the labels hidden. A reporter codes `human_label`, then compares against `human_check_sample_KEY.csv` to get a human-verified error rate. PRO is oversampled relative to its share because it is the smaller count, so each error moves it more.
6. **Off-docket comments:** at least two comments are about eliminating a 60-day grace period for employment-based workers (8 CFR 214.1(l)(2)), which this fee rule doesn't address. They appear to have been filed on the wrong docket. Both are among the disagreements and should be coded UNCLEAR or excluded.

## Limitations

- Two models can share the same blind spot, sarcasm in particular. Agreement doesn't guarantee a label is correct, but in the samples read by hand, agreed labels were correct.
- "PRO" combines people who support the rule as written with people who want OPT ended entirely. Those are different positions, and the story should describe them that way.
- Comments counts submissions, not people. One person or organization can submit more than once, and form-letter campaigns produce many identical submissions (see Results).
- Attachments over about 7,500 characters were classified from their opening and closing sections only.

## Files

| File | Contents |
|---|---|
| `comments_two_model_classification.csv` | **Main output.** One row per submission: final_stance, tier, both models' labels and confidences, metadata, comment text |
| `review_disagreements_tiebreak.csv` | The 57 disagreements, with tiebreaker and suggested readings, for human coding |
| `validation_sample.csv` | The 200-comment pilot check |
| `human_check_sample.csv` / `human_check_sample_KEY.csv` | Blind 200-row sample for human coding, and its answer key |
| `classify.py`, `classify_attachments.py`, `compare_models.py`, `tiebreak.py` | Code to reproduce the run |
