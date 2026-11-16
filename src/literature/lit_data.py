"""Shared data access for the literature stages and figures (Figs 3-5).

Input : lit/tagged_records.csv.gz, lit/counts_by_year_<form>.csv
Output: none (helper module: the main paper set, labels and Wilson intervals)
"""
import numpy as np
import pandas as pd

import config

L = "lit"
PARTIAL_YEAR = 2026          # records pulled 2026-09-24: about 73% of the year
YEARS = list(range(2015, 2027))

MOD_LABEL = {
    "M1_neuroimaging": "Imaging", "M2_pathology": "Pathology",
    "M3_bulk_omics": "Bulk omics", "M4_single_cell": "Single-cell",
    "M5_spatial": "Spatial omics", "M6_clinical_text": "Clinical text",
}
ARCH_LABEL = {
    "R1_classical": "Classical ML", "R2_cnn": "CNNs", "R3_transformer": "Transformers",
    "R4_representation": "Representation learning",
    "R5_generative": "Generative", "R6a_llm": "Language models",
    "R6b_foundation": "Foundation models",
    "R7_agentic": "Agentic AI", "R9_federated": "Federated / privacy",
    "R8_KG": "Knowledge graphs*",
}
TASK_LABEL = {
    "K1_segmentation": "Segmentation", "K2_diagnosis_classification": "Diagnosis / grading",
    "K3_prognosis": "Prognosis / survival", "K4_response_progression": "Treatment response",
    "K5_therapeutics": "Therapy planning",
    "K6_workflow_trust": "Decision support",
}


def focused_research():
    """Main paper set (13,423 papers): T and A visible, tumor term in title or keywords,
    articles and conference papers with an abstract, 2015-2026, and no review,
    meta-analysis or survey in the title (some reviews are filed as articles)."""
    t = pd.read_csv(config.inp(f"{L}/tagged_records.csv.gz"))
    return t[(t.in_primary_set == 1) & (t.T_focus == 1) & (t.doctype.isin(["ar", "cp"]))
             & (t.has_abstract == 1) & (t.year.between(min(YEARS), max(YEARS)))
             & (t.review_title == 0)].copy()


def counts(form="focused"):
    return pd.read_csv(config.inp(f"{L}/counts_by_year_{form}.csv")).pivot_table(
        index="year", columns="query_id", values="count")


def wilson(k, n, z=1.96):
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = np.where(n > 0, k / np.maximum(n, 1), np.nan)
    den = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p, centre - half, centre + half
