"""Term blocks for the literature survey (Supplementary Table S1). Imported by every
literature stage, by the trial stage and by the supplement table emitter.

Every block is ONE list of terms. From it we generate both
  * the Scopus TITLE-ABS-KEY string  (scopus_or)
  * the local regex used to tag pulled records (compile_block)
so the query that was run and the tagging applied to its records cannot drift apart.

Term syntax
  "phrase words"   exact phrase (Scopus loose phrase; regex allows space/hyphen/slash
                   between words and an optional plural s/es at the end)
  word*            truncation (verified 2026-09-23: Scopus honours * inside quotes)

Design choices, each from a check of the terms on real records:
  - A: no bare "neural network" (15% of brain-tumour hits have no AI term: biological
       networks); no "diffusion model" (reaction-diffusion growth models, 27 pre-2015
       hits vs 0 for "denoising diffusion"); no bare "AI", "CNN", "transformer".
  - A is a SUPERSET of every architecture block, so architecture series nest inside
       the AI set.
  - K2: no bare "classification" (WHO classification). X1: no bare "multimodal"
       (multimodal therapy, 26% of hits). X5: no bare "CLAIM". X7: no bare
       "calibration". X2: no bare "multicenter". X4: no bare "FDA". R3: no
       "attention mechanism". R7: no "tool use", no "ReAct" (matches "react").
  - T: primary CNS tumours as reviewed in the paper; brain metastases are a separate
       entity series and are NOT in T.
"""
import re

# ------------------------------------------------------------------ tumour scope
T = [
    "brain tumor*", "brain tumour*", "brain cancer*", "brain neoplasm*",
    "CNS tumor*", "CNS tumour*", "central nervous system tumor*",
    "central nervous system tumour*", "central nervous system neoplasm*",
    "intracranial tumor*", "intracranial tumour*", "intracranial neoplasm*",
    "neuro-oncology", "neurooncology",
    "glioma*", "glioblastoma*", "gliosarcoma*", "astrocytoma*", "oligodendroglioma*",
    "ependymoma*", "medulloblastoma*", "meningioma*", "craniopharyngioma*",
    "pineoblastoma*", "ganglioglioma*", "atypical teratoid rhabdoid",
    "diffuse midline glioma*", "diffuse intrinsic pontine glioma*", "DIPG",
    "brainstem glioma*", "primary CNS lymphoma*",
]

# ------------------------------------------------------------------ architectures
R1_CLASSICAL = [
    "random forest*", "support vector machine*", "SVM", "XGBoost", "LightGBM",
    "CatBoost", "AdaBoost", "gradient boosting", "k-nearest neighbor*",
    "k-nearest neighbour*", "naive Bayes",
]
R2_CNN = [
    "convolutional neural network*", "fully convolutional network*", "U-Net", "UNet",
    "nnU-Net", "nnUNet", "3D U-Net", "V-Net", "ResNet*", "DenseNet*", "EfficientNet*",
    "VGG16", "VGG19", "DeepMedic", "SegResNet",
]
R3_TRANSFORMER = [
    "vision transformer*", "transformer-based", "transformer model*",
    "transformer architecture*", "transformer network*", "Swin transformer*",
    "Swin-UNETR", "UNETR", "ViT", "self-attention", "cross-attention",
    "multi-head attention", "attention-based network*",
]
R4_REPRESENTATION = [
    "autoencoder*", "auto-encoder*", "graph neural network*",
    "graph convolutional network*", "contrastive learning", "representation learning",
    "self-supervised learning", "self-supervised",
]
R5_GENERATIVE = [
    "generative adversarial network*", "denoising diffusion", "latent diffusion",
    "diffusion probabilistic model*", "score-based generative", "stable diffusion",
    "normalizing flow*", "synthetic data generation", "image synthesis",
]
# R6 is split in two for reporting (2026-09-28): language models vs other
# foundation models (pathology or imaging). The union is unchanged, so every Scopus
# query string built from A is unchanged. "BERT" is matched case-sensitively locally
# (see CASE_SENSITIVE) so that the surname "Bert" is not counted.
R6_LLM = [
    "large language model*", "ChatGPT", "GPT-4", "GPT-4o", "GPT-3.5",
    "vision-language model*", "vision language model*",
    "BERT", "BioBERT", "ClinicalBERT", "pre-trained language model*",
    "pretrained language model*", "retrieval-augmented generation",
]
R6_FOUNDATION = ["foundation model*"]
R6_LLM_FOUNDATION = [
    "large language model*", "ChatGPT", "GPT-4", "GPT-4o", "GPT-3.5",
    "foundation model*", "vision-language model*", "vision language model*",
    "BERT", "BioBERT", "ClinicalBERT", "pre-trained language model*",
    "pretrained language model*", "retrieval-augmented generation",
]
assert set(R6_LLM) | set(R6_FOUNDATION) == set(R6_LLM_FOUNDATION)
CASE_SENSITIVE = {"BERT"}

