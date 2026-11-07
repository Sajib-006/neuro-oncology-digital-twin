"""Tag every downloaded record with every term block, locally.

Input : lit/records/T_A_<year>.jsonl.gz      (02_scopus_records.py)
Output: lit/tagged_records.csv.gz            one row per unique record, 0/1 flags
        lit/tag_summary_by_year.csv          counts per flag per year (records with T and A visible)
        lit/tag_summary_by_year_allpulled.csv  the same for all downloaded records

Text searched = title + abstract + author keywords (the local form of Scopus
TITLE-ABS-KEY; Scopus also searches indexed keywords, so local counts can run slightly
below API counts; 04_checks.py reports the agreement).

Data-type flags come in two strengths:
  <Mk>_mention  any match in title, abstract or keywords
  <Mk>_used     match in title or keywords, OR >= 2 matches in the abstract.
                A single passing mention ("MRI-confirmed", "histopathologically
                verified") does not make a paper a user of that data type.
  multimodal_used = at least two different data types "used". This is the main
                measure of combined data: it does not depend on the word "multimodal",
                which in oncology usually means multimodal THERAPY.
Tasks (K1-K6) use the same "used" rule; <K>_mention keeps the any-mention flag.
Model families, cross-cutting topics and tumor classes are mention-level.

Evaluation flags (X2 external validation, X3/X3a/X3b prospective and reader study)
count only sentences that report what was done. A sentence that matches the
future-work pattern FUTURE ("warrants further prospective validation", "should be
externally validated", "will be explored") is ignored for these flags.
review_title = the title says review, meta-analysis or survey; these are dropped from
the research set (lit_data.py).
radiogenomic = paper that predicts a molecular marker from images; used for a
sensitivity analysis in which imaging + bulk omics papers of this kind are not counted
as combining data types (the omics may be only the label).

Duplicates: records are unique by Scopus EID; a second pass drops repeated DOIs,
keeping the earliest year.
Run: python src/literature/03_tag_records.py
"""
import os, sys, glob, gzip, json
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
import blocks as b

REC = str(config.inp("lit/records"))
OUT = str(config.out_dir("lit"))

ARCH = {"R1_classical": b.R1_CLASSICAL, "R2_cnn": b.R2_CNN,
        "R3_transformer": b.R3_TRANSFORMER, "R4_representation": b.R4_REPRESENTATION,
        "R5_generative": b.R5_GENERATIVE, "R6_llm_foundation": b.R6_LLM_FOUNDATION,
        "R6a_llm": b.R6_LLM, "R6b_foundation": b.R6_FOUNDATION,
        "R7_agentic": b.R7_AGENTIC, "R9_federated": b.R9_FEDERATED, "R8_KG": b.R8_KG}


def load():
    rows = []
    for p in sorted(glob.glob(os.path.join(REC, "T_A_*.jsonl.gz"))):
        year = int(os.path.basename(p)[4:8])
        for line in gzip.open(p, "rt"):
            r = json.loads(line)
            r["year"] = year
            rows.append(r)
    df = pd.DataFrame(rows)
    n0 = len(df)
    df = df.drop_duplicates("eid")
    has_doi = df["doi"].notna()
    df = pd.concat([df[has_doi].sort_values("year").drop_duplicates("doi"), df[~has_doi]])
    print(f"records loaded {n0:,}; unique by EID then DOI: {len(df):,}")
    return df.reset_index(drop=True)


UNICODE_FIX = {"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
               "\u2014": "-", "\u2212": "-", "\u00a0": " ", "\u202f": " ",
               "\u2009": " ", "\u200b": ""}


def norm(s):
    """Unicode dashes and spaces -> ASCII, so 'deep\u2010learning' matches 'deep-learning'."""
    s = s.fillna("")
    for k, v in UNICODE_FIX.items():
        s = s.str.replace(k, v, regex=False)
    return s


import re
FUTURE = re.compile(
    r"\b(future|further|warrant\w*|need\w*|should|will|would|could|may be|pending|"
    r"remain\w* to be|require\w*|planned|ongoing|next step|before clinical)\b", re.I)
EVAL_FLAGS = ["X2_external_validation", "X3_prospective", "X3a_prospective_patients",
              "X3b_reader_study"]
