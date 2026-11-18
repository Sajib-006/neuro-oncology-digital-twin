"""Further tests of whether tumor-class similarity reflects coverage (Fig. 3e; not pre-specified).

Input : matrices/<kb>_<level>_gene_entity.csv           (06_build_matrices.py)
Output: similarity_robust/pairs_<kb>_<level>.csv        per pair: sizes, overlap, three scores
        similarity_robust/size_check_robust.csv         correlation with size, 95% CI, P, reading

09_null_similarity.py is kept unchanged and still reported: it was fixed before it was
run, and it failed. This stage was written after that result was seen, so it is NOT
pre-specified, and the paper says so. It adds three things:

1. A null that keeps degrees (Curveball algorithm; Strona et al. 2014).
   The gene x tumor membership matrix is randomized by "trades" between two tumors: the
   genes that only one of the two tumors has are pooled and dealt back at random, keeping
   each tumor's size. Every gene keeps the number of tumors it belongs to (its degree), and
   every tumor keeps its size. 09_null_similarity.py instead drew genes with weight
   (degree + 1), which keeps sizes but not degrees.
   E = mean overlap over null samples; score = log2((O + 0.5) / (E + 0.5)).

2. A size-matched comparison. Jaccard is capped by the ratio of the two set sizes, so part
   of its link with size is arithmetic. Here every tumor's gene set is downsampled at
   random to the same size n (the smallest measurable set in that resource and level),
   500 times, and Jaccard is averaged. Equal sizes remove the cap.

3. Uncertainty. For every Spearman correlation between a similarity score and the smaller
   set's size, a tumor-level bootstrap 95% interval (tumors resampled with replacement;
   pairs of a tumor with its own copy dropped; 2,000 resamples) and a permutation P value
   (tumor sizes shuffled across tumors; 5,000 permutations).

Reading rule (the |rho| < 0.3 band of the pre-specified test, applied to the interval):
"coverage-free" only if the whole 95% interval lies inside (-0.3, 0.3); "coverage-linked"
if it lies wholly outside; otherwise "unclear".

Run: python src/knowledge_bases/10_similarity_robust.py
"""
import os, sys, itertools
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from entities import KEYS, MIN_SUPPORT

MAT = str(config.inp("matrices"))
OUT = str(config.OUT_DIR / "similarity_robust")
KGS = ["OpenTargets", "DisGeNET", "CTD"]
SEED = 20260928
N_NULL = 1000          # null matrices kept
TRADES_BURN = 20000    # trades before the first kept sample
TRADES_THIN = 200      # trades between kept samples
N_DOWN = 500
N_BOOT = 2000
N_PERM = 5000
BAND = 0.30


def tiers(kg):
    suf = "_gene_entity.csv"
    return sorted(f[len(kg) + 1:-len(suf)] for f in os.listdir(MAT)
                  if f.startswith(kg + "_") and f.endswith(suf))


def curveball_expected(M, rng):
    """M: bool array genes x tumors. Returns expected pairwise overlap (tumors x tumors)."""
    M = M.copy()
    k = M.shape[1]
    acc = np.zeros((k, k))

    def trade():
        a, b = rng.choice(k, 2, replace=False)
        ca, cb = M[:, a], M[:, b]
        only = np.flatnonzero(ca ^ cb)
        if only.size == 0:
            return
        na = int((ca & ~cb).sum())
        if na == 0 or na == only.size:
            return
        pool = rng.permutation(only)
        M[pool[:na], a] = True;  M[pool[:na], b] = False
        M[pool[na:], a] = False; M[pool[na:], b] = True

    for _ in range(TRADES_BURN):
        trade()
    Mi = M.astype(np.int32)
    for _ in range(N_NULL):
        for _ in range(TRADES_THIN):
            trade()
        np.copyto(Mi, M, casting="unsafe")
        acc += Mi.T @ Mi
    acc /= N_NULL
    np.fill_diagonal(acc, 0)
    return acc


def downsampled_jaccard(sets, n, rng):
    """Mean Jaccard after downsampling every set to n genes, N_DOWN times."""
    subs = {e: [frozenset(rng.choice(np.array(sorted(s)), n, replace=False).tolist())
                for _ in range(N_DOWN)] for e, s in sets.items()}
    out = {}
    for a, b in itertools.combinations(list(sets), 2):
        out[(a, b)] = float(np.mean([len(A & B) / len(A | B) for A, B in zip(subs[a], subs[b])]))
    return out


def spearman(x, y):
    return pd.Series(x).corr(pd.Series(y), method="spearman")


