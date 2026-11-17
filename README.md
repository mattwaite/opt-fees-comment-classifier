# OPT Fees rule: public comment stance classification

This repo classifies all 8,953 public comments on the DHS/ICE proposed rule **"Optional Practical Training Fees"** (docket [ICEB-2026-0100](https://www.regulations.gov/docket/ICEB-2026-0100)) as **PRO**, **CON** or **UNCLEAR**. Two open-weight language models from different developers did the classifying, running locally. Where they disagree, a person makes the call.

**Full methodology, checks and limitations: [METHODS.md](METHODS.md).**

## Headline numbers

| | Submissions | Share |
|---|---|---|
| CON (both models) | 7,915 | 88.4% |
| PRO (both models) | 920 | 10.3% |
| UNCLEAR (both models) | 61 | 0.7% |
| Models disagree (human review) | 57 | 0.6% |

The two models agree on 99.4% of submissions.

## Files

**Results**
- `comments_two_model_classification.csv`: **main output**, one row per submission
  - `final_stance`: the agreed label, or `REVIEW` where the models disagree
  - `tier`: `high` (both agree, each at least 0.90 confident), `agree_low`, `agree_unclear`, `soft` (one model said UNCLEAR) or `flip` (one said PRO, the other CON)
  - both models' labels, confidences and per-label probabilities
  - `stance_source`: whether the label came from the comment text alone or from the comment plus its attachment
- `review_disagreements_tiebreak.csv`: the 57 disagreements, with a third model's vote, suggested readings and a `human_final` column for a person to fill in
- `human_check_sample.csv`: a blind random sample of 200 comments for a human to code. Its answer key is `human_check_sample_KEY.csv`; don't open the key until you've finished coding.
- `validation_sample.csv`: the 200-comment pilot comparison

**Intermediate (needed to re-run the comparison)**
- `classified_comments_final.csv`: Gemma's labels
- `classified_comments_qwen_final.csv`: Qwen's labels
- `review_disagreements.csv`: the disagreements before the tiebreak
- `run.log`, `run_qwen.log`: progress logs from the runs

**Source data**
- `mwe-1z5p-yhxg.csv`: the docket's bulk comment export from Regulations.gov
- `attachment_urls.txt`: the 748 attachment PDFs, one URL per line. The PDFs aren't included because together they're 343 MB.

## Reproducing

Requirements:
- Python 3.10+ with `pandas`
- [LM Studio](https://lmstudio.ai) running its local server on port 1234, with these models: `google/gemma-4-26b-a4b-qat`, `qwen/qwen3.6-35b-a3b`, `qwen/qwen3.8-27b`
- `pdftotext` (from poppler)
- macOS `textutil` (only needed for non-PDF attachments)

Steps:

1. Download the attachments into `attachments/`. Each file needs the comment's Document ID somewhere in its name, e.g. `ICEB-2026-0100-0008_attachment_1.pdf`. The download host blocks scripts, so use a browser bulk downloader such as DownThemAll with `attachment_urls.txt`.
2. Run:

```bash
python3 classify.py --model google/gemma-4-26b-a4b-qat --workers 8 --out classified_comments.csv
python3 classify_attachments.py --model google/gemma-4-26b-a4b-qat --base classified_comments.csv --out classified_comments_final.csv
python3 classify.py --model qwen/qwen3.6-35b-a3b --workers 6 --out classified_comments_qwen.csv
python3 classify_attachments.py --model qwen/qwen3.6-35b-a3b --base classified_comments_qwen.csv --out classified_comments_qwen_final.csv
python3 compare_models.py
python3 tiebreak.py
python3 add_flip_notes.py
```

`classify.py` is resumable: if it stops, re-run the same command and it skips rows already written. On an Apple-silicon laptop, each full pass takes about 1 hour.

## Scripts

| Script | Purpose |
|---|---|
| `classify.py` | Prompt and label definitions; classifies the comment text. Confidence comes from the model's probability for each label (logprobs). |
| `classify_attachments.py` | Extracts attachment text and re-classifies those rows using comment plus attachment |
| `compare_models.py` | Joins the two models' labels and assigns agreement tiers |
| `tiebreak.py` | Runs a third model on the disagreements |
| `add_flip_notes.py` | Adds suggested readings, written by Claude, for the PRO/CON flips |
| `make_url_list.py` | Builds `attachment_urls.txt` from the source CSV |

## A note on personal information

The comment data includes commenters' names, cities and states as published on Regulations.gov. These are public records, but think about that before quoting or identifying individual commenters.
