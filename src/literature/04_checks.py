"""Automatic checks on the literature data (Supplementary Note 1, "Automatic checks").

Input : lit/counts_by_year_visible.csv, lit/counts_by_year_focused.csv  (01_scopus_counts.py)
        lit/records_manifest.csv                                        (02_scopus_records.py)
        lit/tag_summary_by_year.csv, lit/tagged_records.csv.gz          (03_tag_records.py)
Output: lit/checks.csv   one row per check: id, what, verdict, detail

  C1 nesting        every <Mk>_AI <= <Mk>_GEN, MASTER <= N1_T, MASTER <= N2, per year
  C2 completeness   every year 2000-2026 has a record file with written == expected
  C3 reconciliation records with T and A visible per year vs the visible MASTER_T_A count
  C4 local vs API   local <Mk>_mention count / API <Mk>_AI count, per data type (pooled
                    2015-2026). Expected close to 1; WARN outside 0.85 to 1.10.
  C5 face validity  a method must be about absent before it existed. WARN if the mean
                    records per year before it exceeds 2.
  C6 info           share of downloaded records with T / A visible (the index-term gap;
                    records without them are left out of the main set).
Run: python src/literature/04_checks.py
"""
import os, sys, csv
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
import blocks as b

L = "lit"
YEARS = range(2000, 2027)
FACE = [("R5_generative", 2000, 2013, "GANs 2014, diffusion 2020"),
        ("R3_transformer", 2000, 2016, "transformer 2017"),
        ("R6_llm_foundation", 2000, 2017, "BERT 2018"),
        ("R7_agentic", 2000, 2021, "LLM agents ~2022"),
        ("R9_federated", 2000, 2016, "federated learning 2017")]


def main():
    rows = []
    add = lambda cid, what, verdict, detail: rows.append([cid, what, verdict, detail])
    cnt = pd.read_csv(config.inp(f"{L}/counts_by_year_visible.csv"))        # primary form
    piv = cnt.pivot_table(index="year", columns="query_id", values="count")

    # C1
    bad = []
    for mk in b.M:
        v = piv[piv[f"{mk}_AI"] > piv[f"{mk}_GEN"]]
        bad += [f"{mk}:{y}" for y in v.index]
    bad += [f"MASTER>N1:{y}" for y in piv[piv.MASTER_T_A > piv.N1_T].index]
    bad += [f"MASTER>N2:{y}" for y in piv[piv.MASTER_T_A > piv.N2_onc_A].index]
    add("C1", "nesting of all count queries (visible)", "PASS" if not bad else "FAIL",
        "none violated" if not bad else "; ".join(bad))
    fp = config.inp(f"{L}/counts_by_year_focused.csv")
    if os.path.exists(fp):                      # the form the figures use
        pf = pd.read_csv(fp).pivot_table(index="year", columns="query_id", values="count")
        badf = [f"{mk}:{y}" for mk in b.M for y in pf[pf[f"{mk}_AI"] > pf[f"{mk}_GEN"]].index]
        badf += [f"MASTER>N1:{y}" for y in pf[pf.MASTER_T_A > pf.N1_T].index]
        badf += [f"FOCUSED>VISIBLE:{y}" for y in pf.index
                 if y in piv.index and pf.loc[y, "MASTER_T_A"] > piv.loc[y, "MASTER_T_A"]]
        add("C1b", "nesting of focused counts, and focused <= visible", "PASS" if not badf else "FAIL",
            "none violated" if not badf else "; ".join(badf))

    # C2 + C3
    man = pd.read_csv(config.inp(f"{L}/records_manifest.csv"))
    missing = sorted(set(YEARS) - set(man.year))
    short = man[man.expected != man.written]
    add("C2", "record files complete", "PASS" if not missing and short.empty else "FAIL",
        f"missing years {missing}; short years {list(short.year)}")
    # records were pulled with TITLE-ABS-KEY (a superset); the primary set is those with
    # T and A visible locally. Compare its size with the visible-form MASTER count.
    tagsum = pd.read_csv(config.inp(f"{L}/tag_summary_by_year.csv"), index_col=0)
    m = tagsum[["n_records"]].join(piv["MASTER_T_A"])
    m = m[m.index >= 2015]
    rel = ((m.n_records - m.MASTER_T_A).abs() / m.MASTER_T_A.clip(lower=1))
    add("C3", "primary-set records vs visible MASTER count (2015+)",
        "PASS" if rel.max() <= 0.05 else "WARN",
        f"median gap {rel.median():.1%}, max {rel.max():.1%} (local regex vs Scopus tokeniser)")

    # C4
    tag = pd.read_csv(config.inp(f"{L}/tag_summary_by_year.csv"), index_col=0)
    for mk in b.M:
        yrs = [y for y in range(2015, 2027) if y in tag.index and y in piv.index]
        loc, api = tag.loc[yrs, f"{mk}_mention"].sum(), piv.loc[yrs, f"{mk}_AI"].sum()
        r = loc / api if api else float("nan")
        add("C4", f"local vs API, {mk}", "PASS" if 0.85 <= r <= 1.10 else "WARN",
            f"local {int(loc):,} / API {int(api):,} = {r:.2f}")

    # C5
    for flag, y0, y1, why in FACE:
        yrs = [y for y in range(y0, y1 + 1) if y in tag.index]
        mean = tag.loc[yrs, flag].mean() if yrs else 0
        add("C5", f"face validity {flag} {y0}-{y1} ({why})",
            "PASS" if mean <= 2 else "WARN", f"mean {mean:.1f} records/yr")

    # C6
    t = pd.read_csv(config.inp(f"{L}/tagged_records.csv.gz"),
                    usecols=["_T_local", "_A_local", "has_abstract"])
    # INFO, not a test: records were pulled with TITLE-ABS-KEY, a superset that also
    # matches hidden indexed keywords. This is the size of that gap; the primary set
    # excludes those records.
    for c in ["_T_local", "_A_local"]:
        v = t[c].mean()
        add("C6", f"pulled records with {c[1]} visible (index-term gap)", "INFO", f"{v:.1%}")

    with open(config.out(f"{L}/checks.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["check", "what", "verdict", "detail"]); w.writerows(rows)
    for r in rows:
        print(f"  {r[0]}  {r[2]:<5} {r[1]:<52} {r[3]}")


if __name__ == "__main__":
    main()
