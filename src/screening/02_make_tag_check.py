"""Draw the hand-check sample of keyword tags (precision and recall) for two human coders.

Input : lit/tagged_records.csv.gz (through lit_data.focused_research()) and
        lit/records/T_A_<year>.jsonl.gz (titles, abstracts and keywords shown to coders)
Output (audit/tag_check/):
        screening_tags_<coder>.xlsx   blind coder sheets, same rows (contain Scopus abstracts:
                                      do not share)
        tags_sample_KEY.csv           tags + strata for scoring (never shown to coders)
        tag_check_strata.csv          pool and sample size per stratum

Frame: the main research set (13,423 papers, 2015-2026). The strata below are a
PARTITION of that frame (each paper is in exactly one stratum, assigned in the order
listed), so the scorer can weight each sampled paper by N_stratum / n_stratum and
estimate precision AND recall for the whole set, not only for the sample.

  MM      multimodal_used = 1 (2 or more data types tagged)
  EV      external validation tagged (X2), not MM
  EVNEAR  not tagged X2, not MM, but uses a plain synonym the rule misses
          ("external dataset", "validation cohort", ...): the main recall worry
  ONE_M2..ONE_M6  exactly one data type tagged, and it is not imaging
  IMG     imaging is the only data type tagged (most of the set)
  NONE    no data type tagged

Labels must come from people only. No model or rule fills any answer cell.
Seed 20261106; rerunning gives the same rows.
Run: python src/screening/02_make_tag_check.py
"""
import os, sys, glob, gzip, json, re
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
config.use("literature")
import lit_data as D
import blocks as b

SEED = 20261106
OUT = str(config.OUT_DIR / "audit" / "tag_check")
CODERS = ["Erin", "Rafi"]

# stratum -> target sample size (total 100)
# (first draw had NONE = 5; raised to 10 after seeing that NONE holds 2,988 papers,
#  22% of the frame, before any coding was done)
TARGET = {"MM": 30, "EV": 15, "EVNEAR": 8,
          "ONE_M2": 4, "ONE_M3": 4, "ONE_M4": 3, "ONE_M5": 3, "ONE_M6": 3,
          "IMG": 20, "NONE": 10}

# plain synonyms for external validation that X2 does not contain
EV_SYNONYMS = ["external dataset*", "external data set*", "external test*",
               "externally tested", "external testing", "validation cohort*",
               "independent dataset*", "independent data set*", "independent test cohort*",
               "external data"]

MODS = list(D.MOD_LABEL)          # M1..M6 keys

# ---------------------------------------------------------------- questions (blind)
# (column id, short header shown in the sheet, key column it is scored against)
QUESTIONS = [
    ("Q1_research", "Q1. Original research on brain tumours?", "in_set"),
    ("Q2_ai", "Q2. Uses an AI or machine learning method?", "in_set"),
    ("Q3a_imaging", "Q3a. Data: medical imaging (MRI, CT, PET)?", "M1_neuroimaging_used"),
    ("Q3b_pathology", "Q3b. Data: pathology slides or tissue staining?", "M2_pathology_used"),
    ("Q3c_bulk_omics", "Q3c. Data: bulk omics (DNA, RNA, methylation, protein profiles)?", "M3_bulk_omics_used"),
    ("Q3d_single_cell", "Q3d. Data: single-cell omics?", "M4_single_cell_used"),
    ("Q3e_spatial", "Q3e. Data: spatial omics?", "M5_spatial_used"),
    ("Q3f_clinical_text", "Q3f. Data: clinical text or records (EHR, notes, reports, registry)?", "M6_clinical_text_used"),
    ("Q4_combine", "Q4. Combines 2 or more of these data types in one analysis?", "multimodal_used"),
    ("Q5_external", "Q5. Tests the model on data from another site or cohort (external validation)?", "X2_external_validation"),
]
NOTES_AFTER = {"Q1_research": "Q1 notes", "Q2_ai": "Q2 notes", "Q3f_clinical_text": "Q3 notes (data types)",
               "Q4_combine": "Q4 notes", "Q5_external": "Q5 notes"}

