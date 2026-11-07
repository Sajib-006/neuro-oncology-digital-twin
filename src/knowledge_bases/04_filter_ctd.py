"""Filter the downloaded CTD gene-disease file to the brain tumor subset.

Input : raw/ctd/CTD_genes_diseases.tsv.gz      (from 03_download_ctd.sh)
Output: raw/ctd/ctd_brain_subset.tsv.gz
        provenance_ctd.csv                     (written last; it marks the subset as complete)

Downloading with curl (resumable) and filtering here is more reliable than streaming the
download, which can time out part-way through 130 million rows.
CTD splits evidence natively: DirectEvidence non-empty = curated, empty = inferred
through chemicals. Both are kept; 06_build_matrices.py separates them.

Run: python src/knowledge_bases/04_filter_ctd.py   (about 15 minutes)
"""
import os, re, sys, gzip, csv, hashlib, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config

SRC = str(config.inp("raw/ctd/CTD_genes_diseases.tsv.gz"))
OUT = str(config.out("raw/ctd/ctd_brain_subset.tsv.gz"))

KEEP = re.compile(
    r"glioblastoma|astrocytoma|oligodendroglioma|medulloblastoma|ependymoma|"
    r"meningioma|craniopharyngioma|rhabdoid|teratoid|glioma|pineoblastoma|"
    r"neuroma|schwannoma|brain neoplasm|central nervous system neoplasm",
    re.I,
)
COLS = ["GeneSymbol", "GeneID", "DiseaseName", "DiseaseID", "DirectEvidence",
        "InferenceChemicalName", "InferenceScore", "OmimIDs", "PubMedIDs"]


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"missing {SRC}")
    size = os.path.getsize(SRC)
    mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(SRC)).isoformat() + "Z"
    src_sha = hashlib.sha256()
    with open(SRC, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            src_sha.update(chunk)
    print(f"source {size/1e9:.2f} GB  sha256 {src_sha.hexdigest()[:16]}")

    n_in = n_kept = n_cur = 0
    sub_sha = hashlib.sha256()
    with gzip.open(SRC, "rb") as src, gzip.open(OUT, "wt", newline="") as dst:
        w = csv.writer(dst, delimiter="\t")
        w.writerow(COLS)
        for line in src:
            n_in += 1
            if line.startswith(b"#"):
                continue
            text = line.decode("utf-8", "replace")
            if not KEEP.search(text):
                continue
            row = text.rstrip("\n").split("\t")
            if len(row) < len(COLS):
                row += [""] * (len(COLS) - len(row))
            w.writerow(row[: len(COLS)])
            sub_sha.update(line)
            n_kept += 1
            if row[4].strip():
                n_cur += 1
            if n_in % 20_000_000 == 0:
                print(f"  {n_in:,} scanned, {n_kept:,} kept", flush=True)

    print(f"scanned {n_in:,}; kept {n_kept:,} "
          f"({n_cur:,} curated / {n_kept-n_cur:,} inferred)")

    with open(config.out("provenance_ctd.csv"), "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["source_url", "source_file_mtime_utc", "source_bytes",
                     "source_sha256_16", "pull_date", "rows_scanned", "rows_kept",
                     "rows_curated", "rows_inferred", "subset_sha256_16"])
        cw.writerow(["https://ctdbase.org/reports/CTD_genes_diseases.tsv.gz",
                     mtime, size, src_sha.hexdigest()[:16],
                     datetime.date.today().isoformat(), n_in, n_kept, n_cur,
                     n_kept - n_cur, sub_sha.hexdigest()[:16]])
    print(f"written -> {OUT} and provenance_ctd.csv")


if __name__ == "__main__":
    main()