R7_AGENTIC = [
    "agentic", "AI agent*", "autonomous agent*", "multi-agent system*",
    "LLM agent*", "tool calling", "function calling",
]
R9_FEDERATED = [
    "federated learning", "swarm learning", "privacy-preserving",
    "differential privacy",
]
# Knowledge graphs are a separate series, not part of A (not an architecture).
R8_KG = [
    "knowledge graph*", "biomedical ontolog*", "ontology-based", "semantic web",
    "linked data",
]

A_CORE = [
    "artificial intelligence", "machine learning", "deep learning",
    "artificial neural network*", "deep neural network*", "recurrent neural network*",
    "neural network model*", "multilayer perceptron*", "reinforcement learning",
    "natural language processing",
]
A = (A_CORE + R1_CLASSICAL + R2_CNN + R3_TRANSFORMER + R4_REPRESENTATION
     + R5_GENERATIVE + R6_LLM_FOUNDATION + R7_AGENTIC + R9_FEDERATED)

# ------------------------------------------------------------------ modalities
M = {
    "M1_neuroimaging": [
        "neuroimaging", "magnetic resonance imaging", "MRI", "MR imaging",
        # added after the zero-modality diagnosis (2026-09-24): papers that say
        # "MR images", "FLAIR" or name the BraTS MRI benchmark instead of "MRI".
        # Generic "medical image" is NOT added - it does not name a modality.
        "MR image*", "MR scan*", "magnetic resonance image*", "T1-weighted",
        "T2-weighted", "FLAIR", "BraTS",
        "computed tomography", "CT scan*", "CT imaging", "positron emission tomography",
        "PET imaging", "PET/CT", "amino acid PET", "FET PET", "radiomic*",
        "radiogenomic*", "MR spectroscopy", "magnetic resonance spectroscopy",
        "diffusion tensor imaging", "diffusion-weighted imaging",
        "diffusion weighted imaging", "perfusion imaging", "perfusion-weighted",
        "dynamic susceptibility contrast", "arterial spin labeling",
        "arterial spin labelling", "susceptibility-weighted imaging", "tractography",
        "functional MRI", "fMRI",
    ],
    "M2_pathology": [
        # No "histolog*", "neuropatholog*", "cytolog*": imaging papers say
        # "histologically confirmed" in passing, which would tag them as pathology.
        "histopatholog*", "whole-slide image*", "whole slide image*",
        "whole-slide imaging", "digital pathology", "computational pathology",
        "pathology image*", "pathological image*", "immunohistochemi*",
        "hematoxylin and eosin", "haematoxylin and eosin", "H&E",
        "tissue microarray*", "frozen section*",
    ],
    "M3_bulk_omics": [
        "multi-omic*", "multiomic*", "genomic*", "transcriptom*", "proteom*",
        "epigenom*", "metabolom*", "methylom*", "RNA sequencing", "RNA-seq",
        "whole-exome sequencing", "whole-genome sequencing",
        "next-generation sequencing", "DNA methylation", "methylation profil*",
        "gene expression", "copy number",
    ],
    "M4_single_cell": [
        "single-cell RNA*", "single-cell transcriptom*", "single-cell sequencing",
        "single-nucleus RNA*", "scRNA-seq", "snRNA-seq", "single-cell multiome",
        "single-cell ATAC",
    ],
    "M5_spatial": [
        "spatial transcriptom*", "spatial proteom*", "spatial omics",
        "spatial multi-omic*", "spatially resolved transcriptom*",
        "spatially resolved proteom*", "Visium", "Xenium", "CosMx", "MERFISH",
        "seqFISH", "GeoMx", "Stereo-seq", "Slide-seq*", "imaging mass cytometry",
        "co-detection by indexing", "PhenoCycler", "multiplexed ion beam imaging",
    ],
    "M6_clinical_text": [
        "electronic health record*", "electronic medical record*", "EHR",
        "clinical note*", "radiology report*", "pathology report*", "clinical text",
        "free-text", "tumor board*", "tumour board*", "cancer registr*",
        "SEER database", "National Cancer Database", "discharge summar*",
        "clinical documentation",
    ],
}