INSTRUCTIONS = [
    ("How to fill this file", "title"),
    ("Thank you! There are 100 papers. Each one takes about 1 minute, so about 1 to 2 hours in total.", ""),
    ("", ""),
    ("Rules", "head"),
    ("1. Please work on your own. The other coder fills the same file separately. Do not talk about the answers until both files are sent back.", ""),
    ("2. Read the title, abstract and keywords. Answer about what THIS study itself did. Open the link only if you are really stuck.", ""),
    ("3. Pick Yes, No or Unsure from the dropdown in every answer cell. Use Unsure only when the abstract really does not let you decide, and write a short note.", ""),
    ("4. Things mentioned only as background, motivation or future work do not count. For example 'external validation is needed' is No, and 'histologically confirmed glioma' does not make it a pathology study.", ""),
    ("5. Data types (Q3a to Q3f): answer Yes if the study analyses that kind of data, as model input or as data it measures and studies. A single lab marker used as the label (for example IDH or MGMT status) is NOT bulk omics. Several MRI sequences (T1, T2, FLAIR) are one data type (imaging). Simple clinical variables such as age, sex or KPS are not clinical text or records on their own.", ""),
    ("6. Q4 (combine): Yes if two or more of the six data types in Q3 are used together in one analysis or model, for example MRI plus whole-slide images as inputs, or MRI features linked to gene expression profiles. Predicting one marker (IDH, MGMT) from MRI alone is No. Imaging plus age or sex is No.", ""),
    ("7. Q5 (external validation): Yes if the model is tested on data from a different hospital, site, cohort or public dataset that was not used to train it. A random split, cross-validation, or a held-out part of the same dataset is No.", ""),
    ("8. Please do not change, add or sort the other columns or rows. Save the file with the same name and send it back.", ""),
    ("", ""),
    ("What each question means", "head"),
    ("Q1. Is this an original research study about brain tumours (primary brain or CNS tumours)? No for a review, a commentary, a study mainly about another disease, or a study only about brain metastases. A case report counts as research.", ""),
    ("Q2. Does the study build, train or test an AI or machine learning method (for example deep learning, a CNN, random forest, SVM, a language model)? Plain statistics only (t-test, Cox model, logistic regression without any machine learning) is No.", ""),
    ("Q3a to Q3f. Which data types does the study analyse? Answer each one Yes or No. Imaging = MRI, CT, PET and similar scans (radiomics counts). Pathology = H&E or other stained tissue slides, whole-slide images, immunohistochemistry. Bulk omics = genome, exome, RNA-seq, gene expression, DNA methylation, copy number, proteomics or other molecular profiles of bulk tissue. Single-cell = single-cell or single-nucleus sequencing. Spatial omics = spatial transcriptomics or proteomics (for example Visium, Xenium, imaging mass cytometry). Clinical text or records = electronic health records, clinical notes, radiology or pathology reports, or a cancer registry such as SEER.", ""),
    ("Q4. Does the study combine two or more of the data types in Q3 in one analysis or model? (see rule 6)", ""),
    ("Q5. Does the study test its model on data from another site or cohort (external validation)? (see rule 7)", ""),
    ("", ""),
    ("Worked example 1 (made up, not from the sheet)", "head"),
    ("Abstract says: 'We trained a convolutional neural network on preoperative MRI (T1, T2, FLAIR) from 310 glioma patients at Hospital A to predict IDH mutation status. The model was then tested on 120 patients from Hospital B, with an AUC of 0.88.'", ""),
    ("Answers: Q1 Yes. Q2 Yes (CNN). Q3a imaging Yes. Q3b to Q3f all No (IDH status is a single marker used as the label, so bulk omics is No). Q4 No (only one data type). Q5 Yes (tested on a second hospital).", ""),
    ("", ""),
    ("Worked example 2 (made up, not from the sheet)", "head"),
    ("Abstract says: 'Using TCGA glioblastoma cases, we built a random forest that combines RNA-seq gene expression with features from H&E whole-slide images to predict overall survival. Five-fold cross-validation gave a C-index of 0.71. External validation in larger cohorts is needed.'", ""),
    ("Answers: Q1 Yes. Q2 Yes (random forest). Q3a imaging No. Q3b pathology Yes. Q3c bulk omics Yes. Q3d to Q3f No. Q4 Yes (gene expression plus slides in one model). Q5 No (cross-validation within one dataset; external validation is only future work).", ""),
]


