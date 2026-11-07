"""Pre-specified coverage test: tumor-class similarity against a size-matched random null.

Input : matrices/<kb>_<level>_gene_entity.csv           (06_build_matrices.py)
        enrichment/<kb>_<level>_annotated_terms.csv      (08_enrichment.py)
Output: null_similarity/<level>_<kb>_<tier>_log2oe.csv   class x class score
        null_similarity/<level>_<kb>_<tier>_expected.csv mean random overlap
        null_similarity/size_check.csv                   the test, PASS or FAIL per setting

The method and the pass mark were fixed before the test was first run (2026-09-24).

Why
  Jaccard, cosine and pathway-profile correlation all track gene-list size; a log odds
  ratio over-corrects, because thin classes hold mostly well-studied "hub" genes that
  every class shares.

Method (pre-specified)
  For classes A, B in one knowledge base and level:
    O  = |A & B|, the observed overlap.
    Null: draw random sets A*, B* of sizes |A|, |B| from that setting's gene universe,
          without replacement, each gene weighted by (number of OTHER classes that
          contain it) + 1. A and B are left out of the weights so the pair cannot
          inflate its own null. 1,000 draws, seed 20260924.
    E  = mean overlap of A*, B* over the draws.
    Similarity = log2((O + 0.5) / (E + 0.5)), an effect size, deliberately NOT a
          z-score, because z-scores grow with sample size and would put the size
          effect straight back.
  Same procedure on significant pathway sets (annotated background), with pathway
  weights = number of other classes in which the pathway is significant.
  Classes need >= MIN_SUPPORT genes (gene level) or >= 10 significant terms (pathway level).

Acceptance test (pre-specified)
  |Spearman(similarity, log10 size of the smaller set)| < 0.30 in every setting with
  >= 6 measurable classes, written to size_check.csv with PASS or FAIL per row.

Run: python src/knowledge_bases/09_null_similarity.py   (a few minutes)
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from entities import KEYS, MIN_SUPPORT

MAT = str(config.inp("matrices"))
SIG = str(config.inp("enrichment"))
OUT = str(config.OUT_DIR / "null_similarity")
KGS = ["OpenTargets", "DisGeNET", "CTD"]
TIERS = ["curated", "all"]
N_DRAWS = 1000
SEED = 20260924
MIN_TERMS = 10
PASS_RHO = 0.30
MIN_ENTITIES_FOR_TEST = 6


def weighted_sample_sets(rng, weights, size, n_draws):
    """n_draws weighted samples without replacement (Efraimidis-Spirakis keys)."""
    logw = np.log(weights)
    out = np.empty((n_draws, size), dtype=np.int32)
    for k in range(n_draws):
        keys = np.log(rng.random(len(weights))) / np.exp(logw)   # log(u)/w, larger = earlier
        out[k] = np.argpartition(-keys, size - 1)[:size]
    return out


def null_similarity(sets, universe, rng):
    """sets: dict entity -> set of items (genes or pathways). Returns (sim, expected)."""
    items = np.array(sorted(universe))
    idx = {g: i for i, g in enumerate(items)}
    member = {e: np.zeros(len(items), dtype=bool) for e in sets}
    for e, s in sets.items():
        member[e][[idx[g] for g in s]] = True
    ents = [e for e in KEYS if e in sets]
    sim = pd.DataFrame(np.nan, index=KEYS, columns=KEYS)
    exp = pd.DataFrame(np.nan, index=KEYS, columns=KEYS)
    for i, a in enumerate(ents):
        for b in ents[i + 1:]:
            others = [e for e in ents if e not in (a, b)]
            w = 1.0 + (np.sum([member[e] for e in others], axis=0) if others else 0)
            A = weighted_sample_sets(rng, w, len(sets[a]), N_DRAWS)
            B = weighted_sample_sets(rng, w, len(sets[b]), N_DRAWS)
            ov = np.fromiter((np.intersect1d(A[k], B[k], assume_unique=True).size
                              for k in range(N_DRAWS)), dtype=float, count=N_DRAWS)
            O = len(sets[a] & sets[b])
            E = ov.mean()
            sim.loc[a, b] = sim.loc[b, a] = np.log2((O + 0.5) / (E + 0.5))
            exp.loc[a, b] = exp.loc[b, a] = E
    return sim, exp


def size_check(sim, sizes):
    rows = []
    for i, a in enumerate(KEYS):
        for b in KEYS[i + 1:]:
            if not np.isnan(sim.loc[a, b]):
                rows.append((sim.loc[a, b], np.log10(min(sizes[a], sizes[b]))))
    if len(rows) < 3:
        return np.nan, len(rows)
    d = pd.DataFrame(rows, columns=["v", "m"])
    return d.v.corr(d.m, method="spearman"), len(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    checks = []
    for level in ["gene", "pathway"]:
        for kg in KGS:
            for tier in TIERS:
                if level == "gene":
                    if not os.path.exists(os.path.join(MAT, f"{kg}_{tier}_gene_entity.csv")):
                        continue
                    m = pd.read_csv(os.path.join(MAT, f"{kg}_{tier}_gene_entity.csv"),
                                    index_col=0).reindex(columns=KEYS).fillna(0)
                    universe = set(m.index.astype(str))
                    sets = {e: set(m.index[m[e] != 0].astype(str)) for e in KEYS}
                    sets = {e: s for e, s in sets.items() if len(s) >= MIN_SUPPORT}
                else:
                    p = os.path.join(SIG, f"{kg}_{tier}_annotated_terms.csv")
                    if not os.path.exists(p):
                        continue
                    t = pd.read_csv(p)
                    sets = {e: set(t[t.entity == e].term_id) for e in KEYS}
                    sets = {e: s for e, s in sets.items() if len(s) >= MIN_TERMS}
                    universe = set().union(*sets.values()) if sets else set()
                n_ent = len(sets)
                if n_ent < 2:
                    print(f"  {level:<7} {kg:<12} {tier:<8} {n_ent} measurable, skipped")
                    continue
                sim, exp = null_similarity(sets, universe, rng)
                sim.to_csv(os.path.join(OUT, f"{level}_{kg}_{tier}_log2oe.csv"))
                exp.to_csv(os.path.join(OUT, f"{level}_{kg}_{tier}_expected.csv"))
                rho, npairs = size_check(sim, {e: len(s) for e, s in sets.items()})
                tested = n_ent >= MIN_ENTITIES_FOR_TEST
                verdict = ("PASS" if abs(rho) < PASS_RHO else "FAIL") if tested else "not tested (<6 entities)"
                checks.append([level, kg, tier, n_ent, npairs, round(rho, 3), verdict])
                print(f"  {level:<7} {kg:<12} {tier:<8} entities={n_ent:>2} pairs={npairs:>2} "
                      f"rho vs smaller size = {rho:+.2f}  -> {verdict}", flush=True)
    c = pd.DataFrame(checks, columns=["level", "kg", "tier", "entities", "pairs",
                                      "rho_vs_smaller_size", "verdict"])
    c.to_csv(os.path.join(OUT, "size_check.csv"), index=False)
    for level in ["gene", "pathway"]:
        sub = c[(c.level == level) & (c.verdict.isin(["PASS", "FAIL"]))]
        overall = "PASS" if len(sub) and (sub.verdict == "PASS").all() else "FAIL"
        print(f"\nOVERALL {level}-level: {overall}  ({(sub.verdict=='PASS').sum()}/{len(sub)} tested rows pass)")


if __name__ == "__main__":
    main()
