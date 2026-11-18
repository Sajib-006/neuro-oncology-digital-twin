"""Pairwise similarity of tumor classes, per knowledge base and evidence level (Fig. 3c,d).

Input : matrices/<kb>_<level>_gene_entity.csv     (06_build_matrices.py)
Output: similarity/<kb>_<level>_<metric>.csv       class x class, metric = cosine or jaccard
        similarity_long.csv                         one row per (kb, level, metric, class pair)

Method notes:
1. No per-gene scaling. Scaling turns an all-zero column into a vector of constant
   values and gives similarity values to a class with no data. Cosine is computed on the
   raw score vectors.
2. Minimum support. A cell needs MIN_SUPPORT genes on BOTH classes or it is reported as
   NaN (no data, drawn grey). Never filled in.
3. Jaccard similarity on gene-set membership is given alongside cosine.

Run: python src/knowledge_bases/07_similarity.py
"""
import os, sys, itertools
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from entities import KEYS, MIN_SUPPORT

MAT = str(config.inp("matrices"))
OUT = str(config.out_dir("similarity"))
KGS = ["OpenTargets", "DisGeNET", "CTD"]
TIERS = ["curated", "all"]


def cosine(u, v):
    du, dv = np.linalg.norm(u), np.linalg.norm(v)
    if du == 0 or dv == 0:
        return np.nan
    return float(np.dot(u, v) / (du * dv))


def jaccard(u, v):
    a, b = u != 0, v != 0
    union = (a | b).sum()
    if union == 0:
        return np.nan
    return float((a & b).sum() / union)


def similarity(mat, metric):
    n = len(KEYS)
    out = pd.DataFrame(np.full((n, n), np.nan), index=KEYS, columns=KEYS)
    support = {e: int((mat[e] != 0).sum()) if e in mat.columns else 0 for e in KEYS}
    for a, b in itertools.combinations_with_replacement(KEYS, 2):
        if support[a] < MIN_SUPPORT or support[b] < MIN_SUPPORT:
            continue                      # no-data, stays NaN
        u = mat[a].values.astype(float)
        v = mat[b].values.astype(float)
        s = cosine(u, v) if metric == "cosine" else jaccard(u, v)
        out.loc[a, b] = out.loc[b, a] = s
    return out, support


def main():
    long_rows = []
    for kg in KGS:
        for tier in TIERS:
            path = os.path.join(MAT, f"{kg}_{tier}_gene_entity.csv")
            if not os.path.exists(path):
                print(f"  !! missing {path}")
                continue
            mat = pd.read_csv(path, index_col=0).reindex(columns=KEYS).fillna(0.0)
            for metric in ("cosine", "jaccard"):
                sim, support = similarity(mat, metric)
                sim.to_csv(os.path.join(OUT, f"{kg}_{tier}_{metric}.csv"))
                n_cells = int(sim.notna().sum().sum())
                n_poss = len(KEYS) ** 2
                print(f"  {kg:<12} {tier:<8} {metric:<8} "
                      f"{n_cells:>3}/{n_poss} cells have data")
                for a in KEYS:
                    for b in KEYS:
                        long_rows.append([kg, tier, metric, a, b, sim.loc[a, b],
                                          support[a], support[b]])

    df = pd.DataFrame(long_rows, columns=["kg", "tier", "metric", "entity_1",
                                          "entity_2", "similarity",
                                          "support_1", "support_2"])
    df.to_csv(config.out("similarity_long.csv"), index=False)
    print(f"\nwritten -> {OUT}/ and similarity_long.csv")

    print("\nEntities dropped for lack of support (min = "
          f"{MIN_SUPPORT} genes):")
    for kg in KGS:
        for tier in TIERS:
            sub = df[(df.kg == kg) & (df.tier == tier) & (df.metric == "cosine")]
            if sub.empty:
                continue
            dropped = sorted(sub[sub.support_1 < MIN_SUPPORT]["entity_1"].unique())
            if dropped:
                print(f"  {kg:<12} {tier:<8} {', '.join(dropped)}")


if __name__ == "__main__":
    main()
