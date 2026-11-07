"""Compare a fresh run (OUT_DIR) with the stored or released outputs (DATA_DIR), file by file.

Input : every .csv, .csv.gz, .tex, .jsonl and .txt file under OUT_DIR, and the file at the
        same relative path under DATA_DIR
Output: a table printed to the screen and, with --csv, written to a file:
        path, status, rows, detail
Status:
  same        identical bytes
  equal       same table: same columns, same rows, numbers equal within --rtol / --atol
  differs     the table or text differs (detail says where)
  new         no file at that path under DATA_DIR
Columns named in --ignore (default: dates of the run and download stamps) are not compared.
Run: DATA_DIR=... OUT_DIR=... python scripts/compare_outputs.py [--csv compare.csv]
"""
import argparse
import filecmp
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import config

EXT = (".csv", ".csv.gz", ".tex", ".jsonl", ".txt")
IGNORE = ["pull_date", "build_date", "download_date", "date"]


def read_table(p):
    if p.endswith(".jsonl"):
        return pd.read_json(p, lines=True)
    with open(p, "rb") as f:
        head = f.read(2)
    # the blank screening sheets start with '#' comment lines
    return pd.read_csv(p, comment="#" if head == b"# " else None, low_memory=False)


def compare_tables(a, b, rtol, atol, ignore):
    if list(a.columns) != list(b.columns):
        extra = set(a.columns) ^ set(b.columns)
        return "differs", f"columns differ: {sorted(extra)[:6]}"
    if len(a) != len(b):
        return "differs", f"rows {len(a)} vs {len(b)}"
    bad = []
    for c in a.columns:
        if c in ignore:
            continue
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            xv, yv = x.to_numpy(float), y.to_numpy(float)
            ok = np.isclose(xv, yv, rtol=rtol, atol=atol, equal_nan=True)
            if not ok.all():
                d = np.nanmax(np.abs(xv - yv)[~ok])
                bad.append(f"{c}: {int((~ok).sum())} cells, max diff {d:.3g}")
        else:
            xs, ys = x.astype(str).where(x.notna(), ""), y.astype(str).where(y.notna(), "")
            n = int((xs != ys).sum())
            if n:
                bad.append(f"{c}: {n} cells")
    return ("equal", "") if not bad else ("differs", "; ".join(bad[:5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--atol", type=float, default=1e-12)
    ap.add_argument("--ignore", nargs="*", default=IGNORE)
    ap.add_argument("--csv")
    a = ap.parse_args()
    rows = []
    for root, _, names in os.walk(config.OUT_DIR):
        for n in sorted(names):
            p = os.path.join(root, n)
            rel = os.path.relpath(p, config.OUT_DIR)
            if not rel.endswith(EXT) or rel.startswith("figures"):
                continue
            q = os.path.join(config.DATA_DIR, rel)
            if not os.path.exists(q):
                rows.append([rel, "new", "", ""])
                continue
            if filecmp.cmp(p, q, shallow=False):
                rows.append([rel, "same", "", ""])
                continue
            if rel.endswith((".tex", ".txt")):
                la, lb = open(p).read().splitlines(), open(q).read().splitlines()
                diff = [i for i, (x, y) in enumerate(zip(la, lb)) if x != y]
                det = f"{len(diff)} lines differ (first: {diff[:3]}), {len(la)} vs {len(lb)} lines"
                rows.append([rel, "differs", len(la), det])
                continue
            try:
                ta, tb = read_table(p), read_table(q)
                st, det = compare_tables(ta, tb, a.rtol, a.atol, a.ignore)
                rows.append([rel, st, len(ta), det])
            except Exception as e:
                rows.append([rel, "differs", "", f"could not compare: {e}"])
    df = pd.DataFrame(rows, columns=["path", "status", "rows", "detail"]).sort_values("path")
    with pd.option_context("display.max_rows", None, "display.max_colwidth", 120, "display.width", 250):
        print(df.to_string(index=False))
    print("\n" + df.status.value_counts().to_string())
    if a.csv:
        df.to_csv(a.csv, index=False)


if __name__ == "__main__":
    main()
