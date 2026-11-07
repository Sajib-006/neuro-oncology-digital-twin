"""Pathway enrichment per tumor class with g:Profiler (KEGG and Reactome).

Input : matrices/<kb>_<level>_gene_entity.csv           (06_build_matrices.py)
Output: enrichment/<kb>_<level>_<background>_terms.csv            enriched terms per class
        enrichment/<kb>_<level>_<background>_pathway_jaccard.csv  class x class, on term sets
        provenance_gprofiler.csv                                  g:Profiler version, written once
Needs network (the g:Profiler API, free, no key). The paper used version e114_eg62_p19.
The term sets feed the pathway-level null test in 09_null_similarity.py.

Background (--background):
  annotated (DEFAULT, used in the paper) - all genes annotated in KEGG/Reactome, the
      standard g:Profiler scope.
  kg - the union of genes within the same knowledge base and level. A sensitivity check
      only. Do NOT use it for the curated levels of DisGeNET or CTD: a background barely
      larger than the query list leaves the test with no power.

Up to the 2,000 highest-scoring genes are sent for each class.
Run: python src/knowledge_bases/08_enrichment.py [--kg OpenTargets] [--tier all]
"""
import os, sys, json, time, argparse, itertools
import urllib.request
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from entities import KEYS, MIN_SUPPORT

URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
MAT = str(config.inp("matrices"))
OUT = str(config.OUT_DIR / "enrichment")
# Cap the gene list sent per entity. CTD-inferred entities carry >20k genes, which is
# not a hypothesis-driven set; the top slice by score keeps the request meaningful.
MAX_GENES = 2000


def gprofiler(genes, background=None):
    payload = {
        "organism": "hsapiens",
        "query": list(genes),
        "sources": ["KEGG", "REAC"],
        "user_threshold": 0.05,
        "significance_threshold_method": "g_SCS",
        "domain_scope": "custom" if background else "annotated",
        "no_evidences": True,
    }
    if background:
        payload["background"] = list(background)
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "AI4BrainCancer-review/1.0"})
    for attempt in range(4):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=180))
            meta = d.get("meta", {})
            ver = meta.get("version") or meta.get("genome_build") or ""
            path = config.out("provenance_gprofiler.csv")
            if not os.path.exists(path):                       # record the tool version once
                with open(path, "w") as f:
                    f.write("gprofiler_version,organism,sources,threshold,method,date\n")
                    f.write(f"{ver},hsapiens,KEGG;REAC,0.05,g_SCS,{time.strftime('%Y-%m-%d')}\n")
            return d.get("result", [])
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def run(kg, tier, bg_mode):
    path = os.path.join(MAT, f"{kg}_{tier}_gene_entity.csv")
    if not os.path.exists(path):
        print(f"  !! missing {path}")
        return
    mat = pd.read_csv(path, index_col=0).reindex(columns=KEYS).fillna(0.0)
    background = None
    if bg_mode == "kg":
        background = [g for g in mat.index.astype(str)]
        if len(background) < 1000:
            print(f"  {kg}/{tier}: KG background only {len(background)} genes - "
                  "too small for a meaningful test, skipped")
            return

    rows, termsets = [], {}
    for e in KEYS:
        col = mat[e]
        genes = col[col != 0].sort_values(ascending=False).index.astype(str)[:MAX_GENES]
        if len(genes) < MIN_SUPPORT:
            print(f"    {e:<22} support {len(genes)} < {MIN_SUPPORT}, skipped")
            termsets[e] = set()
            continue
        res = gprofiler(genes, background)
        termsets[e] = {r["native"] for r in res}
        for r in res:
            rows.append([kg, tier, e, r["source"], r["native"], r["name"],
                         r["p_value"], r["intersection_size"], r["term_size"]])
        print(f"    {e:<22} {len(genes):>5} genes -> {len(res):>4} enriched terms")
        time.sleep(0.5)

    os.makedirs(OUT, exist_ok=True)
    pd.DataFrame(rows, columns=["kg", "tier", "entity", "source", "term_id", "term_name",
                                "p_value", "intersection_size", "term_size"]
                 ).to_csv(os.path.join(OUT, f"{kg}_{tier}_{bg_mode}_terms.csv"), index=False)

    sim = pd.DataFrame(np.full((len(KEYS), len(KEYS)), np.nan), index=KEYS, columns=KEYS)
    for a, b in itertools.combinations_with_replacement(KEYS, 2):
        sa, sb = termsets[a], termsets[b]
        if not sa or not sb:
            continue
        sim.loc[a, b] = sim.loc[b, a] = len(sa & sb) / len(sa | sb)
    sim.to_csv(os.path.join(OUT, f"{kg}_{tier}_{bg_mode}_pathway_jaccard.csv"))
    print(f"  written -> {OUT}/{kg}_{tier}_{bg_mode}_*.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kg", default=None)
    ap.add_argument("--tier", default=None)
    ap.add_argument("--background", default="annotated", choices=["annotated", "kg"])
    a = ap.parse_args()
    kgs = [a.kg] if a.kg else ["OpenTargets", "DisGeNET", "CTD"]
    tiers = [a.tier] if a.tier else ["curated", "all"]
    for kg in kgs:
        for tier in tiers:
            print(f"\n{kg} / {tier}")
            run(kg, tier, a.background)


if __name__ == "__main__":
    main()
