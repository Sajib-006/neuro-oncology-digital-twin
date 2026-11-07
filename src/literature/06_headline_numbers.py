"""Every literature-survey number quoted in the paper, from one script.

Input : lit/tagged_records.csv.gz   (03_tag_records.py), through lit_data.focused_research()
        (research papers only: articles and conference papers, no review in the title)
Output: lit/headline_numbers.csv    name, value, detail
        lit/share_by_year.csv       per-year share naming 2+ data types, Wilson 95% intervals
Trends: logistic regression of a flag on year (2015-2025) with document type as a covariate.
Run: python src/literature/06_headline_numbers.py
"""
import os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
import lit_data as D

OUT = "lit"
MODS = list(D.MOD_LABEL)
rows = []


def put(name, value, detail=""):
    rows.append([name, value, detail])
    print(f"  {name:<46} {value!s:<12} {detail}")


def trend(df, flag, years=(2015, 2025)):
    """Logistic regression of flag on year (per 1 year), with document type (article vs
    conference paper) as a covariate. Complete years only."""
    d = df[df.year.between(*years)].copy()
    d["y"] = d[flag].astype(int)
    d["yr"] = d.year - years[0]
    d["journal"] = (d.doctype == "ar").astype(int)
    try:
        m = smf.logit("y ~ yr + journal", data=d).fit(disp=0)
    except Exception:                      # too few events for the covariate
        return (np.nan,) * 5
    orr = np.exp(m.params["yr"])
    lo, hi = np.exp(m.conf_int().loc["yr"])
    return orr, lo, hi, m.pvalues["yr"], np.exp(m.params["journal"])


def main():
    df = D.focused_research()
    full = pd.read_csv(config.inp(f"{D.L}/tagged_records.csv.gz"))
    base = full[(full.in_primary_set == 1) & (full.T_focus == 1) & (full.doctype.isin(["ar", "cp"]))
                & (full.has_abstract == 1) & (full.year.between(2015, 2026))]
    put("research_papers", len(df), "focused set, 2015-2026, no review in title")
    put("review_titles_removed", int(base.review_title.sum()))
    put("research_papers_2015_2025", int((df.year <= 2025).sum()))

    # ---------------------------------------------------------------- data types
    for mk in MODS:
        put(f"{mk}_used", int(df[f"{mk}_used"].sum()))
    k = int(df.multimodal_used.sum())
    put("multimodal_used", k, f"{100 * k / len(df):.1f}%")
    by = df.groupby("year").agg(n=("eid", "size"), k=("multimodal_used", "sum"))
    p, lo, hi = D.wilson(by.k, by.n)
    by["share"], by["lo"], by["hi"] = 100 * p, 100 * lo, 100 * hi
    full_years = by.loc[2015:2025]
    put("multimodal_share_min_2015_2025", round(full_years.share.min(), 1),
        f"year {int(full_years.share.idxmin())}")
    put("multimodal_share_max_2015_2025", round(full_years.share.max(), 1),
        f"year {int(full_years.share.idxmax())}")
    put("multimodal_share_2026_partial", round(by.loc[2026, "share"], 1))
    orr, l, h, pv, jr = trend(df, "multimodal_used")
    put("multimodal_trend_OR_per_year", round(orr, 3), f"95% CI {l:.3f}-{h:.3f}; p={pv:.2f}; journal vs conference OR {jr:.2f}")

    # sensitivity: do not count radiogenomic imaging + bulk-omics papers as combining
    rg = (df.radiogenomic == 1) & (df.M1_neuroimaging_used == 1) & (df.M3_bulk_omics_used == 1) \
         & (df.n_modalities_used == 2)
    k2 = int((df.multimodal_used.astype(bool) & ~rg).sum())
    put("multimodal_excl_radiogenomic", k2, f"{100 * k2 / len(df):.1f}% (radiogenomic image+omics pairs removed: {int(rg.sum())})")

    fus = df[df.X1_fusion_vocab == 1]
    put("fusion_vocab_papers", len(fus))
    put("fusion_vocab_with_two_types", int(fus.multimodal_used.sum()))
    pairs = {}
    for i, a in enumerate(MODS):
        for b_ in MODS[i + 1:]:
            pairs[(a, b_)] = int(((df[f"{a}_used"] == 1) & (df[f"{b_}_used"] == 1)).sum())
    for (a, b_), n in sorted(pairs.items(), key=lambda x: -x[1])[:4]:
        put(f"pair_{a}__{b_}", n)
    img = df[df.M1_neuroimaging_used == 1]
    put("imaging_papers", len(img))
    put("imaging_therapy_task", int(img.K5_therapeutics.sum()))
    for mk in ["M3_bulk_omics", "M4_single_cell", "M5_spatial", "M2_pathology"]:
        sub = df[df[f"{mk}_used"] == 1]
        put(f"{mk}_therapy_task_share", round(100 * sub.K5_therapeutics.mean(), 1), f"n={len(sub)}")

    # ---------------------------------------------------------------- evaluation
    for flag in ["X2_external_validation", "X3a_prospective_patients", "X3b_reader_study",
                 "X3_prospective", "X5_reporting", "X7_uncertainty", "X8_fairness_shift"]:
        for yr in (2025, 2026):
            sub = df[df.year == yr]
            put(f"{flag}_{yr}", round(100 * sub[flag].mean(), 1), f"{int(sub[flag].sum())}/{len(sub)}")
        put(f"{flag}_all", int(df[flag].sum()))
        if f"{flag}_anymention" in df:
            put(f"{flag}_anymention_all", int(df[f"{flag}_anymention"].sum()),
                "before removing future-work sentences")
        orr, l, h, pv, _ = trend(df, flag)
        put(f"{flag}_trend_OR_per_year", round(orr, 3), f"95% CI {l:.3f}-{h:.3f}; p={pv:.3g}")

    # ---------------------------------------------------------------- methods and tasks
    y25 = df[df.year == 2025]
    for c in D.ARCH_LABEL:
        if c in df:
            put(f"{c}_2025", round(100 * y25[c].mean(), 1))
    for c in D.TASK_LABEL:
        put(f"{c}_2025", round(100 * y25[c].mean(), 1))
        put(f"{c}_all_years", round(100 * df[c].mean(), 1))
    for c in ["R6a_llm", "R6b_foundation", "R6_llm_foundation", "R7_agentic", "R8_KG", "X9_digital_twin",
              "X4_regulatory"]:
        put(f"{c}_count", int(df[c].sum()))
    for c in ["R6a_llm", "R6b_foundation"]:
        for yr in (2023, 2024, 2025):
            put(f"{c}_{yr}", int(df[df.year == yr][c].sum()))
    put("pediatric_share_all", round(100 * df.pediatric.mean(), 1), f"{int(df.pediatric.sum())}/{len(df)}")

    pd.DataFrame(rows, columns=["name", "value", "detail"]).to_csv(
        config.out(f"{OUT}/headline_numbers.csv"), index=False)
    by.round(2).to_csv(config.out(f"{OUT}/share_by_year.csv"))
    print(f"\nwritten -> {OUT}/headline_numbers.csv")


if __name__ == "__main__":
    main()
