"""Score the human tag check once the two coders return their sheets.

Input : two filled coder sheets (screening_tags_<coder>.xlsx, sheet "Papers"), the key
        (tags_sample_KEY.csv from 02_make_tag_check.py) and, optionally, a resolved sheet
Output: <out>/tag_check_scores.csv          precision, recall and estimated true share per question
        <out>/tag_check_kappa.csv           agreement and Cohen's kappa between the coders
        <out>/tag_check_disagreements.csv   rows where the coders differ
Answers are Yes / No / Unsure; Unsure and blank cells are left out of every score and counted.

For each question it reports
  * agreement and Cohen's kappa between the two coders (rows where both said Yes or No)
  * precision and recall of the keyword tag against each coder, against the rows where
    both coders agree ("agreed"), and against a resolved file if one is given
      - "sample": plain counts in the 100 rows, Wilson 95% interval
      - "weighted": each row weighted by N_stratum / n_labelled_in_stratum, so the
        numbers estimate precision and recall in the whole 13,423-paper set; 95%
        interval from a stratified bootstrap (resample rows within each stratum)
  * the estimated true share in the whole set (weighted share of human Yes)
Q1 and Q2 have no recall: every paper in the set is tagged yes by construction.
Q4_from_types is not a question: it is Yes when the coder ticked 2 or more data types
in Q3, the looser reading of "multimodal" that matches how the tag is built.

Run:
  python src/screening/03_score_tag_check.py \
      --coder A=path/to/screening_tags_A.xlsx --coder B=path/to/screening_tags_B.xlsx \
      --key path/to/tags_sample_KEY.csv [--resolved path/to/resolved.xlsx] --out DIR
"""
import os, argparse
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

# question id -> (header prefix in the sheet, key column)
Q = {
    "Q1_research": ("Q1.", "in_set"),
    "Q2_ai": ("Q2.", "in_set"),
    "Q3a_imaging": ("Q3a.", "M1_neuroimaging_used"),
    "Q3b_pathology": ("Q3b.", "M2_pathology_used"),
    "Q3c_bulk_omics": ("Q3c.", "M3_bulk_omics_used"),
    "Q3d_single_cell": ("Q3d.", "M4_single_cell_used"),
    "Q3e_spatial": ("Q3e.", "M5_spatial_used"),
    "Q3f_clinical_text": ("Q3f.", "M6_clinical_text_used"),
    "Q4_combine": ("Q4.", "multimodal_used"),
    "Q5_external": ("Q5.", "X2_external_validation"),
}
TYPES = ["Q3a_imaging", "Q3b_pathology", "Q3c_bulk_omics", "Q3d_single_cell", "Q3e_spatial",
         "Q3f_clinical_text"]
KEYCOL = {**{q: v[1] for q, v in Q.items()}, "Q4_from_types": "multimodal_used"}
NO_RECALL = {"Q1_research", "Q2_ai"}
B = 2000
SEED = 20261106


