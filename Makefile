# Run the pipeline stage by stage. Paths come from DATA_DIR and OUT_DIR (see src/config.py).
#   make quick      every figure, table and headline number from the archived derived data
#   make full       everything from raw sources (needs network and SCOPUS_API_KEY)
# Each stage can also be run on its own, for example `make literature`.

PYTHON ?= python
SHELL := /bin/bash
S := src

.PHONY: help quick full download kb-download kb-raw kb enrichment \
        literature-api literature-tags literature trials-api trials devices \
        screening tag-check figures fig5 release

help:
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

quick: kb literature trials screening figures  ## all paper outputs from archived derived data

full: download kb-raw enrichment kb literature-api literature-tags literature trials-api trials devices screening figures  ## everything from raw sources

download: kb-download literature-api trials-api  ## all network downloads

# ---------------------------------------------------------------- knowledge bases
kb-download:  ## download Open Targets 26.09, CTD and DisGeNET v7.0 (network, about 6 GB)
	bash $(S)/knowledge_bases/01_download_opentargets.sh 26.09
	bash $(S)/knowledge_bases/03_download_ctd.sh
	bash $(S)/knowledge_bases/05_download_disgenet_v7.sh

kb-raw:  ## build gene lists and matrices from the downloaded files
	$(PYTHON) $(S)/knowledge_bases/02_opentargets_genes.py 26.09
	$(PYTHON) $(S)/knowledge_bases/04_filter_ctd.py
	$(PYTHON) $(S)/knowledge_bases/06_build_matrices.py

enrichment:  ## g:Profiler enrichment per class (network)
	$(PYTHON) -u $(S)/knowledge_bases/08_enrichment.py

kb:  ## similarity, pre-specified null test and robust checks, from the matrices
	$(PYTHON) $(S)/knowledge_bases/07_similarity.py
	$(PYTHON) -u $(S)/knowledge_bases/09_null_similarity.py
	$(PYTHON) -u $(S)/knowledge_bases/10_similarity_robust.py

# ---------------------------------------------------------------- literature
literature-api:  ## Scopus counts, records and class counts (network, needs SCOPUS_API_KEY)
	$(PYTHON) -u $(S)/literature/01_scopus_counts.py --form visible
	$(PYTHON) -u $(S)/literature/01_scopus_counts.py --form tak
	$(PYTHON) -u $(S)/literature/01_scopus_counts.py --form focused
	$(PYTHON) -u $(S)/literature/01_scopus_counts.py --form focused --research
	$(PYTHON) -u $(S)/literature/02_scopus_records.py
	$(PYTHON) -u $(S)/literature/05_entity_counts.py

literature-tags:  ## tag the stored Scopus records (needs the Scopus records)
	$(PYTHON) $(S)/literature/03_tag_records.py

literature:  ## checks, headline numbers, supplementary tables and sanity checks, from the tags
	$(PYTHON) $(S)/literature/04_checks.py
	$(PYTHON) $(S)/literature/06_headline_numbers.py
	$(PYTHON) $(S)/literature/07_supplement_tables.py
	$(PYTHON) $(S)/literature/08_multimodal_sanity.py
	$(PYTHON) $(S)/literature/09_partial_year_check.py

# ---------------------------------------------------------------- trials and devices
trials-api:  ## ClinicalTrials.gov download (network)
	$(PYTHON) $(S)/trials/01_pull_trials.py

trials:  ## trial measures from the stored ClinicalTrials.gov records
	$(PYTHON) $(S)/trials/02_trial_metrics.py

devices:  ## FDA device text flags and rules (needs pdftotext and the decision summary PDFs)
	$(PYTHON) -u $(S)/devices/01_fda_devices.py
	$(PYTHON) $(S)/devices/02_device_metrics.py

# ---------------------------------------------------------------- human screening
screening:  ## merge the two screeners and the third reviewer; kappa and final lists
	$(PYTHON) $(S)/screening/01_final_screening.py

tag-check:  ## draw the tag hand-check sample (needs the Scopus records)
	$(PYTHON) $(S)/screening/02_make_tag_check.py

# ---------------------------------------------------------------- figures
figures:  ## Figure 1 (PPTX), Figures 2 to 5 from derived data, then Figure 6 (needs Chrome)
	$(PYTHON) $(S)/figures/fig1_overview.py
	$(PYTHON) $(S)/figures/fig2_knowledge.py
	$(PYTHON) $(S)/figures/fig3_landscape.py
	$(PYTHON) $(S)/figures/fig4_integration.py
	$(PYTHON) $(S)/figures/fig5_translation.py
	$(PYTHON) $(S)/figures/fig6_digital_twin.py
	$(PYTHON) $(S)/figures/figS1_workflow.py

fig6:  ## Figure 6 only
	$(PYTHON) $(S)/figures/fig6_digital_twin.py

# ---------------------------------------------------------------- data release
release:  ## collect shareable derived files into ./release with SHA256SUMS
	$(PYTHON) scripts/make_data_release.py --out release
