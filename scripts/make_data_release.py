"""Collect the shareable derived files into one release folder, with full SHA256 hashes.

Input : DATA_DIR (and OUT_DIR, which is read first; see src/config.py)
Output: <out>/...              the files listed in RELEASE, at the same relative paths
        <out>/SHA256SUMS       full sha256 of every file, in `sha256sum -c` format
        <out>/MANIFEST.csv     path, bytes, sha256
        <out>/devices/pdf_manifest.csv   URL, bytes and sha256 of each stored FDA decision summary

Excluded files (provider terms):
  * Scopus records (lit/records/) and the tag-check coder sheets, which contain titles and
    abstracts. lit/tagged_records.csv.gz keeps the EID, DOI, year, document type and all
    derived tags.
  * Raw third-party downloads (Open Targets, CTD, DisGeNET, FDA PDFs), which are retrieved
    from the providers by the download scripts. --third-party adds the CTD subset and the
    DisGeNET v7.0 file.
The script also checks that nothing it copies holds an "abstract" column.

Run: python scripts/make_data_release.py --out release [--third-party]
         [--extra /path/to/PREREGISTERED.csv:knowledge_bases/PREREGISTERED.csv]
"""
import argparse
import csv
import glob
import gzip
import hashlib
import os
import shutil
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import config

# relative paths or glob patterns under DATA_DIR / OUT_DIR
RELEASE = [
    # knowledge bases
    "provenance_opentargets.csv", "provenance_ctd.csv", "provenance_ctd_release.csv",
    "provenance_disgenet.csv", "provenance_gprofiler.csv",
    "raw/opentargets/*.jsonl", "raw/opentargets/terms.csv",
    "matrices/*.csv", "support_counts.csv", "opentargets_genes_by_datasource.csv",
    "disgenet_v7_diseases_matched.csv",
    "similarity/*.csv", "similarity_long.csv", "enrichment/*_annotated_*.csv",
    "null_similarity/*.csv", "similarity_robust/*.csv",
    # literature (no abstracts)
    "lit/queries_*.csv", "lit/counts_by_year_*.csv", "lit/records_manifest.csv",
    "lit/tag_summary_by_year*.csv", "lit/checks.csv", "lit/entity_counts.csv",
    "lit/headline_numbers.csv", "lit/share_by_year.csv",
    # trials (ClinicalTrials.gov records are public)
    "trials/raw/*.json.gz", "trials/provenance.csv", "trials/candidates_tagged.csv",
    "trials/denominator_by_start_year.csv", "trials/trial_screening_sheet.csv",
    "trials/trial_metrics.csv", "trials/trial_summary.csv", "trials/trial_share_by_start_year*.csv",
    # devices (FDA list and text snippets from public decision summaries)
    "devices/raw/f_178541", "devices/provenance.csv", "devices/devices_tagged.csv",
    "devices/device_screening_sheet.csv", "devices/device_metrics.csv",
    "devices/device_summary.csv", "devices/device_context_snippets.csv",
    # human screening
    "audit/human_review/*.xlsx", "audit/screening_final_trials.csv",
    "audit/screening_final_devices.csv", "audit/screening_summary.csv",
    "audit/tag_check/tag_check_strata.csv", "audit/tag_check/tags_sample_KEY.csv",
    # generated supplementary tables
    "supplement/*.tex",
]
THIRD_PARTY = ["raw/ctd/ctd_brain_subset.tsv.gz",
               "raw/disgenet_v7/curated_gene_disease_associations.tsv"]
DROP_TAG_COLUMNS = ["venue", "source_id", "aggregation_type", "cited_by"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find(pattern):
    """Files matching pattern; a path in OUT_DIR wins over the same path in DATA_DIR."""
    found = {}
    for root in (config.DATA_DIR, config.OUT_DIR):
        for p in glob.glob(str(root / pattern)):
            if os.path.isfile(p):
                found[os.path.relpath(p, root)] = p
    return found


def check_no_abstract(path):
    if path.endswith((".csv", ".csv.gz")):
        cols = pd.read_csv(path, nrows=0).columns
        bad = [c for c in cols if c.lower() in ("abstract", "dc:description")]
        if bad:
            sys.exit(f"refusing to release {path}: it has column(s) {bad}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--third-party", action="store_true")
    ap.add_argument("--extra", action="append", default=[], help="SRC:DEST, copy one more file")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    files = {}
    for pat in RELEASE + (THIRD_PARTY if a.third_party else []):
        hit = find(pat)
        if not hit:
            print(f"  missing: {pat}")
        files.update(hit)
    for e in a.extra:
        src, dest = e.split(":", 1)
        files[dest] = src

    for rel, src in sorted(files.items()):
        dest = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        check_no_abstract(src)
        shutil.copy2(src, dest)

    # tagged records without the Scopus metadata columns
    tag_src = config.inp("lit/tagged_records.csv.gz")
    t = pd.read_csv(tag_src)
    t = t.drop(columns=[c for c in DROP_TAG_COLUMNS if c in t.columns])
    os.makedirs(os.path.join(out, "lit"), exist_ok=True)
    with gzip.open(os.path.join(out, "lit", "tagged_records.csv.gz"), "wt", newline="") as f:
        t.to_csv(f, index=False)

    # FDA decision summaries: URL and hash of each stored PDF, not the PDFs
    sys.path.insert(0, str(config.SRC / "devices"))
    import importlib
    fda = importlib.import_module("01_fda_devices")
    dev = pd.read_csv(config.inp("devices/devices_tagged.csv"))
    rows = []
    for sub in dev.submission:
        p = fda.pdf_path(sub)
        rows.append([sub, fda.url_for(sub), os.path.getsize(p) if p else "", sha256(p) if p else ""])
    pd.DataFrame(rows, columns=["submission", "url", "bytes", "sha256"]).to_csv(
        os.path.join(out, "devices", "pdf_manifest.csv"), index=False)

    # hashes
    entries = []
    for root, _, names in os.walk(out):
        for n in names:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, out)
            if rel in ("SHA256SUMS", "MANIFEST.csv"):
                continue
            entries.append((rel, os.path.getsize(p), sha256(p)))
    entries.sort()
    with open(os.path.join(out, "SHA256SUMS"), "w") as f:
        for rel, _, h in entries:
            f.write(f"{h}  {rel}\n")
    with open(os.path.join(out, "MANIFEST.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "bytes", "sha256"])
        w.writerows(entries)
    total = sum(e[1] for e in entries)
    print(f"{len(entries)} files, {total / 1e6:.1f} MB -> {out}")


if __name__ == "__main__":
    main()
