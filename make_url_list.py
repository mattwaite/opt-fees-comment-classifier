"""Write attachment_urls.txt: one URL per attachment, preferring PDF when the same
attachment exists in several formats (attachment_1.pdf + attachment_1.docx)."""
import csv, re, sys
csv.field_size_limit(sys.maxsize)
seen = {}
with open("mwe-1z5p-yhxg.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        for u in filter(None, (x.strip() for x in r["Attachment Files"].split(","))):
            m = re.match(r"(.*/attachment_\d+)\.(\w+)$", u)
            stem, ext = (m.group(1), m.group(2).lower()) if m else (u, "")
            if stem not in seen or (ext == "pdf" and not seen[stem].endswith(".pdf")):
                seen[stem] = u
with open("attachment_urls.txt", "w") as f:
    f.write("\n".join(seen.values()) + "\n")
print(len(seen), "attachment URLs written")