# ------------------------------------------------------------------ tasks
K = {
    "K1_segmentation": [
        "segmentation", "auto-contouring", "autosegmentation", "auto-segmentation",
        "tumor delineation", "tumour delineation", "lesion detection",
        "tumor detection", "tumour detection",
    ],
    "K2_diagnosis_classification": [
        "tumor classification", "tumour classification", "image classification",
        "automated classification", "classifier*", "classification accuracy",
        "tumor grading", "tumour grading", "WHO grade", "grade prediction",
        "molecular subtype*", "molecular subtyping", "IDH", "IDH1", "MGMT",
        "1p/19q", "1p19q", "methylation class*", "differential diagnosis",
        "diagnostic accuracy",
    ],
    "K3_prognosis": [
        "prognos*", "survival prediction", "overall survival",
        "progression-free survival", "risk stratification", "time-to-event",
        "survival analysis",
    ],
    "K4_response_progression": [
        "treatment response", "therapy response", "pseudoprogression",
        "pseudo-progression", "radiation necrosis", "RANO", "recurrence prediction",
        "tumor recurrence", "tumour recurrence", "tumor progression",
        "tumour progression",
    ],
    "K5_therapeutics": [
        "drug discovery", "drug repurposing", "drug repositioning",
        "virtual screening", "drug-target interaction*", "drug response",
        "drug sensitivity", "temozolomide response", "temozolomide resistance",
        "radiosensitiv*", "chemosensitiv*", "immunotherapy response",
        "blood-brain barrier permeab*", "blood-brain barrier penetra*",
        # radiotherapy planning (added 2026-09-28: therapy had drug terms only)
        "radiotherapy planning", "radiation therapy planning", "radiotherapy treatment planning",
        # not bare "treatment planning": 1,204 imaging abstracts use it as motivation
        # ("to aid treatment planning"), checked 2026-09-28
        "dose prediction", "dose distribution*", "dose painting",
        "clinical target volume*", "gross tumor volume", "gross tumour volume",
        "target volume delineation", "organ* at risk", "synthetic CT", "pseudo-CT",
        "MR-only radiotherapy", "MRI-only radiotherapy", "adaptive radiotherapy",
        "proton therapy planning", "radiosurgery planning",
    ],
    "K6_workflow_trust": [
        "clinical decision support", "decision support system*", "CDSS",
        "clinical workflow*", "human-in-the-loop", "explainable artificial intelligence",
        "explainable AI", "XAI", "interpretab*", "explainab*", "trustworthy",
        "clinical deployment", "clinical implementation", "clinical integration",
    ],
}

