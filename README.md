# brain-tumor-ai-review

Code for the review paper **"Artificial intelligence toward digital-twin precision
neuro-oncology"** (Sajib Acharjee Dip et al.).

The paper backs its review with four small analyses. This repository holds the code for
all of them, and every number, figure and generated table in the paper comes from it.

1. **Knowledge bases.** How many genes Open Targets, CTD and DisGeNET link to each of ten
   brain tumor classes, and whether tumor similarity from these resources just follows
   coverage (Figure 1a to 1e).
2. **Literature survey.** 13,423 AI research papers on brain tumors from Scopus, tagged by
   data type, model family, clinical task and evaluation (Figures 1f, 1g, 2, 3 and 4a).
3. **Trials and devices.** AI trials in ClinicalTrials.gov and AI devices on the FDA list,
   screened by people (Figure 4b, 4c and Supplementary Tables S7 and S8).
4. **Figure 5**, a drawn roadmap for a brain tumor digital twin (no data).

## Pipeline

```
 Scopus API ──> literature/01,02,05 ──> records, counts ──> literature/03 tags ──┐
                                                                                 ├─> literature/04,06-09 ──> numbers, Table S1, S4
 Open Targets, CTD, DisGeNET ──> knowledge_bases/01-06 ──> gene x tumor matrices ┤
                                  knowledge_bases/07-10 ──> similarity and null tests
 ClinicalTrials.gov ──> trials/01 ──> trials/02 ──┐                              │
 FDA device list + PDFs ──> devices/01 ──> 02 ────┼─> screening/01 (2 reviewers  │
                                                  │   + a third) ──> Tables S7, S8
                                                  └──────────────────────────────┴─> figures/fig1..fig5
```

Each folder in `src/` is one stage. Scripts are numbered in run order inside each folder.
Every script says at the top what it reads and what it writes.

```
src/
  config.py          paths (DATA_DIR, OUT_DIR, FIG_DIR), data versions and dates
  knowledge_bases/   01-05 download and filter, 06 matrices, 07 similarity,
                     08 enrichment, 09 pre-specified null test, 10 robust checks
  literature/        blocks.py (all search terms), lit_data.py (the main paper set),
                     01-02 Scopus counts and records, 03 tagging, 04 checks, 05 class counts,
                     06 headline numbers, 07 supplementary tables, 08-09 sanity checks
  trials/            01 download, 02 rule-based measures
  devices/           01 FDA list and decision summaries, 02 rule-based measures
  screening/         01 merge of the human screening, 02-03 tag hand-check sample and scoring
  figures/           style.py, panel helpers, one script per paper figure, icons
scripts/             make_data_release.py, compare_outputs.py
data/README.md       the derived data files and their columns
```

## Setup

You need Python 3.11 and the pinned packages:

```
conda env create -f environment.yml
conda activate brain-tumor-ai-review
```

or `pip install -r requirements.txt` in a Python 3.11 virtual environment.

Other tools:
- **Google Chrome or Chromium**, only for Figure 5 (it prints the SVG to PDF and PNG).
  Set `CHROME=/path/to/chrome` if it is not found.
- **pdftotext** (poppler; the paper used 22.02.0), only for the devices stage.
- **Arial.** The figures use Arial, which cannot be shared here. Copy `Arial.ttf`,
  `Arial Bold.ttf` and `Arial Italic.ttf` into `src/figures/fonts/` (or set `FONT_DIR`).
  Without Arial, Figures 1 to 4 are drawn with a similar font and a warning; the numbers
  stay the same. Figure 5 needs Arial.

## Where data go

All paths are set by three environment variables (see `src/config.py`):

| Variable | Meaning | Default |
|---|---|---|
| `DATA_DIR` | input data: the released derived files and any stored downloads | `./data` |
| `OUT_DIR` | where scripts write | same as `DATA_DIR` |
| `FIG_DIR` | where figures are written | `$OUT_DIR/figures` |

A script reads a file from `OUT_DIR` when it is there and from `DATA_DIR` otherwise. So you
can keep the released data untouched, write to a new folder, and later stages still find
what earlier stages just made. Set `OFFLINE=1` to stop the devices stage from downloading
missing PDFs.

