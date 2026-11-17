"""Re-classify comments that have attachments, using the comment text + extracted attachment text,
then merge with classified_comments.csv into classified_comments_final.csv.

Expects downloaded files somewhere under attachments/, with the comment's Document ID
(e.g. ICEB-2026-0100-0008) in the file's path or name.

Usage: python3 classify_attachments.py [--model ID] [--workers N]
"""
import argparse, csv, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import classify

csv.field_size_limit(sys.maxsize)
HEAD, TAIL = 6000, 1500  # chars of attachment text kept: opening + closing (where stance usually lives)


def extract(path):
    ext = path.rsplit(".", 1)[-1].lower()
    try:
        if ext == "pdf":
            out = subprocess.run(["pdftotext", "-q", "-layout", path, "-"], capture_output=True, timeout=120).stdout
        elif ext in ("docx", "doc", "rtf", "txt", "html", "htm"):
            out = subprocess.run(["textutil", "-convert", "txt", "-stdout", path], capture_output=True, timeout=120).stdout
        else:
            return ""  # images etc. are not OCR'd
        return out.decode("utf-8", "replace")
    except Exception:
        return ""


def find_files(root="attachments"):
    """Map Document ID -> list of files, preferring one format per attachment number."""
    by_id = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            m = re.search(r"(ICEB-2026-0100-\d{4})", p)
            if m:
                by_id.setdefault(m.group(1), []).append(p)
    return by_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-26b-a4b-qat")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--input", default="mwe-1z5p-yhxg.csv")
    ap.add_argument("--base", default="classified_comments.csv")
    ap.add_argument("--out", default="classified_comments_final.csv")
    a = ap.parse_args()

    with open(a.input, newline="", encoding="utf-8") as f:
        src = {r["Document ID"]: r for r in csv.DictReader(f)
               if r["Document Type"] == "Public Submission" and r["Attachment Files"].strip()}
    files = find_files()

    jobs, missing, no_text = {}, [], []
    for did, r in src.items():
        fs = files.get(did, [])
        # one file per attachment number, prefer pdf
        best = {}
        for p in sorted(fs):
            k = re.sub(r"\.\w+$", "", os.path.basename(p))
            if k not in best or p.lower().endswith(".pdf"):
                best[k] = p
        text = "\n\n".join(t for t in (extract(p).strip() for p in best.values()) if t)
        text = re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text))
        if not fs:
            missing.append(did); continue
        if len(text) < 50:
            no_text.append(did); continue
        att = text if len(text) <= HEAD + TAIL else text[:HEAD] + "\n[...]\n" + text[-TAIL:]
        jobs[did] = (f"{classify.norm(r['Comment'])}\n\n--- ATTACHED DOCUMENT ---\n{att}", len(text))
    print(f"{len(src)} comments with attachments: {len(jobs)} with text, {len(missing)} files missing, "
          f"{len(no_text)} no extractable text (images/scans)", flush=True)

    results = {}
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(classify.classify, t, a.model, HEAD + TAIL + 2500): did for did, (t, _) in jobs.items()}
        for i, fu in enumerate(as_completed(futs), 1):
            did = futs[fu]
            try:
                results[did] = fu.result()
            except Exception as e:
                print("ERROR", did, repr(e)[:200], flush=True)
            if i % 50 == 0:
                print(f"{i}/{len(futs)}", flush=True)

    with open(a.base, newline="", encoding="utf-8") as f:
        base = list(csv.DictReader(f))
    fields = list(base[0].keys()) + ["stance_source", "attachment_chars"]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in base:
            did = r["Document ID"]
            r["stance_source"], r["attachment_chars"] = "comment_text", ""
            if did in results:
                label, p, raw, mass = results[did]
                r.update(stance=label, confidence=round(p[label], 4), p_pro=round(p["PRO"], 4),
                         p_con=round(p["CON"], 4), p_unclear=round(p["UNCLEAR"], 4), label_mass=round(mass, 4),
                         model=a.model, stance_source="comment+attachment", attachment_chars=jobs[did][1])
            elif did in missing:
                r["stance_source"] = "comment_text (attachment not downloaded)"
            elif did in no_text:
                r["stance_source"] = "comment_text (attachment had no extractable text)"
            w.writerow(r)
    print("wrote", a.out)
    if missing:
        print("missing files for:", " ".join(missing[:20]), "..." if len(missing) > 20 else "")


if __name__ == "__main__":
    main()
