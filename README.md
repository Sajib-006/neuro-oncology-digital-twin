# Artificial Intelligence toward Precision Neuro-Oncology

This repository contains the analysis code for the review *Artificial intelligence toward
precision neuro-oncology* (Acharjee Dip et al., 2026). All quantitative results,
figures and generated supplementary tables in the paper are produced by the scripts here.

## Overview

The review is supported by four analyses:

1. **Knowledge-base coverage.** Gene associations for ten primary brain tumor classes in
   Open Targets, CTD and DisGeNET, and a test of whether tumor-tumor similarity reflects
   database coverage (Fig. 2a-e).
2. **Literature survey.** 13,423 research articles on AI for brain tumors retrieved from
   Scopus and annotated with rule-based tags for data type, model family, clinical task and
   evaluation design (Figs. 2f-g, 3, 4 and 5a).
3. **Clinical translation.** AI-related clinical trials from ClinicalTrials.gov and AI-enabled
   medical devices from the FDA list, screened by two independent reviewers with
   adjudication by a third (Fig. 5b-c; Supplementary Tables S7 and S8).
4. **Figures without data.** The overview in Fig. 1 and the digital-twin roadmap in Fig. 6.

```
Scopus API ----------------> literature/01-02, 05 --> literature/03 (tags) --> literature/04, 06-09
Open Targets, CTD, DisGeNET -> knowledge_bases/01-06 (matrices) ------------> knowledge_bases/07-10
ClinicalTrials.gov ---------> trials/01-02 ---------+
FDA device list ------------> devices/01-02 --------+--> screening/01 (human screening)
                                                              |
                         all derived outputs ----------------> figures/fig1-fig5
```

## Repository structure

```
src/
  config.py          paths, data versions and access dates
  knowledge_bases/   download, gene-by-tumor matrices, similarity, enrichment, null models
  literature/        search blocks, Scopus retrieval, tagging, summary statistics, tables
  trials/            ClinicalTrials.gov retrieval and rule-based trial measures
  devices/           FDA device list, decision summaries and rule-based device measures
  screening/         merging of human screening decisions; tag validation sample and scoring
  figures/           plotting style, one script per main figure, icons
scripts/
  make_data_release.py   assembles the derived data archive with checksums
  compare_outputs.py     compares newly generated outputs with the archived ones
data/README.md       description of every derived data file and its columns
Makefile             entry points for each stage
```

Scripts in each folder are numbered in execution order. The header of each script lists its
inputs and outputs.

## System requirements

- Linux or macOS. The results in the paper were generated on Ubuntu 22.04 with Python 3.11.16.
- Python 3.11 with the packages pinned in `environment.yml` and `requirements.txt`.
- Google Chrome or Chromium (Fig. 6 only), used to render the SVG to PDF and PNG.
- The cairo graphics library (Fig. 1 only), used by CairoSVG to rasterize the icons. The
  slide is saved as PPTX and exported to PDF with PowerPoint or LibreOffice.
  Set `CHROME=/path/to/chrome` if it is not on the default path.
- `pdftotext` from poppler (version 22.02.0 in the paper; device stage only).
- `curl` and `sha256sum` (download scripts).
- Arial font files (`Arial.ttf`, `Arial Bold.ttf`, `Arial Italic.ttf`) in `src/figures/fonts/`,
  or a folder given by `FONT_DIR`. If Arial is missing, Figs. 2-5 fall back to a metric-similar
  font.

## Installation

```
git clone https://github.com/Sajib-006/neuro-oncology-digital-twin.git
cd neuro-oncology-digital-twin
conda env create -f environment.yml
conda activate neuro-oncology-digital-twin
```

Alternatively, create a Python 3.11 virtual environment and run
`pip install -r requirements.txt`.

## Data