## How to reproduce

### a) Quick path: from the released derived data (no keys, no network)

Download the derived data (see `data/README.md`) into `./data`, then:

```
export DATA_DIR=$PWD/data OUT_DIR=$PWD/out
make quick
python scripts/compare_outputs.py        # compare your outputs with the released files
```

This reruns the similarity and null tests from the gene matrices, all literature numbers
and supplementary tables from the tags, the trial measures from the stored registry
records, the human screening merge, and all five figures. It takes about one hour; the
knowledge-base null tests take most of it. Figures go to `out/figures/`.

### b) Full path: from the raw sources

```
export SCOPUS_API_KEY=...          # your own key from the Elsevier developer portal
make full
```

| Stage | Needs | Rough time |
|---|---|---|
| `kb-download` | network; about 6 GB (Open Targets 2.5 GB, CTD 3.2 GB) | 30 min |
| `kb-raw` | the downloads | 30 min |
| `enrichment` | network (g:Profiler) | 10 min |
| `kb` | the matrices | 40 min |
| `literature-api` | network and `SCOPUS_API_KEY` (about 2,500 requests) | 2 to 3 hours |
| `literature-tags`, `literature` | the stored records | 10 min |
| `trials-api`, `trials` | network (ClinicalTrials.gov, no key) | 5 min |
| `devices` | network for 1,313 decision summary PDFs (1 per second), pdftotext | 1 hour |
| `screening`, `figures` | the outputs above | 5 min |

Scopus, ClinicalTrials.gov, the FDA list and CTD change over time, and CTD serves only its
current release. A full rerun today will therefore not give exactly the paper's numbers.
The stored downloads and the released derived files do.

## Paper items and where they come from

| Paper item | Script | Output file (under `OUT_DIR`) |
|---|---|---|
| Fig. 1a, 1b; genes per class; 12-fold and 510-fold | `knowledge_bases/06_build_matrices.py` | `support_counts.csv` |
| Fig. 1c, 1d; Jaccard and cosine rho ranges | `knowledge_bases/07_similarity.py` | `similarity_long.csv` (rho printed by `fig1_knowledge.py`) |
| Pre-specified null test (rho -0.42 to -0.63, failed) | `knowledge_bases/09_null_similarity.py` | `null_similarity/size_check.csv` |
| Fig. 1e; Curveball and size-matched Jaccard checks | `knowledge_bases/10_similarity_robust.py` | `similarity_robust/size_check_robust.csv`, `pairs_*.csv` |
| CTD rows (574,115; 329 curated); versions | `knowledge_bases/02`, `04`, `05`, `06` | `provenance_*.csv` |
| Fig. 1f, 1g (AI share per class; rho 0.67) | `literature/05_entity_counts.py` | `lit/entity_counts.csv` (rho printed by `fig1_knowledge.py`) |
| Fig. 2a (AI share per data type) | `literature/01_scopus_counts.py` | `lit/counts_by_year_focused_research.csv` |
| Fig. 2b, 2c, Fig. 3, Fig. 4a | `literature/03_tag_records.py` | `lit/tagged_records.csv.gz` |
| 13,423 papers; 1.8% (235) name 2+ data types; trend OR 0.99; 1.4% without radiogenomic papers; 322 and 30 fusion papers; 51 of 9,642; external validation 2.5% and prospective 0.3% (2025); model and task shares | `literature/06_headline_numbers.py` | `lit/headline_numbers.csv` |
| 0.7% to 2.7% each year | `literature/06_headline_numbers.py` | `lit/share_by_year.csv` |
| Lenient share (4.4%, Fig. 3b dashed line) | `literature/08_multimodal_sanity.py`, `figures/fig3_integration.py` | printed |
| Automatic checks (Supplementary Note 1) | `literature/04_checks.py` | `lit/checks.csv` |
| 2026 partial-year check | `literature/09_partial_year_check.py` | printed |
| Supplementary Table S1 (search blocks) | `literature/07_supplement_tables.py` | `supplement/S_search_blocks.tex` |
| Supplementary Table S4 (class identifiers) | `literature/07_supplement_tables.py` | `supplement/S_entities.tex` |
| 6,008 trials, 5,299 on primary tumors, 118 candidates | `trials/01_pull_trials.py`, `trials/02_trial_metrics.py` | `trials/provenance.csv`, `trials/trial_summary.csv` |
| 1,614 devices, 1,313 searched, 1,305 texts, 35 candidates | `devices/01_fda_devices.py` | `devices/provenance.csv` |
| 77 trials, 12 devices, kappa 0.81 and 0.20, 15 and 19 settled, roles, 28 due and 0 posted, start-year shares | `screening/01_final_screening.py` | `audit/screening_summary.csv` |
| Fig. 4b, 4c | `screening/01_final_screening.py` | `trials/trial_share_by_start_year_screened.csv`, `audit/screening_final_devices.csv` |
| Supplementary Tables S7 (trials) and S8 (devices) | `screening/01_final_screening.py` | `audit/screening_final_trials.csv`, `audit/screening_final_devices.csv` (rows with `final` = 1) |
| Figures 1 to 5 | `figures/fig1_knowledge.py` ... `fig5_digital_twin.py` | `fig1_knowledge.pdf` ... `fig5_digital_twin.pdf` in `FIG_DIR` |

