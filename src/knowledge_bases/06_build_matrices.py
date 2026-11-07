"""Build gene x tumor-class matrices for each knowledge base and evidence level.

Input : raw/opentargets/<class>.jsonl                          (02_opentargets_genes.py)
        raw/ctd/ctd_brain_subset.tsv.gz, provenance_ctd.csv     (04_filter_ctd.py)
        raw/disgenet_v7/curated_gene_disease_associations.tsv   (05_download_disgenet_v7.sh)
Output: matrices/<kb>_<level>_gene_entity.csv
        support_counts.csv                     genes per class per knowledge base and level
        opentargets_genes_by_datasource.csv    genes per class per Open Targets source
        disgenet_v7_diseases_matched.csv       DisGeNET disease names matched to each class
        provenance_ctd_release.csv             CTD report date, read from the file header

Main matrices: {OpenTargets, DisGeNET, CTD} x {curated, all}.
Sensitivity matrices:
  OpenTargets curatedplusdrug : curated + drug-trial targets (clinical_precedence)
  DisGeNET    curatednoctd    : curated rows supported by a source other than CTD
                                (DisGeNET imports CTD, so comparing DisGeNET-curated with
                                CTD-curated is partly a resource agreeing with itself)

Evidence levels, chosen so the three resources are comparable:

  curated  OpenTargets : direct associations with evidence from an expert-curated or
                         genetic source (CURATED_OT_DATASOURCES): COSMIC Cancer Gene
                         Census, IntOGen, ClinVar germline and somatic (eva,
                         eva_somatic), Cancer Biomarkers, GWAS credible sets, gene
                         burden, Genomics England, Gene2Phenotype, Orphanet, ClinGen,
                         UniProt, Reactome. Excluded: text mining (europepmc), expression
                         (expression_atlas), mouse models (impc), CRISPR screens and
                         drug-trial targets (clinical_precedence).
           DisGeNET    : v7.0 (2020) curated file, the last openly downloadable release
                         (PheKnowLator archive copy; see provenance_disgenet.csv)
           CTD         : DirectEvidence non-empty
  all      OpenTargets : every associated target
           DisGeNET    : not used. The v7.0 all-evidence file is no longer openly
                         available, and we did not mix in an older file.
           CTD         : every row (direct + chemical-inferred)

Run: python src/knowledge_bases/06_build_matrices.py
"""
import os, re, sys, json, gzip, csv, datetime
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
from entities import KEYS, NAME_PATTERNS

OUT = "matrices"
DG_V7 = str(config.inp("raw/disgenet_v7/curated_gene_disease_associations.tsv"))
CTD_SUBSET = str(config.inp("raw/ctd/ctd_brain_subset.tsv.gz"))
OT_DIR = str(config.inp("raw/opentargets"))

CURATED_OT_DATASOURCES = {
    "cancer_gene_census", "intogen", "eva_somatic", "cancer_biomarkers",       # somatic
    "eva", "gwas_credible_sets", "gene_burden", "genomics_england",          # genetic
    "gene2phenotype", "orphanet", "clingen", "uniprot_literature", "uniprot_variants",
    "reactome",                                                              # pathway
}
DRUG_OT_DATASOURCES = {"clinical_precedence"}
# DisGeNET curated sources other than CTD (v4 file: source column lists every source)
DG_CURATED_NONCTD = re.compile(r"UNIPROT|CLINVAR|ORPHANET|PSYGENET|CGI|CLINGEN|GENOMICS_ENGLAND", re.I)


def entity_of(name):
    """Map a free-text disease name to an entity key, or None."""
    s = str(name).lower()
    for key in KEYS:
        pat = NAME_PATTERNS[key]
        if not re.search(pat["include"], s):
            continue
        if pat["exclude"] and re.search(pat["exclude"], s):
            continue
        return key
    return None


def matrix_from_pairs(pairs):
    """pairs: list of (gene, entity, score) -> gene x entity DataFrame, max score."""
    if not pairs:
        return pd.DataFrame(index=[], columns=KEYS, dtype=float)
    df = pd.DataFrame(pairs, columns=["gene", "entity", "score"])
    m = df.pivot_table(index="gene", columns="entity", values="score", aggfunc="max")
    return m.reindex(columns=KEYS).fillna(0.0)