def size_rho_with_uncertainty(scores, sizes, rng):
    """scores: dict (a,b)->value; sizes: dict tumor->size."""
    ents = sorted(sizes)
    def rho_for(sample):
        xs, ys = [], []
        for i, j in itertools.combinations(range(len(sample)), 2):
            a, b = sample[i], sample[j]
            if a == b:
                continue
            key = (a, b) if (a, b) in scores else (b, a)
            xs.append(scores[key]); ys.append(np.log10(min(sizes[a], sizes[b])))
        return spearman(xs, ys) if len(set(ys)) > 1 and len(xs) >= 3 else np.nan
    obs = rho_for(ents)
    boots = np.array([rho_for(list(rng.choice(ents, len(ents), replace=True))) for _ in range(N_BOOT)])
    boots = boots[~np.isnan(boots)]
    lo, hi = np.percentile(boots, [2.5, 97.5]) if len(boots) else (np.nan, np.nan)
    # permutation: shuffle sizes across tumors
    perm = []
    vals = [sizes[e] for e in ents]
    for _ in range(N_PERM):
        sh = dict(zip(ents, rng.permutation(vals)))
        xs, ys = [], []
        for a, b in itertools.combinations(ents, 2):
            key = (a, b) if (a, b) in scores else (b, a)
            xs.append(scores[key]); ys.append(np.log10(min(sh[a], sh[b])))
        perm.append(spearman(xs, ys))
    perm = np.array(perm)
    p = (np.sum(np.abs(perm) >= abs(obs)) + 1) / (len(perm) + 1)
    if hi < BAND and lo > -BAND:
        reading = "coverage-free"
    elif lo >= BAND or hi <= -BAND:
        reading = "coverage-linked"
    else:
        reading = "unclear"
    return obs, lo, hi, p, reading


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    rows = []
    for kg in KGS:
        for tier in tiers(kg):
            path = os.path.join(MAT, f"{kg}_{tier}_gene_entity.csv")
            if not os.path.exists(path):
                continue
            m = pd.read_csv(path, index_col=0).reindex(columns=KEYS).fillna(0)
            sets = {e: set(m.index[m[e] != 0].astype(str)) for e in KEYS}
            sets = {e: s for e, s in sets.items() if len(s) >= MIN_SUPPORT}
            ents = [e for e in KEYS if e in sets]
            if len(ents) < 3:
                print(f"  {kg:<12} {tier:<14} {len(ents)} measurable tumors, skipped")
                continue
            sizes = {e: len(sets[e]) for e in ents}
            genes = sorted(set().union(*sets.values()))
            gi = {g: i for i, g in enumerate(genes)}
            M = np.zeros((len(genes), len(ents)), dtype=bool)
            for j, e in enumerate(ents):
                M[[gi[g] for g in sets[e]], j] = True
            E = curveball_expected(M, rng)
            n_min = min(sizes.values())
            dj = downsampled_jaccard(sets, n_min, rng)

            metrics = {"jaccard": {}, "curveball_log2oe": {}, "downsampled_jaccard": dj}
            pair_rows = []
            for i, j in itertools.combinations(range(len(ents)), 2):
                a, b = ents[i], ents[j]
                O = len(sets[a] & sets[b])
                metrics["jaccard"][(a, b)] = O / len(sets[a] | sets[b])
                metrics["curveball_log2oe"][(a, b)] = np.log2((O + 0.5) / (E[i, j] + 0.5))
                pair_rows.append([kg, tier, a, b, sizes[a], sizes[b], O, round(E[i, j], 2),
                                  metrics["jaccard"][(a, b)], metrics["curveball_log2oe"][(a, b)],
                                  dj[(a, b)]])
            pd.DataFrame(pair_rows, columns=["kg", "tier", "entity_1", "entity_2", "size_1", "size_2",
                                             "observed", "expected_curveball", "jaccard",
                                             "curveball_log2oe", "downsampled_jaccard"]
                         ).to_csv(os.path.join(OUT, f"pairs_{kg}_{tier}.csv"), index=False)
            for name, sc in metrics.items():
                rho, lo, hi, p, reading = size_rho_with_uncertainty(sc, sizes, rng)
                rows.append([kg, tier, name, len(ents), len(sc), n_min, round(rho, 3),
                             round(lo, 3), round(hi, 3), round(p, 4), reading])
                print(f"  {kg:<12} {tier:<14} {name:<20} tumors={len(ents):>2} rho={rho:+.2f} "
                      f"[{lo:+.2f}, {hi:+.2f}] p={p:.3f} -> {reading}", flush=True)
    pd.DataFrame(rows, columns=["kg", "tier", "metric", "tumors", "pairs", "downsample_n",
                                "rho_vs_smaller_size", "ci_low", "ci_high", "perm_p", "reading"]
                 ).to_csv(os.path.join(OUT, "size_check_robust.csv"), index=False)
    print(f"\nwritten -> {OUT}/size_check_robust.csv")


if __name__ == "__main__":
    main()