REVIEW_TITLE = re.compile(r"\b(review|meta-?analys\w*|survey)\b", re.I)
RADIOGENOMIC = re.compile(
    r"radiogenomic\w*|radiogenomics|(predict\w*|non-?invasive\w*|classif\w*)[^.;]{0,80}"
    r"\b(IDH\d?|1p/?19q|MGMT|TERT|EGFR|ATRX|H3\s?K27M?|molecular (status|subtype\w*|marker\w*)|"
    r"mutation status|genotype|methylation status|codeletion)\b", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+")


def done_not_future(text_series, rx):
    """1 if some sentence matches rx and does not read as future work."""
    out = []
    for t in text_series:
        hit = 0
        for sent in SENT_SPLIT.split(t):
            if rx.search(sent) and not FUTURE.search(sent):
                hit = 1
                break
        out.append(hit)
    return pd.Series(out, index=text_series.index)


def main():
    df = load()
    title = norm(df["title"])
    abst = norm(df["abstract"])
    kw = norm(df["keywords"]).str.replace("|", " ; ", regex=False)
    tk = title + " ; " + kw
    full = title + " ; " + abst + " ; " + kw

    out = df[["eid", "doi", "year", "doctype", "venue", "source_id",
              "aggregation_type", "cited_by"]].copy()
    out["has_abstract"] = (abst.str.len() > 0).astype(int)

    # Bulk omics must not re-count single-cell or spatial papers: "single-cell
    # transcriptomics" and "spatial transcriptomics" both contain "transcriptom".
    # Blank single-cell and spatial phrases before testing M3.
    rx_sc_sp = b.compile_block(b.M["M4_single_cell"] + b.M["M5_spatial"])
    blank = lambda s: s.str.replace(rx_sc_sp, " ", regex=True)

    used_cols = []
    for mk, terms in b.M.items():
        rx = b.compile_block(terms)
        f_full, f_tk, f_abs = (full, tk, abst) if mk != "M3_bulk_omics" else \
            (blank(full), blank(tk), blank(abst))
        out[f"{mk}_mention"] = f_full.str.contains(rx).astype(int)
        in_tk = f_tk.str.contains(rx)
        n_abs = f_abs.str.count(rx)
        out[f"{mk}_used"] = (in_tk | (n_abs >= 2)).astype(int)
        used_cols.append(f"{mk}_used")
    out["n_modalities_used"] = out[used_cols].sum(axis=1)
    out["multimodal_used"] = (out["n_modalities_used"] >= 2).astype(int)

    # Tasks use the same strength rule as data types (2026-09-28): named in the
    # title or keywords, or at least twice in the abstract. One passing phrase in an
    # abstract ("important for prognosis") no longer makes a paper a prognosis paper.
    for name, terms in b.K.items():
        rx = b.compile_block(terms)
        out[f"{name}_mention"] = full.str.contains(rx).astype(int)
        out[name] = (tk.str.contains(rx) | (abst.str.count(rx) >= 2)).astype(int)
    for name, terms in {**ARCH, **b.X}.items():
        rx = b.compile_block(terms)
        out[f"{name}_anymention" if name in EVAL_FLAGS else name] = full.str.contains(rx).astype(int)
        if name in EVAL_FLAGS:
            out[name] = done_not_future(full, rx)
    out["review_title"] = title.str.contains(REVIEW_TITLE).astype(int)
    out["radiogenomic"] = full.str.contains(RADIOGENOMIC).astype(int)
    for ent, terms in b.E.items():
        out[f"E_{ent}"] = full.str.contains(b.compile_block(terms)).astype(int)
    out["pediatric"] = full.str.contains(b.compile_block(b.PEDIATRIC)).astype(int)
    # sanity: every record came from T AND A, so both should (almost) always match
    out["_T_local"] = full.str.contains(b.compile_block(b.T)).astype(int)
    out["_A_local"] = full.str.contains(b.compile_block(b.A)).astype(int)
    # PRIMARY analysis set: T and A both visible in title / abstract / author keywords.
    out["in_primary_set"] = (out["_T_local"] & out["_A_local"]).astype(int)
    # FOCUSED: the tumour term is in the title or author keywords, i.e. brain tumours are
    # the subject, not one benchmark among many in a general medical-imaging paper.
    out["T_focus"] = tk.str.contains(b.compile_block(b.T)).astype(int)

    out.to_csv(os.path.join(OUT, "tagged_records.csv.gz"), index=False)
    flags = [c for c in out.columns if c not in
             ("eid", "doi", "year", "doctype", "venue", "source_id", "aggregation_type", "cited_by")]
    for name, sub in [("tag_summary_by_year.csv", out[out.in_primary_set == 1]),      # PRIMARY
                      ("tag_summary_by_year_allpulled.csv", out)]:
        summ = sub.groupby("year")[flags].sum()
        summ.insert(0, "n_records", sub.groupby("year").size())
        summ.to_csv(os.path.join(OUT, name))
    print(f"written -> {OUT}/tagged_records.csv.gz and tag_summary_by_year.csv")
    print(f"local re-match of T: {out['_T_local'].mean():.1%}   of A: {out['_A_local'].mean():.1%}")
    print(f"primary set (T and A visible): {out['in_primary_set'].sum():,} of {len(out):,} "
          f"({out['in_primary_set'].mean():.1%})")


if __name__ == "__main__":
    main()
