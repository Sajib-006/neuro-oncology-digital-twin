"""Partial-year check: is the 2026 rise in external validation and prospective studies real,
or a change in the mix of journal articles and conference papers? (Fig. 4a, 2026 values)

Input : lit/tagged_records.csv.gz   (03_tag_records.py), through lit_data.focused_research()
Output: printed only: per year 2024-2026, the conference-paper share and the X2 and X3
        shares in all papers and in journal articles only.
Run: python src/literature/09_partial_year_check.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config  # noqa: F401  (sets up paths)
import lit_data as D

df = D.focused_research()
for y in (2024, 2025, 2026):
    s = df[df.year == y]
    cp = (s.doctype == "cp").mean()
    line = f"{y}: n={len(s):,}  conference share {cp:.0%}"
    for col in ["X2_external_validation", "X3_prospective"]:
        allv = s[col].mean()
        ar = s[s.doctype == "ar"][col].mean()
        line += f" | {col[:11]} all {allv:.1%}, articles only {ar:.1%}"
    print(line)