def norm(s):
    s = s.fillna("")
    for k, v in {"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
                 "\u2212": "-", "\u00a0": " ", "\u202f": " ", "\u2009": " ", "\u200b": ""}.items():
        s = s.str.replace(k, v, regex=False)
    return s


def load_records():
    recs = {}
    for p in glob.glob(str(config.inp("lit/records") / "T_A_*.jsonl.gz")):
        for line in gzip.open(p, "rt"):
            r = json.loads(line)
            recs.setdefault(r["eid"], r)
    return recs


def assign_strata(df, text):
    ev_near = text.str.contains(b.compile_block(EV_SYNONYMS))
    s = pd.Series("", index=df.index)
    one = df.n_modalities_used == 1
    rules = [("MM", df.multimodal_used == 1),
             ("EV", df.X2_external_validation == 1),
             ("EVNEAR", ev_near)]
    rules += [(f"ONE_{mk[:2]}", one & (df[f"{mk}_used"] == 1)) for mk in MODS if mk != "M1_neuroimaging"]
    rules += [("IMG", one & (df.M1_neuroimaging_used == 1)),
              ("NONE", df.n_modalities_used == 0)]
    for name, mask in rules:
        s[(s == "") & mask] = name
    assert (s != "").all(), "every paper must fall in one stratum"
    return s


def row_height(abstract, width_chars=105):
    lines = sum(max(1, int(np.ceil(len(p) / width_chars))) for p in str(abstract).split("\n"))
    return float(min(409, max(60, 15 * lines + 10)))


