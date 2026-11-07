"""Rule-based device measures from the stored decision summaries (no new download).

Input : devices/devices_tagged.csv (01_fda_devices.py) and the stored PDFs
Output: devices/device_metrics.csv           one row per candidate device
        devices/device_context_snippets.csv  every tumor-term snippet, for reading each record
        devices/device_summary.csv

01_fda_devices.py flags a device when a primary CNS tumor term appears ANYWHERE in its
decision summary, including predicate comparisons, contraindications and general text.
This stage re-reads the PDFs and applies fixed rules:
  in_use_statement   a primary CNS tumor term within 1,500 characters after an
                     "Indications for Use" or "Intended Use" heading
  negated            every such hit is within 80 characters after a negation cue
                     ("not intended", "contraindicat", "exclud", "not for use",
                     "should not", "not been validated")
  strict flag        in_use_statement and not negated
Metastasis-only devices are reported separately. The denominator is the 1,313 devices from
the radiology, neurology and pathology panels. The final list comes from human screening
(src/screening/01_final_screening.py).
Run: python src/devices/02_device_metrics.py
"""
import os, re, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
import importlib
fda = importlib.import_module("01_fda_devices")

OUT = "devices"
HEAD = re.compile(r"indications?\s+for\s+use|intended\s+use", re.I)
NEG = re.compile(r"not\s+intended|contraindicat|exclud|not\s+for\s+use|should\s+not|"
                 r"not\s+been\s+validated|not\s+indicated", re.I)


def windows(text):
    return [(m.end(), m.end() + 1500) for m in HEAD.finditer(text)]


def main():
    t = pd.read_csv(config.inp(f"{OUT}/devices_tagged.csv"))
    cand = t[(t.flag_specific == 1) | (t.flag_metastasis_only == 1)].copy()
    rows, snippets = [], []
    for r in cand.itertuples(index=False):
        path = fda.pdf_path(r.submission)
        txt = re.sub(r"\s+", " ", fda.text_of(path)) if path else ""
        wins = windows(txt)
        in_use, all_neg = False, True
        for m in fda.SPECIFIC.finditer(txt):
            s = m.start()
            ctx = txt[max(0, s - 200): s + 200]
            inside = any(a <= s <= b for a, b in wins)
            neg = bool(NEG.search(txt[max(0, s - 80): s]))
            snippets.append([r.submission, r.device, inside, neg, m.group(0), ctx])
            if inside:
                in_use = True
                if not neg:
                    all_neg = False
        strict = in_use and not all_neg
        year = int(str(r.decision_date)[-4:])
        rows.append([r.submission, r.device, r.company, r.panel, year, int(r.flag_specific),
                     int(r.flag_metastasis_only), int(in_use), int(strict)])
    m = pd.DataFrame(rows, columns=["submission", "device", "company", "panel", "year",
                                    "flag_specific_anywhere", "flag_metastasis_only",
                                    "tumor_in_use_statement", "strict_primary_tumor"])
    m.to_csv(config.out(f"{OUT}/device_metrics.csv"), index=False)
    pd.DataFrame(snippets, columns=["submission", "device", "in_use_statement_window",
                                    "negated", "term", "context"]
                 ).to_csv(config.out(f"{OUT}/device_context_snippets.csv"), index=False)
    s = m[m.strict_primary_tumor == 1]
    summ = [("devices_searched", len(t)),
            ("flag_anywhere_primary", int(m.flag_specific_anywhere.sum())),
            ("flag_metastasis_only", int(m.flag_metastasis_only.sum())),
            ("strict_primary_tumor", len(s)),
            ("strict_earliest_year", int(s.year.min()) if len(s) else ""),
            ("anywhere_earliest_year", int(m[m.flag_specific_anywhere == 1].year.min()))]
    for yr, n in s.groupby("year").size().items():
        summ.append((f"strict_year_{yr}", int(n)))
    pd.DataFrame(summ, columns=["name", "value"]).to_csv(config.out(f"{OUT}/device_summary.csv"), index=False)
    for k, v in summ:
        print(f"  {k:<28} {v}")
    print(s[["submission", "year", "device"]].to_string(index=False))


if __name__ == "__main__":
    main()