def to01(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    return {"yes": 1.0, "y": 1.0, "1": 1.0, "no": 0.0, "n": 0.0, "0": 0.0}.get(s, np.nan)


def read_answers(path):
    df = pd.read_excel(path, sheet_name="Papers", dtype=str)
    out = pd.DataFrame({"paper_id": df["paper_id"].str.strip()})
    raw = {}
    for q, (prefix, _) in Q.items():
        cols = [c for c in df.columns if str(c).startswith(prefix)]
        assert len(cols) == 1, f"{path}: expected one column starting with {prefix!r}, got {cols}"
        raw[q] = df[cols[0]]
        out[q] = df[cols[0]].map(to01)
    # 2 or more data types ticked; unknown if any type is missing and the known Yes count is below 2
    t = out[TYPES]
    yes = (t == 1).sum(axis=1)
    out["Q4_from_types"] = np.where(yes >= 2, 1.0, np.where(t.isna().any(axis=1), np.nan, 0.0))
    unsure = {q: int(raw[q].fillna("").str.strip().str.lower().eq("unsure").sum()) for q in Q}
    blank = {q: int(raw[q].isna().sum()) for q in Q}
    return out.set_index("paper_id"), unsure, blank


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    den = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p, c - h, c + h


def row_weights(strat, pool):
    """N_stratum / n_labelled_in_stratum. Strata with no labelled row drop out, so the
    true share is then a share of the strata that were labelled."""
    return (strat.map(pool) / strat.map(strat.value_counts())).to_numpy(float)


def weighted(tag, y, w):
    """Weighted precision, recall and true share (numpy arrays)."""
    tp = np.sum(w * (tag == 1) * (y == 1))
    pos_tag, pos_y = np.sum(w * (tag == 1)), np.sum(w * (y == 1))
    prec = tp / pos_tag if pos_tag > 0 else np.nan
    rec = tp / pos_y if pos_y > 0 else np.nan
    return prec, rec, pos_y / np.sum(w)


def boot(tag, y, w, strat, rng):
    """Stratified bootstrap: resample rows within each stratum (weights stay fixed)."""
    groups = [np.flatnonzero(strat == s) for s in np.unique(strat)]
    res = np.empty((B, 3))
    for k in range(B):
        ii = np.concatenate([rng.choice(ix, size=len(ix), replace=True) for ix in groups])
        res[k] = weighted(tag[ii], y[ii], w[ii])
    with np.errstate(all="ignore"):
        return np.nanpercentile(res, 2.5, axis=0), np.nanpercentile(res, 97.5, axis=0)


def score(label_name, lab, key, rng):
    rows = []
    for q, kc in KEYCOL.items():
        y = lab[q]
        ok = y.notna()
        tag, yy = key.loc[ok, kc].astype(int), y[ok].astype(int)
        strat = key.loc[ok, "stratum"]
        pool = key.groupby("stratum").pool_N.first()
        tp = int(((tag == 1) & (yy == 1)).sum()); fp = int(((tag == 1) & (yy == 0)).sum())
        fn = int(((tag == 0) & (yy == 1)).sum()); tn = int(((tag == 0) & (yy == 0)).sum())
        p, plo, phi = wilson(tp, tp + fp)
        r, rlo, rhi = wilson(tp, tp + fn)
        if len(yy):
            w = row_weights(strat, pool)
            t_a, y_a, s_a = tag.to_numpy(), yy.to_numpy(), strat.to_numpy()
            wp, wr, ws = weighted(t_a, y_a, w)
            lo, hi = boot(t_a, y_a, w, s_a, rng)
        else:
            wp = wr = ws = np.nan
            lo = hi = np.full(3, np.nan)
        norec = q in NO_RECALL
        rows.append({"labels": label_name, "question": q, "key_tag": kc, "n_labelled": int(ok.sum()),
                     "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                     "precision_sample": p, "precision_sample_lo": plo, "precision_sample_hi": phi,
                     "recall_sample": np.nan if norec else r,
                     "recall_sample_lo": np.nan if norec else rlo,
                     "recall_sample_hi": np.nan if norec else rhi,
                     "precision_weighted": wp, "precision_weighted_lo": lo[0], "precision_weighted_hi": hi[0],
                     "recall_weighted": np.nan if norec else wr,
                     "recall_weighted_lo": np.nan if norec else lo[1],
                     "recall_weighted_hi": np.nan if norec else hi[1],
                     "true_share_weighted": ws, "true_share_lo": lo[2], "true_share_hi": hi[2]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coder", action="append", required=True, help="Name=path.xlsx (give two)")
    ap.add_argument("--key", required=True)
    ap.add_argument("--resolved", help="optional sheet with final answers, same layout")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(SEED)

    key = pd.read_csv(a.key).set_index("paper_id")
    coders = {}
    for spec in a.coder:
        name, path = spec.split("=", 1)
        lab, uns, blk = read_answers(path)
        assert list(lab.index) == list(key.index), f"{name}: paper ids or order differ from the key"
        coders[name] = (lab, uns, blk)
    names = list(coders)
    assert len(names) == 2, "give exactly two coders"
    A, Bl = coders[names[0]][0], coders[names[1]][0]

    # ------------------------------------------------ agreement between coders
    krows, dis = [], []
    for q in list(Q) + ["Q4_from_types"]:
        both = A[q].notna() & Bl[q].notna()
        x, z = A.loc[both, q].astype(int), Bl.loc[both, q].astype(int)
        agree = float((x == z).mean()) if both.any() else np.nan
        kap = cohen_kappa_score(x, z) if both.any() and len(set(x) | set(z)) > 1 else np.nan
        krows.append({"question": q, "n_both_answered": int(both.sum()), "agreement": agree,
                      "kappa": kap,
                      f"unsure_{names[0]}": coders[names[0]][1].get(q, np.nan),
                      f"unsure_{names[1]}": coders[names[1]][1].get(q, np.nan),
                      f"blank_{names[0]}": coders[names[0]][2].get(q, np.nan),
                      f"blank_{names[1]}": coders[names[1]][2].get(q, np.nan)})
        if q in Q:
            for pid in A.index[both & (A[q] != Bl[q])]:
                dis.append({"paper_id": pid, "question": q, names[0]: A.at[pid, q], names[1]: Bl.at[pid, q]})
    kap = pd.DataFrame(krows)
    kap.to_csv(os.path.join(a.out, "tag_check_kappa.csv"), index=False)
    pd.DataFrame(dis).to_csv(os.path.join(a.out, "tag_check_disagreements.csv"), index=False)

    # ------------------------------------------------ precision and recall
    agreed = A.where(A == Bl)            # NaN where they differ or either is missing
    sets = [(names[0], A), (names[1], Bl), ("agreed", agreed)]
    if a.resolved:
        R, _, _ = read_answers(a.resolved)
        assert list(R.index) == list(key.index)
        sets.append(("resolved", R))
    rows = []
    for nm, lab in sets:
        rows += score(nm, lab, key, rng)
    sc = pd.DataFrame(rows)
    sc.to_csv(os.path.join(a.out, "tag_check_scores.csv"), index=False)

    pd.set_option("display.width", 200)
    print("Agreement between coders")
    print(kap[["question", "n_both_answered", "agreement", "kappa"]].round(2).to_string(index=False))
    show = sc[sc.labels == ("resolved" if a.resolved else "agreed")]
    print(f"\nTag scores against {'resolved' if a.resolved else 'agreed'} labels")
    print(show[["question", "n_labelled", "TP", "FP", "FN", "precision_sample", "recall_sample",
                "precision_weighted", "recall_weighted", "true_share_weighted"]].round(2).to_string(index=False))
    print("\nwritten ->", a.out)


if __name__ == "__main__":
    main()
