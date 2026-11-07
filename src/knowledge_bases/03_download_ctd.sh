#!/usr/bin/env bash
# Download the full CTD gene-disease file (about 3.2 GB, resumable).
#   input : https://ctdbase.org/reports/CTD_genes_diseases.tsv.gz (network)
#   output: $OUT_DIR/raw/ctd/CTD_genes_diseases.tsv.gz
# The paper used the report created on 28 August 2026 (downloaded 24 September 2026).
# CTD serves only its current report, so a new download may differ.
# Run: bash src/knowledge_bases/03_download_ctd.sh
set -euo pipefail
DATA_DIR=${DATA_DIR:-$(cd "$(dirname "$0")/../.." && pwd)/data}
OUT_DIR=${OUT_DIR:-$DATA_DIR}
mkdir -p "$OUT_DIR/raw/ctd"
curl -L --retry 10 --retry-delay 5 --retry-all-errors -C - \
  -o "$OUT_DIR/raw/ctd/CTD_genes_diseases.tsv.gz" \
  https://ctdbase.org/reports/CTD_genes_diseases.tsv.gz
echo "download done: $(ls -lh "$OUT_DIR/raw/ctd/CTD_genes_diseases.tsv.gz" | awk '{print $5}')"