# ------------------------------------------------------------------ cross-cutting
X = {
    "X1_fusion_vocab": [
        "multimodal fusion", "multi-modal fusion", "modality fusion", "data fusion",
        "cross-modal", "multimodal deep learning", "multimodal machine learning",
        "multimodal model*", "multimodal learning", "multimodal integration",
        "multi-modal integration", "integrative multi-omic*",
        "multimodal artificial intelligence",
    ],
    "X2_external_validation": [
        "external validation", "externally validated", "external cohort*",
        "external test set*", "external test cohort*", "independent validation",
        "independent test set*", "independent cohort*", "held-out cohort*",
        "multi-site validation", "multicenter validation", "multi-center validation",
        "multicentre validation", "multi-institutional validation",
    ],
    # X3 split (2026-09-28): a reader study on stored images is not a
    # prospective evaluation in patients. X3 keeps its old union for the Scopus side;
    # the local tags X3a and X3b report the two parts, and 03_tag_records.py ignores
    # sentences that describe future work ("warrants prospective validation").
    "X3_prospective": [
        "prospective validation", "prospective cohort*", "prospective study",
        "prospectively enrolled", "prospectively collected", "prospectively validated",
        "reader study", "randomized controlled trial*", "randomised controlled trial*",
    ],
    "X3a_prospective_patients": [
        "prospective validation", "prospective cohort*", "prospective study",
        "prospectively enrolled", "prospectively collected", "prospectively validated",
        "randomized controlled trial*", "randomised controlled trial*",
    ],
    "X3b_reader_study": ["reader study", "reader studies", "observer study"],
    "X4_regulatory": [
        "FDA clearance", "FDA-cleared", "FDA cleared", "CE mark*", "CE-marked",
        "regulatory clearance", "regulatory approval", "software as a medical device",
        "SaMD",
    ],
    "X5_reporting": [
        "CLAIM checklist", "Checklist for Artificial Intelligence in Medical Imaging",
        "TRIPOD statement", "TRIPOD-AI", "TRIPOD+AI", "TRIPOD guideline*",
        "DECIDE-AI", "STARD-AI", "STARD 2015", "CONSORT-AI", "SPIRIT-AI",
        "PROBAST", "PROBAST-AI", "MINIMAR", "radiomics quality score",
    ],
    "X7_uncertainty": [
        "uncertainty quantification", "uncertainty estimation", "model calibration",
        "calibration curve*", "calibration plot*", "Brier score",
        "expected calibration error", "conformal prediction", "Bayesian deep learning",
        "Monte Carlo dropout", "out-of-distribution", "selective prediction",
    ],
    "X8_fairness_shift": [
        "algorithmic bias", "fairness", "health equity", "health disparit*",
        "domain shift", "distribution shift", "dataset shift",
        "domain generalization", "domain generalisation", "domain adaptation",
    ],
    "X9_digital_twin": [
        "digital twin*", "virtual patient*", "in silico trial*", "virtual twin*",
    ],
}

# ------------------------------------------------------------------ entities
E = {
    "GBM": ["glioblastoma*", "gliosarcoma*"],
    "Astrocytoma": ["astrocytoma*"],
    "Oligodendroglioma": ["oligodendroglioma*"],
    "DMG_H3K27": ["diffuse midline glioma*", "diffuse intrinsic pontine glioma*",
                  "DIPG", "brainstem glioma*"],
    "Medulloblastoma": ["medulloblastoma*"],
    "Ependymoma": ["ependymoma*"],
    # not "AT/RT": Scopus strips the slash, leaving "at rt", which matches "at RT" (radiotherapy)
    "ATRT": ["atypical teratoid rhabdoid", "atypical teratoid/rhabdoid", "ATRT"],
    "PilocyticAstrocytoma": ["pilocytic astrocytoma*"],
    "Meningioma": ["meningioma*"],
    "Craniopharyngioma": ["craniopharyngioma*"],
    "BrainMetastasis": ["brain metasta*", "cerebral metasta*"],   # separate, not in T
}
PEDIATRIC = ["pediatric", "paediatric", "children", "childhood", "infant*",
             "adolescent*"]

NORMALIZER_ONCOLOGY = ["cancer*", "oncolog*", "tumor*", "tumour*", "neoplas*",
                       "carcinoma*", "malignan*"]

FILTERS = ("AND ( DOCTYPE(ar) OR DOCTYPE(re) OR DOCTYPE(cp) ) "
           "AND LANGUAGE(english)")
