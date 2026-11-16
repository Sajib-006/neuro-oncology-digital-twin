"""Tumor classes for the knowledge-base coverage analysis (Figure 2, Supplementary Table S4).

Ten WHO CNS5 classes, each pinned to an ontology identifier. Open Targets is queried by
identifier; CTD and DisGeNET, which use other identifiers, are matched by disease name with
the include and exclude patterns below.

Ontology IDs were checked against the Open Targets Platform API on 2026-09-23.

Note on astrocytoma: no source resolves IDH status. Open Targets MONDO_0019781 is
"astrocytoma (excluding glioblastoma)"; CTD and DisGeNET map through MeSH/UMLS
"Astrocytoma", which covers all grades. The entity is therefore labelled
"Astrocytoma (excluding GBM)", not "IDH-mutant", which the data cannot support.
The same applies to glioblastoma: sources do not separate IDH-wildtype, and many
records predate the WHO 2021 split, so the label is "Glioblastoma".
"""

ENTITIES = [
    # key,                   display label,                          ontology id,      family
    ("GBM",                  "Glioblastoma",                         "MONDO_0018177",  "adult diffuse glioma"),
    ("Astrocytoma",          "Astrocytoma (excluding GBM)",          "MONDO_0019781",  "adult diffuse glioma"),
    ("Oligodendroglioma",    "Oligodendroglioma",                    "MONDO_0016695",  "adult diffuse glioma"),
    ("DMG_H3K27",            "Diffuse midline glioma, H3K27-altered","EFO_0020983",    "paediatric high-grade glioma"),
    ("Medulloblastoma",      "Medulloblastoma",                      "MONDO_0007959",  "embryonal"),
    ("Ependymoma",           "Ependymoma",                           "MONDO_0016698",  "ependymal"),
    ("ATRT",                 "Atypical teratoid/rhabdoid tumour",    "MONDO_0020560",  "embryonal"),
    ("PilocyticAstrocytoma", "Pilocytic astrocytoma",                "MONDO_0016691",  "circumscribed glioma"),
    ("Meningioma",           "Meningioma",                           "MONDO_0016642",  "meningeal"),
    ("Craniopharyngioma",    "Craniopharyngioma",                    "MONDO_0018907",  "sellar"),
]

# Name patterns for resources that have no ontology IDs (CTD, DisGeNET dumps).
# `exclude` prevents a parent term from swallowing a child entity.
NAME_PATTERNS = {
    "GBM":                  dict(include=r"glioblastoma", exclude=None),
    "Astrocytoma":          dict(include=r"\bastrocytoma", exclude=r"pilocytic|subependymal|giant cell|anaplastic astrocytoma of"),
    "Oligodendroglioma":    dict(include=r"oligodendroglioma", exclude=None),
    "DMG_H3K27":            dict(include=r"diffuse midline glioma|pontine glioma|dipg|brain ?stem glioma", exclude=None),
    "Medulloblastoma":      dict(include=r"medulloblastoma", exclude=None),
    "Ependymoma":           dict(include=r"ependymoma", exclude=r"subependymoma"),
    "ATRT":                 dict(include=r"atypical teratoid|rhabdoid tumor of the (brain|cns)|\batrt\b", exclude=r"predisposition|syndrome"),
    "PilocyticAstrocytoma": dict(include=r"pilocytic", exclude=None),
    "Meningioma":           dict(include=r"meningioma", exclude=None),
    "Craniopharyngioma":    dict(include=r"craniopharyngioma", exclude=None),
}

KEYS = [e[0] for e in ENTITIES]
LABEL = {e[0]: e[1] for e in ENTITIES}
ONTOLOGY = {e[0]: e[2] for e in ENTITIES}
FAMILY = {e[0]: e[3] for e in ENTITIES}

# Minimum genes for a class to be measurable. Below this the cell is reported as
# no data (grey) and never filled in.
MIN_SUPPORT = 10