def write_sheet(path, sample):
    wb = Workbook()
    ins = wb.active
    ins.title = "Instructions"
    ins.column_dimensions["A"].width = 150
    for i, (txt, kind) in enumerate(INSTRUCTIONS, start=1):
        c = ins.cell(row=i, column=1, value=txt)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if kind == "title":
            c.font = Font(bold=True, size=14)
        elif kind == "head":
            c.font = Font(bold=True, size=12)
        if len(txt) > 140:
            ins.row_dimensions[i].height = 15 * int(np.ceil(len(txt) / 140)) + 4

    ws = wb.create_sheet("Papers")
    cols = [("paper_id", 10), ("year", 7), ("title", 38), ("author keywords", 24),
            ("abstract", 110), ("link (open only if stuck)", 22)]
    answer_cols, note_cols = [], []
    for qid, head, _ in QUESTIONS:
        cols.append((head, 14))
        answer_cols.append(len(cols))
        if qid in NOTES_AFTER:
            cols.append((NOTES_AFTER[qid], 22))
            note_cols.append(len(cols))
    head_fill = PatternFill("solid", fgColor="DDEBF7")
    ans_fill = PatternFill("solid", fgColor="FFF2CC")
    thin = Side(style="thin", color="BFBFBF")
    for j, (h, w) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=j, value=h)
        c.font = Font(bold=True)
        c.fill = head_fill
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[1].height = 90

    for i, r in enumerate(sample.itertuples(), start=2):
        vals = [r.paper_id, int(r.year), r.title, r.keywords, r.abstract, r.link]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for j in answer_cols + note_cols:
            c = ws.cell(row=i, column=j)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            if j in answer_cols:
                c.fill = ans_fill
        ws.row_dimensions[i].height = row_height(r.abstract)
    last = len(sample) + 1
    dv = DataValidation(type="list", formula1='"Yes,No,Unsure"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Please pick from the list",
                        error="Please choose Yes, No or Unsure.")
    ws.add_data_validation(dv)
    for j in answer_cols:
        L = get_column_letter(j)
        dv.add(f"{L}2:{L}{last}")
    ws.freeze_panes = "B2"
    wb.active = 0
    wb.save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    df = D.focused_research().reset_index(drop=True)
    recs = load_records()
    df["title"] = [recs.get(e, {}).get("title") or "" for e in df.eid]
    df["abstract"] = [recs.get(e, {}).get("abstract") or "" for e in df.eid]
    df["keywords"] = [re.sub(r"\s*\|\s*", "; ", (recs.get(e, {}).get("keywords") or "").strip())
                      for e in df.eid]
    text = norm(df.title) + " ; " + norm(df.abstract) + " ; " + norm(df.keywords)
    df["stratum"] = assign_strata(df, text)
    df["in_set"] = 1     # every paper in the frame is tagged AI and research by construction

    rng = np.random.default_rng(SEED)
    picks, strata = [], []
    for name, n_target in TARGET.items():
        pool = df[df.stratum == name]
        n = min(n_target, len(pool))
        idx = rng.choice(pool.index.to_numpy(), size=n, replace=False)
        picks.append(df.loc[np.sort(idx)])
        strata.append({"stratum": name, "pool_N": len(pool), "sampled_n": n,
                       "weight": len(pool) / n if n else np.nan})
    sample = pd.concat(picks)
    sample = sample.iloc[rng.permutation(len(sample))].reset_index(drop=True)   # mix strata
    sample["paper_id"] = [f"TC{i:03d}" for i in range(1, len(sample) + 1)]
    sample["link"] = ["https://doi.org/" + d if isinstance(d, str) and d else
                      "https://www.scopus.com/record/display.uri?eid=" + e
                      for d, e in zip(sample.doi, sample.eid)]
    st = pd.DataFrame(strata)
    sample = sample.merge(st[["stratum", "pool_N", "sampled_n", "weight"]], on="stratum", how="left")
    assert len(df) == st.pool_N.sum()
    assert sample.paper_id.is_unique and sample.eid.is_unique

    # key: tags only, for scoring later. Never shown to coders.
    key_cols = (["paper_id", "eid", "doi", "year", "doctype", "stratum", "pool_N", "sampled_n",
                 "weight", "in_set"] + [f"{mk}_used" for mk in MODS] + [f"{mk}_mention" for mk in MODS]
                + ["n_modalities_used", "multimodal_used", "radiogenomic", "X1_fusion_vocab",
                   "X2_external_validation", "X2_external_validation_anymention"]
                + list(D.ARCH_LABEL) + list(D.TASK_LABEL))
    key = sample[key_cols]
    key.to_csv(os.path.join(OUT, "tags_sample_KEY.csv"), index=False)
    st.loc[len(st)] = {"stratum": "TOTAL", "pool_N": st.pool_N.sum(), "sampled_n": st.sampled_n.sum(),
                       "weight": np.nan}
    st.to_csv(os.path.join(OUT, "tag_check_strata.csv"), index=False)

    for c in CODERS:
        write_sheet(os.path.join(OUT, f"screening_tags_{c}.xlsx"), sample)

    print(f"frame {len(df):,} papers; seed {SEED}")
    print(st.to_string(index=False))
    print("tagged positives in sample:")
    for qid, _, kc in QUESTIONS:
        print(f"  {qid:<18} {kc:<26} {int(key[kc].sum()):>3}")
    print("empty abstracts in sample:", int((sample.abstract.str.len() == 0).sum()))
    print("longest abstract (chars):", int(sample.abstract.str.len().max()))
    print("written ->", OUT)


if __name__ == "__main__":
    main()
