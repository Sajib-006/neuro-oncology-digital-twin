"""Gene (target) associations per tumor class from the Open Targets Platform release files.

Input : raw/opentargets_bulk/<release>/  (parquet files from 01_download_opentargets.sh)
Output: raw/opentargets/<class>.jsonl    one row per target
        raw/opentargets/terms.csv        which ontology terms each class uses
        provenance_opentargets.csv       release, file hashes, counts

Built from the release files, not from the GraphQL API, for two reasons:

1. Paging. The API's `associatedTargets` pages are not stable: for glioblastoma about
   3% of rows came back twice and the same number of targets were never returned, with
   or without an explicit sort order. The release files have every row exactly once.

2. Direct vs indirect evidence. The API default propagates evidence up the disease
   ontology, so "astrocytoma (excluding glioblastoma)" would inherit every pilocytic
   astrocytoma gene (pilocytic astrocytoma is its descendant). We use DIRECT
   associations for the class term and for each descendant term, and drop any
   descendant that is itself (or sits below) another class in our set. Each class keeps
   its own subtypes but never another class's evidence.

Classes are resolved by ontology ID, so no disease-name matching is involved.

Scores kept per target:
  score        overall direct association score (max over the class's terms)
  datasources  {datasourceId: score}, max over terms
  datatypes    {datatypeId: score}, max over terms (from association_by_datatype_direct)

Run: python src/knowledge_bases/02_opentargets_genes.py [release]
"""
import json, os, sys, csv, hashlib, datetime, glob
import pyarrow.parquet as pq
import pyarrow.compute as pc
import pyarrow as pa

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from entities import ENTITIES

REL = sys.argv[1] if len(sys.argv) > 1 else config.OPENTARGETS_RELEASE
BULK = str(config.inp(f"raw/opentargets_bulk/{REL}"))
OUT = str(config.out_dir("raw/opentargets"))


def read(name, columns, filt=None):
    files = sorted(glob.glob(os.path.join(BULK, name, "*.parquet")))
    if not files:
        sys.exit(f"missing {BULK}/{name}; run 01_download_opentargets.sh {REL} first")
    tabs = []
    for f in files:
        t = pq.read_table(f, columns=columns)
        if filt is not None:
            t = t.filter(filt(t))
        tabs.append(t)
    return pa.concat_tables(tabs).to_pylist()


def main():
    disease = {r["id"]: r for r in read("disease", ["id", "name", "descendants"])}
    entity_ids = {efo: key for key, _, efo, _ in ENTITIES}

    desc = {key: list(disease[efo]["descendants"] or []) for key, _, efo, _ in ENTITIES}
    blocked = {}
    for key, _, efo, _ in ENTITIES:
        blocked[key] = set()
        for t in desc[key]:
            if t in entity_ids:
                other = entity_ids[t]
                blocked[key] |= {t} | set(desc[other])
    terms = {key: [efo] + [t for t in desc[key] if t not in blocked[key]]
             for key, _, efo, _ in ENTITIES}
    all_terms = pa.array(sorted({t for ts in terms.values() for t in ts}))

    in_terms = lambda t: pc.is_in(t["diseaseId"], value_set=all_terms)
    cols = ["diseaseId", "targetId", "aggregationValue", "associationScore"]
    overall = read("association_overall_direct", cols, in_terms)
    by_src = read("association_by_datasource_direct", cols, in_terms)
    by_dt = read("association_by_datatype_direct", cols, in_terms)
    tids = pa.array(sorted({r["targetId"] for r in overall}))
    symbol = {r["id"]: r["approvedSymbol"] for r in
              read("target", ["id", "approvedSymbol"], lambda t: pc.is_in(t["id"], value_set=tids))}

    ov = {}
    for r in overall:
        ov.setdefault(r["diseaseId"], {})[r["targetId"]] = r["associationScore"]
    src, dty = {}, {}
    for rows, store in ((by_src, src), (by_dt, dty)):
        for r in rows:
            store.setdefault(r["diseaseId"], {}).setdefault(r["targetId"], []).append(
                (r["aggregationValue"], r["associationScore"]))

    prov, term_rows = [], []
    for key, label, efo, family in ENTITIES:
        merged = {}
        for term in terms[key]:
            hits = ov.get(term, {})
            term_rows.append([key, term, disease[term]["name"], len(hits), term == efo])
            for tid, score in hits.items():
                m = merged.setdefault(tid, {"entity": key, "gene": symbol.get(tid, tid),
                                            "ensembl": tid, "score": 0.0,
                                            "datasources": {}, "datatypes": {}, "terms": []})
                m["score"] = max(m["score"], score)
                m["terms"].append(term)
                for ds, sc in src.get(term, {}).get(tid, []):
                    m["datasources"][ds] = max(m["datasources"].get(ds, 0.0), sc)
                for dt, sc in dty.get(term, {}).get(tid, []):
                    m["datatypes"][dt] = max(m["datatypes"].get(dt, 0.0), sc)
        path = os.path.join(OUT, f"{key}.jsonl")
        with open(path, "w") as f:
            for r in merged.values():
                f.write(json.dumps(r) + "\n")
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
        prov.append([key, label, efo, REL, datetime.date.today().isoformat(), len(merged), h,
                     len(terms[key]), ";".join(sorted(blocked[key]))])
        note = f"  (excluded {len(blocked[key])} terms owned by another entity)" if blocked[key] else ""
        print(f"  {key:<22} {efo:<16} terms={len(terms[key]):3} {len(merged):>6,} targets{note}")

    with open(os.path.join(OUT, "terms.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity", "term", "term_name", "n_direct_targets", "is_entity_term"])
        w.writerows(term_rows)
    with open(config.out("provenance_opentargets.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity", "label", "ontology_id", "data_version", "build_date", "n_targets",
                    "sha256_16", "n_terms", "excluded_terms"])
        w.writerows(prov)
    print(f"\nOpen Targets release {REL}; written -> {OUT}/ and provenance_opentargets.csv")


if __name__ == "__main__":
    main()