## Data sources

| Source | Version used | Access | License or terms |
|---|---|---|---|
| Scopus Search API | records 24 Sep 2026, counts 28 Sep 2026 | API key | Elsevier terms; abstracts cannot be shared |
| Open Targets Platform | release 26.09 | open download | CC0 1.0 |
| CTD gene-disease file | report of 28 Aug 2026 (downloaded 24 Sep 2026) | open download | free for research; see the CTD legal notice |
| DisGeNET | v7.0 (2020), curated file, PheKnowLator archive copy | open download | CC BY-NC-SA 4.0 |
| g:Profiler | e114_eg62_p19 (KEGG, Reactome) | open API | free web service |
| ClinicalTrials.gov | API 2.0.5, data of 24 Sep 2026 | open API | public registry |
| FDA AI-enabled device list | page updated 4 Sep 2026 (downloaded 25 Sep 2026) | open download | US government, public |
| Icons | Bioicons: Servier Medical Art, DBCLS TogoTV, Marcel Tisch, Xi Chen | in this repository | CC BY 3.0, CC BY 4.0, CC0 (see `CREDITS.txt`) |

## What cannot be shared

Scopus terms do not allow the titles and abstracts to be shared. The released data hold
the Scopus record IDs (EIDs), DOIs, years, document types and every derived tag, plus the
exact query strings (`lit/queries_*.csv`). With your own key, `literature/02_scopus_records.py`
downloads the records again. The raw Open Targets, CTD and DisGeNET files and the FDA PDFs
are not copied; the scripts download them from the providers, and the release lists their
hashes and URLs.

## Human screening

Two authors screened the 118 candidate trials and 35 candidate devices on their own, with
short written rules. A third author settled every row with a difference or a missing
rating and wrote down a reason for each. The three spreadsheets are in the released data
(`audit/human_review/`), with the instruction sheet given to the screeners ("How to fill")
and the one used to settle rows ("How to settle"). `screening/01_final_screening.py` reads
them, computes Cohen's kappa on the rows both rated, and writes the final lists. One trial
that both screeners included studies pituitary adenoma, which the rules exclude; the
script removes it after screening and says so.

`screening/02_make_tag_check.py` draws a stratified sample of 100 papers (seed 20261106) for
a hand check of the keyword tags, and `screening/03_score_tag_check.py` scores the returned
sheets (precision, recall, kappa). The coder sheets hold Scopus abstracts, so they are not
shared; the sample key and strata are.

## How to cite

Please cite the paper:

> Acharjee Dip S, et al. Artificial intelligence toward digital-twin precision
> neuro-oncology. 2026. (Full reference to be added.)

and the data deposit (DOI to be added).

## License

The code is under the MIT License (`LICENSE`). Icons keep their own licenses, and data from
each provider keep that provider's terms.
