# Derived data

The derived data are not stored in git. They are attached to release v1.1.0 of this repository
as one archive (https://github.com/Sajib-006/neuro-oncology-digital-twin/releases/tag/v1.1.0). Unpack it here, or anywhere and point `DATA_DIR` at it. The archive is made by
`scripts/make_data_release.py`, which also writes `SHA256SUMS` (full sha256 of every file;
check with `sha256sum -c SHA256SUMS`) and `MANIFEST.csv`.

Paths below are relative to `DATA_DIR`. "Class" means one of the ten tumor classes in
`src/knowledge_bases/entities.py` (GBM, Astrocytoma, Oligodendroglioma, DMG_H3K27,
Medulloblastoma, Ependymoma, ATRT, PilocyticAstrocytoma, Meningioma, Craniopharyngioma).

## Knowledge bases

| File | Made by | Columns or content |
|---|---|---|
| `provenance_opentargets.csv` | knowledge_bases/02 | entity, label, ontology_id, data_version, build_date, n_targets, sha256_16, n_terms, excluded_terms |
| `provenance_ctd.csv` | knowledge_bases/04 | source_url, source_file_mtime_utc, source_bytes, source_sha256_16, pull_date, rows_scanned, rows_kept, rows_curated, rows_inferred, subset_sha256_16 |
| `provenance_ctd_release.csv` | knowledge_bases/06 | ctd_report_created |
| `provenance_disgenet.csv` | knowledge_bases/05 | release, level, rows, source_url, mirror, download_date, sha256_16 |
| `provenance_gprofiler.csv` | knowledge_bases/08 | gprofiler_version, organism, sources, threshold, method, date |
| `raw/opentargets/<class>.jsonl` | knowledge_bases/02 | one target per line: entity, gene, ensembl, score, datasources, datatypes, terms (from Open Targets 26.09, CC0) |
| `raw/opentargets/terms.csv` | knowledge_bases/02 | entity, term, term_name, n_direct_targets, is_entity_term |
| `matrices/<kb>_<level>_gene_entity.csv` | knowledge_bases/06 | gene, then one score column per class (0 = no link) |
| `support_counts.csv` | knowledge_bases/06 | kg, tier, entity, genes, kg_total_genes |
| `opentargets_genes_by_datasource.csv` | knowledge_bases/06 | datasource, then genes per class |
| `disgenet_v7_diseases_matched.csv` | knowledge_bases/06 | entity, diseaseId, diseaseName |
| `similarity/<kb>_<level>_<metric>.csv` | knowledge_bases/07 | class x class similarity (cosine or jaccard; empty = not measurable) |
| `similarity_long.csv` | knowledge_bases/07 | kg, tier, metric, entity_1, entity_2, similarity, support_1, support_2 |
| `enrichment/<kb>_<level>_annotated_terms.csv` | knowledge_bases/08 | kg, tier, entity, source, term_id, term_name, p_value, intersection_size, term_size |
| `enrichment/<kb>_<level>_annotated_pathway_jaccard.csv` | knowledge_bases/08 | class x class Jaccard of enriched term sets |
| `null_similarity/<gene or pathway>_<kb>_<level>_{log2oe,expected}.csv` | knowledge_bases/09 | class x class score and mean random overlap |
| `null_similarity/size_check.csv` | knowledge_bases/09 | level, kg, tier, entities, pairs, rho_vs_smaller_size, verdict |
| `null_similarity/PREREGISTERED.csv` | written before the test was run | method, pass mark and script checksum stored before the first run (the script was edited later, so its checksum no longer matches) |
| `similarity_robust/pairs_<kb>_<level>.csv` | knowledge_bases/10 | kg, tier, entity_1, entity_2, size_1, size_2, observed, expected_curveball, jaccard, curveball_log2oe, downsampled_jaccard |
| `similarity_robust/size_check_robust.csv` | knowledge_bases/10 | kg, tier, metric, tumors, pairs, downsample_n, rho_vs_smaller_size, ci_low, ci_high, perm_p, reading |

`<kb>` is OpenTargets, DisGeNET or CTD. `<level>` is curated or all, plus two sensitivity
levels: OpenTargets curatedplusdrug and DisGeNET curatednoctd.

## Literature (no titles or abstracts)

| File | Made by | Columns or content |
|---|---|---|
| `lit/queries_<form>.csv` | literature/01 | query_id, family, block_expr, query_string_without_year, parent_id, feeds_figure, year_and_filter_suffix (the exact Scopus queries) |
| `lit/counts_by_year_<form>.csv` | literature/01 | query_id, year, count, database, pull_date, response_sha256_16 |
| `lit/records_manifest.csv` | literature/02 | year, expected, written, sha256_16, pull_date, query_id |
| `lit/tagged_records.csv.gz` | literature/03 | eid, doi, year, doctype, has_abstract, then 0/1 tags: `M*_mention`, `M*_used` (data types), n_modalities_used, multimodal_used, `K*` and `K*_mention` (tasks), `R*` (model families), `X*` (evaluation and other topics; `*_anymention` before removing future-work sentences), review_title, radiogenomic, `E_*` (tumor classes), pediatric, _T_local, _A_local, in_primary_set, T_focus. The Scopus venue, source_id, aggregation_type and cited_by columns are removed. |
| `lit/tag_summary_by_year*.csv` | literature/03 | year, n_records, then the yearly sum of each tag |
| `lit/checks.csv` | literature/04 | check, what, verdict, detail |
| `lit/entity_counts.csv` | literature/05 | entity, papers_all, papers_ai, ai_share, pull_date, sha_all, sha_ai |
| `lit/headline_numbers.csv` | literature/06 | name, value, detail (every literature number in the paper) |
| `lit/share_by_year.csv` | literature/06 | year, n, k, share, lo, hi (papers naming 2+ data types, Wilson 95% CI) |

`<form>` is visible, tak, focused or focused_research (the one used in Figure 4a).

## Trials

| File | Made by | Columns or content |
|---|---|---|
| `trials/raw/all_brain_tumour_trials.json.gz` | trials/01 | ClinicalTrials.gov records (short fields) for the condition query |
| `trials/raw/candidates_full.json.gz` | trials/01 | full records of the 118 candidates |
| `trials/provenance.csv` | trials/01 | item, value (API version, data timestamp, queries, counts, hashes) |
| `trials/candidates_tagged.csv` | trials/01 | one row per candidate with keyword flags and a matched snippet |
| `trials/trial_screening_sheet.csv` | trials/01 | the blank sheet with screening rules in its first lines |
| `trials/trial_metrics.csv` | trials/02 | nct_id, brief_title, study_type, start_year, primary, ai_main, ai_role, ai_fields, radiomics, due_results, results_posted, result_publication_linked |
| `trials/trial_summary.csv` | trials/02 | name, value |
| `trials/trial_share_by_start_year.csv` | trials/02 | start_year, ai_trials, all_primary_trials, share_pct |
| `trials/trial_share_by_start_year_screened.csv` | screening/01 | the same plus ai_trials_screened, share_pct_screened |

## Devices

| File | Made by | Columns or content |
|---|---|---|
| `devices/raw/f_178541` | download | the FDA list of AI-enabled devices (CSV, page of 4 Sep 2026) |
| `devices/provenance.csv` | devices/01 | item, value |
| `devices/devices_tagged.csv` | devices/01 | submission, decision_date, device, company, panel, product_code, pdf_status, text_chars, flag_specific, flag_metastasis_only, flag_broad, indication_text |
| `devices/device_screening_sheet.csv` | devices/01 | the blank sheet with screening rules in its first lines |
| `devices/device_metrics.csv` | devices/02 | submission, device, company, panel, year, flag_specific_anywhere, flag_metastasis_only, tumor_in_use_statement, strict_primary_tumor |
| `devices/device_context_snippets.csv` | devices/02 | submission, device, in_use_statement_window, negated, term, context |
| `devices/device_summary.csv` | devices/02 | name, value |
| `devices/pdf_manifest.csv` | make_data_release.py | submission, url, bytes, sha256 of each decision summary PDF used |

## Human screening

| File | Made by | Columns or content |
|---|---|---|
| `audit/human_review/screening_Erin.xlsx`, `screening_Rafi.xlsx` | the two screeners | sheets "How to fill" (the rules they were given), "Trials", "Devices" |
| `audit/human_review/screening_RESOLVE_Erin_Rafi_done.xlsx` | the third reviewer | sheets "How to settle", "Trials to resolve", "Devices to resolve" with FINAL decisions and a note for each |
| `audit/screening_final_trials.csv` | screening/01 | nct_id, both ratings and AI roles (_1, _2), final, final_role, brief_title, study_type, start_year, due_results, results_posted, result_publication_linked |
| `audit/screening_final_devices.csv` | screening/01 | submission, both ratings and functions, final, final_role, device, company, year |
| `audit/screening_summary.csv` | screening/01 | name, value (kappa, agreement, final counts, roles, results posting, start-year shares) |
| `audit/tag_check/tag_check_strata.csv` | screening/02 | stratum, pool_N, sampled_n, weight |
| `audit/tag_check/tags_sample_KEY.csv` | screening/02 | the 100 sampled papers: paper_id, eid, doi, year, stratum, weight and their tags |
| `audit/tag_check/tag_check_coder_A.xlsx`, `tag_check_coder_B.xlsx` | the two coders | sheet "Papers": paper_id and the answers (Yes, No, Unsure) to the ten questions; titles, abstracts and notes removed |
| `audit/tag_check/tag_check_final_labels.xlsx` | screening/04 | the same layout with the final answer after the third review |

## Supplementary tables

| File | Made by | Content |
|---|---|---|
| `supplement/S_search_blocks.tex` | literature/07 | Supplementary Table S1 |
| `supplement/S_entities.tex` | literature/07 | Supplementary Table S4 |
| `supplement/S_query_forms.tex`, `S_checks.tex` | literature/07 | search forms and automatic checks |