# Research papers only (articles and conference papers, no reviews). Used for the
# Fig. 2a counts from 2026-09-28 so that panel a has the same document types as b and c.
FILTERS_RESEARCH = "AND ( DOCTYPE(ar) OR DOCTYPE(cp) ) AND LANGUAGE(english)"


# ================================================================== builders
def _scopus_term(t):
    return t if (" " not in t and "-" not in t and "/" not in t and "&" not in t
                 and "+" not in t and t.isascii()) and not t.endswith("*") else f'"{t}"'


def scopus_or(terms):
    """OR-block for TITLE-ABS-KEY. Single plain words unquoted, everything else quoted."""
    return "( " + " OR ".join(_scopus_term(t) for t in terms) + " )"


def _regex_term(t):
    trunc = t.endswith("*")
    core = t[:-1] if trunc else t
    parts = re.split(r"[\s\-/]+", core)
    pat = r"[\s\-/]*".join(re.escape(p) for p in parts if p)
    if trunc:
        pat += r"\w*"
    else:
        pat += r"(?:s|es)?"          # Scopus loose phrase matches plurals
    return r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])"


def compile_block(terms):
    """Case-insensitive, except terms in CASE_SENSITIVE (e.g. BERT vs the name Bert)."""
    ci = [t for t in terms if t not in CASE_SENSITIVE]
    cs = [t for t in terms if t in CASE_SENSITIVE]
    pats = ["(?i:" + "|".join(_regex_term(t) for t in ci) + ")"] if ci else []
    pats += [_regex_term(t) for t in cs]
    return re.compile("|".join(pats))


def tak(*blocks):
    """TITLE-ABS-KEY( b1 AND b2 ... ). NOT the primary search - see visible()."""
    return "TITLE-ABS-KEY( " + " AND ".join(scopus_or(b) for b in blocks) + " )"


def visible(*blocks):
    """PRIMARY search form: each block must match in the title, abstract or AUTHOR
    keywords - the fields a reader can check, and the fields the local tagging reads.

    TITLE-ABS-KEY also searches Scopus's indexed keywords, which the API does not
    return and which indexers can assign from full text. In the first pull
    (2026-09-24) about 9% of TITLE-ABS-KEY records did not contain T or A in any
    visible field, and a sample of them was mostly off-topic (e.g. colorectal
    microsatellite instability, patient ratings of radiologists). The TITLE-ABS-KEY
    counts are kept as an upper bound.
    """
    return " AND ".join(
        "( TITLE-ABS" + scopus_or(b) + " OR AUTHKEY" + scopus_or(b) + " )" for b in blocks)


def focused(*blocks):
    """PRIMARY for all figures (decided 2026-09-24): like visible(), but the tumour block
    must be in the TITLE or AUTHOR keywords - brain tumours are the subject of the paper,
    not one benchmark among many. Only the T block is restricted; if the first block is
    not T (e.g. the oncology normaliser) this is identical to visible()."""
    if blocks and blocks[0] is T:
        head = "( TITLE" + scopus_or(T) + " OR AUTHKEY" + scopus_or(T) + " )"
        return head if len(blocks) == 1 else head + " AND " + visible(*blocks[1:])
    return visible(*blocks)


def with_year(query, year, filters=None):
    return f"{query} AND PUBYEAR = {year} {filters or FILTERS}"


ALL_BLOCKS = {"T": T, "A": A, "R8_KG": R8_KG,
              "R1_classical": R1_CLASSICAL, "R2_cnn": R2_CNN,
              "R3_transformer": R3_TRANSFORMER, "R4_representation": R4_REPRESENTATION,
              "R5_generative": R5_GENERATIVE, "R6_llm_foundation": R6_LLM_FOUNDATION,
              "R6a_llm": R6_LLM, "R6b_foundation": R6_FOUNDATION,
              "R7_agentic": R7_AGENTIC, "R9_federated": R9_FEDERATED,
              **M, **K, **X, **{f"E_{k}": v for k, v in E.items()},
              "PEDIATRIC": PEDIATRIC}
