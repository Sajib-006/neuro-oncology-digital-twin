"""FDA AI-enabled devices that may concern brain tumors (Fig. 5c, Table S8).

Input : devices/raw/f_178541   FDA list of AI-enabled devices (aiml-devices-csv.csv,
                               page updated 4 September 2026, downloaded 25 September 2026)
        devices/raw/pdf/       decision summary PDFs (downloaded here when missing,
                               1 request per second; set OFFLINE=1 to use stored PDFs only)
Output: devices/devices_tagged.csv          one row per device in the three panels
        devices/device_screening_sheet.csv  candidates, blank sheet for two human screeners
        devices/provenance.csv
Needs pdftotext (poppler; the paper used version 22.02.0).

The FDA list gives device name, company, review panel and product code, but NOT the
indication. The indication is in each device's decision summary PDF, so this stage:
  1. keeps devices reviewed by the Radiology, Neurology or Pathology panels;
  2. reads each decision summary PDF and extracts its text;
  3. flags brain tumor relevance from the TEXT, not the device name:
       specific          an explicit primary CNS tumor term (glioma, glioblastoma,
                         meningioma, "brain tumor", ...)
       metastasis_only   brain metastasis terms without a primary CNS term
       broad             "tumor/lesion/neoplasm" and "brain/intracranial" both present
  4. writes a screening sheet with the indication-for-use text for TWO human screeners.
The keyword flags only build the shortlist. Inclusion is decided by the screeners.
Run: python -u src/devices/01_fda_devices.py   (resumable; PDFs are stored)
"""
import os, re, sys, csv, time, subprocess, hashlib, datetime
import urllib.request
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config

OUT = str(config.OUT_DIR / "devices")
PDF = str(config.OUT_DIR / "devices" / "raw" / "pdf")          # new downloads go here
PDF_STORED = str(config.DATA_DIR / "devices" / "raw" / "pdf")  # stored copies are read from here
LIST = str(config.inp("devices/raw/f_178541"))                 # aiml-devices-csv.csv
PANELS = ["Radiology", "Neurology", "Pathology"]
UA = {"User-Agent": "Mozilla/5.0 (AI4BrainCancer review; academic)"}

SPECIFIC = re.compile(r"glioma|glioblastoma|astrocytoma|oligodendroglioma|meningioma|"
                      r"medulloblastoma|ependymoma|craniopharyngioma|brain tumou?r|"
                      r"brain neoplasm|intracranial (tumou?r|neoplasm)|cns tumou?r|"
                      r"neuro-?oncolog", re.I)
METS = re.compile(r"brain metasta|cerebral metasta|intracranial metasta", re.I)
TUMOR = re.compile(r"tumou?r|neoplas|lesion|cancer|oncolog", re.I)
BRAIN = re.compile(r"\bbrain\b|intracranial|cerebr|cranial|\bhead\b", re.I)


def url_for(sub):
    sub = sub.split("/")[0].strip()
    if sub.startswith("K"):
        # FDA folders drop the leading zero for 2000s years: K080762 -> pdf8/, K253628 -> pdf25/
        return f"https://www.accessdata.fda.gov/cdrh_docs/pdf{int(sub[1:3])}/{sub}.pdf"
    if sub.startswith("DEN"):
        return f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{sub}.pdf"
    if sub.startswith("P"):
        return f"https://www.accessdata.fda.gov/cdrh_docs/pdf{int(sub[1:3])}/{sub}B.pdf"
    return None


def pdf_path(sub):
    """Stored or downloaded PDF of a submission, or None."""
    name = f"{sub.split('/')[0]}.pdf"
    for folder in (PDF, PDF_STORED):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    return None


def fetch(sub):
    path = os.path.join(PDF, f"{sub.split('/')[0]}.pdf")
    for p in (path, os.path.join(PDF_STORED, os.path.basename(path))):
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p, "cached"
    u = url_for(sub)
    if not u:
        return None, "no-url"
    if config.OFFLINE:
        return None, "offline-not-stored"
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        if not data.startswith(b"%PDF"):
            return None, "not-pdf"
        open(path, "wb").write(data)
        time.sleep(1.0)
        return path, "downloaded"
    except Exception as e:
        time.sleep(1.0)
        return None, f"error:{type(e).__name__}"


