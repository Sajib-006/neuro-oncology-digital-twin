"""Check of the combined-data measure (Fig. 3b lenient line; Section 4 text).

Input : lit/tagged_records.csv.gz   (03_tag_records.py)
Output: printed only: mention vs used rate per data type, number of data types per paper,
        overlap with fusion terms, the lenient share (2+ data types mentioned anywhere)
        and the data-type pairs among combined-data papers.
Frame: T and A visible, tumor term in title or keywords, articles and conference papers with
an abstract, 2015-2026 (review titles are not removed here).
Run: python src/literature/08_multimodal_sanity.py
"""
import itertools
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config

t = pd.read_csv(config.inp("lit/tagged_records.csv.gz"))
f = t[(t.in_primary_set == 1) & (t.T_focus == 1) & (t.year >= 2015) & (t.doctype.isin(["ar", "cp"])) & (t.has_abstract == 1)]
print(f"frame: {len(f):,} research records 2015-2026\n")
mods = [c for c in f.columns if c.startswith("M") and c.endswith("_used")]
print(f"{'modality':<20} {'mention':>8} {'used':>7}  used/mention")
for c in mods:
    m = c[:-5] + "_mention"
    print(f"{c[:-5]:<20} {f[m].mean():8.1%} {f[c].mean():7.1%}  {f[c].sum() / max(f[m].sum(), 1):.2f}")
print("\nn_modalities_used:", f.n_modalities_used.value_counts().sort_index().to_dict())
mm, x1 = f.multimodal_used == 1, f.X1_fusion_vocab == 1
print(f"\nmultimodal_used {mm.sum()}, fusion vocab {x1.sum()}, both {(mm & x1).sum()}")
print(f"of fusion-vocab papers, share with >=2 modalities used: {(mm & x1).sum() / x1.sum():.0%}")
m2 = f[[c[:-5] + "_mention" for c in mods]].sum(axis=1) >= 2
print(f"lenient (>=2 modalities MENTIONED): {m2.sum():,} = {m2.mean():.1%}")
print("\nmodality pairs among multimodal_used (n>=5):")
for a, b in itertools.combinations(mods, 2):
    n = ((f[a] == 1) & (f[b] == 1)).sum()
    if n >= 5:
        print(f"  {a[:-5]:<18} + {b[:-5]:<18} {n}")