def build_opentargets():
    out, src_rows = {}, []
    tiers = {"curated": CURATED_OT_DATASOURCES,
             "curatedplusdrug": CURATED_OT_DATASOURCES | DRUG_OT_DATASOURCES,
             "all": None}
    for tier, keep in tiers.items():
        pairs = []
        for key in KEYS:
            path = os.path.join(OT_DIR, f"{key}.jsonl")
            if not os.path.exists(path):
                continue
            for line in open(path):
                r = json.loads(line)
                if tier == "all":
                    for ds in r["datasources"]:
                        src_rows.append([key, ds])
                if keep is not None:
                    ds = set(r["datasources"]) & keep
                    if not ds:
                        continue
                    score = max(r["datasources"][d] for d in ds)
                else:
                    score = r["score"]
                pairs.append((r["gene"], key, score))
        out[tier] = matrix_from_pairs(pairs)
    # genes per class per datasource, for the supplement
    pd.DataFrame(src_rows, columns=["entity", "datasource"]).pivot_table(
        index="datasource", columns="entity", aggfunc="size", fill_value=0
    ).reindex(columns=KEYS).fillna(0).astype(int).to_csv(config.out("opentargets_genes_by_datasource.csv"))
    return out


def build_disgenet():
    """DisGeNET v7.0 curated only (provenance_disgenet.csv is written by the download step)."""
    if not os.path.exists(DG_V7):
        print(f"  !! DisGeNET v7 file missing: {DG_V7}")
        return {"curated": matrix_from_pairs([])}
    d = pd.read_csv(DG_V7, sep="\t", low_memory=False)
    d["entity"] = d["diseaseName"].map(entity_of)
    d = d.dropna(subset=["entity"])
    out = {"curated": matrix_from_pairs(list(zip(d["geneSymbol"], d["entity"], d["score"])))}
    c = d[d["source"].astype(str).str.contains(DG_CURATED_NONCTD)]
    out["curatednoctd"] = matrix_from_pairs(list(zip(c["geneSymbol"], c["entity"], c["score"])))
    d[["entity", "diseaseId", "diseaseName"]].drop_duplicates().sort_values(["entity", "diseaseName"]).to_csv(
        config.out("disgenet_v7_diseases_matched.csv"), index=False)
    return out


def build_ctd():
    out = {}
    # provenance_ctd.csv is written only after the filter completes, so it is the
    # signal that the subset is whole.
    if not (os.path.exists(CTD_SUBSET) and config.inp("provenance_ctd.csv").exists()):
        print("  !! CTD subset incomplete or missing (run 04_filter_ctd.py) - skipping")
        return {"curated": matrix_from_pairs([]), "all": matrix_from_pairs([])}
    raw = config.inp("raw/ctd/CTD_genes_diseases.tsv.gz")
    if os.path.exists(raw):                                  # release date from the file header
        with gzip.open(raw, "rt") as fh:
            for line in fh:
                if line.startswith("# Report created:"):
                    with open(config.out("provenance_ctd_release.csv"), "w") as f:
                        f.write("ctd_report_created\n" + line.split(":", 1)[1].strip() + "\n")
                    break
                if not line.startswith("#"):
                    break
    d = pd.read_csv(CTD_SUBSET, sep="\t", low_memory=False)
    d["entity"] = d["DiseaseName"].map(entity_of)
    d = d.dropna(subset=["entity"])
    d["is_curated"] = d["DirectEvidence"].astype(str).str.strip().replace("nan", "") != ""
    # CTD has no continuous score for direct evidence; use 1.0 for curated,
    # InferenceScore (scaled) for inferred.
    d["sc"] = d["InferenceScore"].fillna(0.0)
    d.loc[d["is_curated"], "sc"] = 1.0
    out["all"] = matrix_from_pairs(list(zip(d["GeneSymbol"], d["entity"], d["sc"])))
    c = d[d["is_curated"]]
    out["curated"] = matrix_from_pairs(list(zip(c["GeneSymbol"], c["entity"], c["sc"])))
    return out


def main():
    built = {"OpenTargets": build_opentargets(),
             "DisGeNET": build_disgenet(),
             "CTD": build_ctd()}

    rows = []
    for kg, tiers in built.items():
        for tier, m in tiers.items():
            path = config.out(f"{OUT}/{kg}_{tier}_gene_entity.csv")
            m.to_csv(path)
            for e in KEYS:
                n = int((m[e] != 0).sum()) if e in m.columns else 0
                rows.append([kg, tier, e, n, m.shape[0]])
            print(f"  {kg:<12} {tier:<8} genes={m.shape[0]:>6,}  -> {path}")

    sup = pd.DataFrame(rows, columns=["kg", "tier", "entity", "genes", "kg_total_genes"])
    sup.to_csv(config.out("support_counts.csv"), index=False)

    print("\nGenes per entity (rows) by KG and tier (columns):")
    piv = sup.pivot_table(index="entity", columns=["kg", "tier"], values="genes").reindex(KEYS)
    print(piv.fillna(0).astype(int).to_string())
    print(f"\nwritten -> {config.OUT_DIR}/support_counts.csv")


if __name__ == "__main__":
    main()