def text_of(path):
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True,
                              text=True, timeout=120).stdout
    except Exception:
        return ""


def indication(text):
    """Text after the last 'Indications for Use' heading that has substance."""
    hits = [m.end() for m in re.finditer(r"indications? for use", text, re.I)]
    for h in reversed(hits):
        chunk = re.sub(r"\s+", " ", text[h:h + 1400]).strip(" :.-")
        if len(chunk) > 80 and "substantially equivalent" not in chunk[:200].lower():
            return chunk[:900]
    return ""


def main():
    os.makedirs(PDF, exist_ok=True)
    d = pd.read_csv(LIST, encoding="latin-1")
    d = d[d["Panel (Lead)"].isin(PANELS)].copy()
    print(f"devices in {PANELS}: {len(d)}", flush=True)

    rows = []
    for i, r in enumerate(d.itertuples(index=False)):
        sub = r[1]
        path, status = fetch(sub)
        txt = text_of(path) if path else ""
        spec = bool(SPECIFIC.search(txt))
        mets = bool(METS.search(txt))
        broad = bool(TUMOR.search(txt) and BRAIN.search(txt))
        rows.append({"submission": sub, "decision_date": r[0], "device": r[2], "company": r[3],
                     "panel": r[4], "product_code": r[5], "pdf_status": status,
                     "text_chars": len(txt), "flag_specific": int(spec),
                     "flag_metastasis_only": int(mets and not spec), "flag_broad": int(broad),
                     "indication_text": indication(txt)})
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(d)}  specific so far {sum(x['flag_specific'] for x in rows)}",
                  flush=True)

    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, "devices_tagged.csv"), index=False)
    cand = t[(t.flag_specific == 1) | (t.flag_metastasis_only == 1)].copy()
    cols = ["submission", "decision_date", "device", "company", "panel", "product_code",
            "flag_specific", "flag_metastasis_only", "indication_text"]
    with open(os.path.join(OUT, "device_screening_sheet.csv"), "w", newline="") as f:
        f.write("# INCLUDE if the device's indication covers detecting, segmenting, characterising\n"
                "# or planning treatment of PRIMARY CNS tumours (record metastasis-only devices\n"
                "# separately). Read the indication text; open the PDF if unclear.\n"
                "# Two independent human coders; record any AI assistance in the coder column.\n")
        out = cand[cols].copy()
        for c in ["include_primary_cns (1/0)", "metastasis_only (1/0)", "function (detect / "
                  "segment / characterise / RT planning / other)", "coder", "coder_2_include (1/0)",
                  "coder_2", "agreed_include (1/0)", "notes"]:
            out[c] = ""
        out.to_csv(f, index=False)

    with open(os.path.join(OUT, "provenance.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "value"])
        w.writerow(["source", "https://www.fda.gov/media/178541/download (aiml-devices-csv.csv)"])
        w.writerow(["fda_page_updated", config.FDA_LIST_UPDATED])
        w.writerow(["pull_date", datetime.date.today().isoformat()])
        w.writerow(["list_sha256_16", hashlib.sha256(open(LIST, "rb").read()).hexdigest()[:16]])
        w.writerow(["devices_all", len(pd.read_csv(LIST, encoding="latin-1"))])
        w.writerow(["devices_in_panels", len(t)])
        w.writerow(["pdf_ok", int((t.text_chars > 0).sum())])
        w.writerow(["flag_specific", int(t.flag_specific.sum())])
        w.writerow(["flag_metastasis_only", int(t.flag_metastasis_only.sum())])
    print(f"\nPDF text obtained: {(t.text_chars > 0).sum()} / {len(t)}  "
          f"(status: {t.pdf_status.value_counts().to_dict()})")
    print(f"specific primary-CNS-tumour term: {t.flag_specific.sum()}; "
          f"metastasis only: {t.flag_metastasis_only.sum()}; broad: {t.flag_broad.sum()}")
    print(f"written -> {OUT}/device_screening_sheet.csv ({len(cand)} rows)")


if __name__ == "__main__":
    main()