The derived data used in the paper are attached to release v1.0.0 of this repository
(https://github.com/Sajib-006/neuro-oncology-digital-twin/releases/tag/v1.0.0) as `brain_tumor_ai_data_release_v1.zip`. Extract it so that its `release/` folder becomes
`data/`, or set `DATA_DIR` to that folder. File integrity can be
checked with `sha256sum -c SHA256SUMS`. All files and columns are described in
[`data/README.md`](data/README.md).

Literature records are identified by Scopus EID and DOI. The full records can be retrieved
with a Scopus API key using `src/literature/02_scopus_records.py`.

## Configuration

Paths are set with environment variables (see `src/config.py`):

| Variable | Description | Default |
|---|---|---|
| `DATA_DIR` | input data | `./data` |
| `OUT_DIR` | output directory | `DATA_DIR` |
| `FIG_DIR` | figure output directory | `OUT_DIR/figures` |
| `SCOPUS_API_KEY` | Elsevier API key (literature retrieval only) | none |
| `OFFLINE` | set to `1` to skip downloads in the device stage | unset |

Each script reads an input from `OUT_DIR` if it exists and from `DATA_DIR` otherwise, so the
archived data can stay unchanged while new outputs are written elsewhere.

## Reproducing the results

### From the archived derived data

This route needs no API keys or network access.

```
export DATA_DIR=$PWD/data OUT_DIR=$PWD/out
make quick
python scripts/compare_outputs.py
```

`make quick` reruns the similarity analyses and null models from the gene matrices, all
literature statistics and supplementary tables from the tags, the trial measures from the
stored registry records, the screening merge and all five figures. `compare_outputs.py`
reports any difference from the archived outputs.

### From the primary sources

```
export SCOPUS_API_KEY=<your key>
make full
```

The individual stages can also be run separately:

| Target | Description |
|---|---|
| `make kb-download` | download Open Targets 26.09, CTD and DisGeNET v7.0 |
| `make kb-raw` | build gene lists and gene-by-tumor matrices |
| `make enrichment` | pathway enrichment per tumor class (g:Profiler) |
| `make kb` | similarity, pre-specified null test and robustness checks |
| `make literature-api` | Scopus counts and records (requires `SCOPUS_API_KEY`) |
| `make literature-tags` | rule-based tagging of the Scopus records |
| `make literature` | literature statistics and supplementary tables |
| `make trials-api`, `make trials` | ClinicalTrials.gov retrieval and trial measures |
| `make devices` | FDA device list, decision summaries and device measures |
| `make screening` | merging of the human screening decisions |
| `make figures` | Figs. 1-6 |

Scopus, ClinicalTrials.gov, the FDA device list and CTD are updated over time, so a rerun from
the primary sources at a later date may give slightly different counts. The archived data
reproduce the published values exactly.

## Figures and tables

| Paper item | Script | Output (under `OUT_DIR`) |
|---|---|---|
| Fig. 2a-b; genes per tumor class | `knowledge_bases/06_build_matrices.py` | `support_counts.csv` |
| Fig. 2c-d; similarity correlations | `knowledge_bases/07_similarity.py` | `similarity_long.csv` |
| Pre-specified null test | `knowledge_bases/09_null_similarity.py` | `null_similarity/size_check.csv` |
| Fig. 2e; Curveball and size-matched checks | `knowledge_bases/10_similarity_robust.py` | `similarity_robust/size_check_robust.csv` |
| Fig. 2f-g; AI share per tumor class | `literature/05_entity_counts.py` | `lit/entity_counts.csv` |
| Fig. 3a; AI share per data type | `literature/01_scopus_counts.py` | `lit/counts_by_year_focused_research.csv` |
| Figs. 3b-c, 4 and 5a | `literature/03_tag_records.py` | `lit/tagged_records.csv.gz` |
| Literature statistics in the text | `literature/06_headline_numbers.py` | `lit/headline_numbers.csv`, `lit/share_by_year.csv` |
| Supplementary Note 1 (automatic checks) | `literature/04_checks.py` | `lit/checks.csv` |
| Supplementary Tables S1 and S4 | `literature/07_supplement_tables.py` | `supplement/S_search_blocks.tex`, `supplement/S_entities.tex` |
| Trial counts | `trials/01_pull_trials.py`, `trials/02_trial_metrics.py` | `trials/provenance.csv`, `trials/trial_summary.csv` |
| Device counts | `devices/01_fda_devices.py` | `devices/provenance.csv` |
| Screening results, inter-rater agreement | `screening/01_final_screening.py` | `audit/screening_summary.csv` |
| Fig. 5b-c | `screening/01_final_screening.py` | `trials/trial_share_by_start_year_screened.csv`, `audit/screening_final_devices.csv` |
| Supplementary Tables S7 and S8 | `screening/01_final_screening.py` | `audit/screening_final_trials.csv`, `audit/screening_final_devices.csv` |
| Tag validation (Methods) | `screening/04_settle_tag_check.py`, `screening/03_score_tag_check.py` | `tag_check_scores/tag_check_scores.csv`, `tag_check_kappa.csv` |
| Supplementary Fig. S1 (analysis workflow) | `figures/figS1_workflow.py` | `FIG_DIR/figS1_workflow.pdf` |
| Fig. 1 (overview) | `figures/fig1_overview.py` | `FIG_DIR/fig1_overview.pptx` (editable; exported to PDF) |
| Figs. 2-6 | `figures/fig2_knowledge.py` to `figures/fig6_digital_twin.py` | `FIG_DIR/fig2_knowledge.pdf` to `fig6_digital_twin.pdf` |

## Human screening and tag validation

Candidate trials (n = 118) and devices (n = 35) were screened independently by two reviewers
using written eligibility rules. Disagreements and missing ratings were resolved by a third
reviewer. `screening/01_final_screening.py` computes Cohen's kappa on records rated by both
reviewers and produces the final lists. A stratified random sample of 100 articles
(seed 20261106) was drawn with `screening/02_make_tag_check.py` for manual validation of the
literature tags. Two reviewers coded the sample independently from titles and abstracts, and a
third reviewer settled the answers on which they differed. `screening/04_settle_tag_check.py`
combines the three sheets into final labels, and `screening/03_score_tag_check.py` computes
inter-rater kappa and the precision and recall of each tag against the final labels:

```
python src/screening/04_settle_tag_check.py --coder A=coder_A.xlsx --coder B=coder_B.xlsx \
    --third third_review.xlsx --out final_labels.xlsx
python src/screening/03_score_tag_check.py --coder A=coder_A.xlsx --coder B=coder_B.xlsx \
    --key tags_sample_KEY.csv --resolved final_labels.xlsx --out tag_check_scores
```

## Data sources

| Source | Version | License or terms |
|---|---|---|
| Scopus Search API | records retrieved 24 Sep 2026; counts 28 Sep 2026 | Elsevier API terms |
| Open Targets Platform | release 26.09 | CC0 1.0 |
| Comparative Toxicogenomics Database (CTD) | gene-disease report of 28 Aug 2026 | CTD terms of use |
| DisGeNET | v7.0, curated gene-disease associations | CC BY-NC-SA 4.0 |
| g:Profiler | e114_eg62_p19 (KEGG, Reactome) | public web service |
| ClinicalTrials.gov | API 2.0.5, data of 24 Sep 2026 | public registry |
| FDA AI-enabled medical devices list | update of 4 Sep 2026 | US government public data |
| Icons (Fig. 6) | Bioicons: Servier Medical Art, DBCLS TogoTV, Marcel Tisch | CC BY 3.0, CC BY 4.0, CC0 (`src/figures/icons_svg_raw/CREDITS.txt`) |
| Icons (Fig. 1) | Bioicons: Servier Medical Art, DBCLS TogoTV, Chenxin Li and CC0 authors | CC BY 3.0, CC BY 4.0, CC0 (`src/figures/icons_overview/CREDITS.txt`) |

## Citation

If you use this code, please cite:

```
Acharjee Dip S, et al. Artificial intelligence toward precision neuro-oncology. 2026.
```

The full reference and the data DOI will be added on publication.

## License

The code is released under the MIT License (see `LICENSE`). Icons and third-party data remain
under the licenses of their providers.
