#!/usr/bin/env bash
# Download the DisGeNET v7.0 curated gene-disease file (2020) from the PheKnowLator archive,
# and record its provenance. DisGeNET v7.0 is the last release that can be downloaded openly.
#   input : the archive URL below (network, about 10 MB)
#   output: $OUT_DIR/raw/disgenet_v7/curated_gene_disease_associations.tsv
#           $OUT_DIR/provenance_disgenet.csv
# The paper's copy was downloaded on 2026-09-29; its sha256 starts with 754b07fba4ec2dac.
# Run: bash src/knowledge_bases/05_download_disgenet_v7.sh
set -euo pipefail
DATA_DIR=${DATA_DIR:-$(cd "$(dirname "$0")/../.." && pwd)/data}
OUT_DIR=${OUT_DIR:-$DATA_DIR}
URL=https://storage.googleapis.com/pheknowlator/archived_builds/release_v3.0.2/build_01NOV2021/data/original_data/curated_gene_disease_associations.tsv
F=$OUT_DIR/raw/disgenet_v7/curated_gene_disease_associations.tsv
mkdir -p "$(dirname "$F")"
curl -L --retry 5 -o "$F" "$URL"
SHA=$(sha256sum "$F" | cut -c1-16)
ROWS=$(( $(wc -l < "$F") - 1 ))
echo "sha256 $SHA, $ROWS rows (paper: 754b07fba4ec2dac, 84038 rows)"
{
  echo "release,level,rows,source_url,mirror,download_date,sha256_16"
  echo "DisGeNET v7.0 (2020),curated,$ROWS,$URL,PheKnowLator archive build 01NOV2021,$(date +%F),$SHA"
} > "$OUT_DIR/provenance_disgenet.csv"
