#!/usr/bin/env bash
# Download the Open Targets Platform release files used by 02_opentargets_genes.py.
#   input : the EBI FTP site (network, about 2.5 GB)
#   output: $OUT_DIR/raw/opentargets_bulk/<release>/{association_*_direct,disease,target}/*.parquet
#           plus SHA256SUMS and DOWNLOADED in that folder
# The GraphQL API pages `associatedTargets` unstably (about 3% of rows come back twice
# and others are missed, checked 2026-09-28), so we build from the release files.
# Files are fetched in parallel to *.part and renamed when complete.
# Run: bash src/knowledge_bases/01_download_opentargets.sh 26.09
set -euo pipefail
REL=${1:-26.09}
DATA_DIR=${DATA_DIR:-$(cd "$(dirname "$0")/../.." && pwd)/data}
BASE=https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/$REL/output
OUT_DIR=${OUT_DIR:-$DATA_DIR}
DEST=$OUT_DIR/raw/opentargets_bulk/$REL
list=()
for d in association_by_datasource_direct association_by_datatype_direct association_overall_direct disease target; do
  mkdir -p "$DEST/$d"
  for f in $(curl -s "$BASE/$d/" | grep -oE 'href="[^"?/][^"]*\.parquet"' | cut -d'"' -f2); do
    [ -s "$DEST/$d/$f" ] || list+=("$d/$f")
  done
done
echo "${#list[@]} files to fetch"
printf '%s\n' "${list[@]}" | xargs -P 8 -I{} sh -c \
  'curl -s --retry 5 -o "'"$DEST"'/{}.part" "'"$BASE"'/{}" && mv "'"$DEST"'/{}.part" "'"$DEST"'/{}" && echo "done {}"'
( cd "$DEST" && find . -name "*.parquet" -exec sha256sum {} \; | sort -k2 ) > "$DEST/SHA256SUMS"
echo "release $REL downloaded $(date -u +%FT%TZ)" > "$DEST/DOWNLOADED"
echo ALL DONE
