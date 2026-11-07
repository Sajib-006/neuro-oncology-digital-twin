"""Rule-based trial measures from the stored ClinicalTrials.gov records (no new download).

Input : trials/raw/all_brain_tumour_trials.json.gz, trials/raw/candidates_full.json.gz
        (01_pull_trials.py)
Output: trials/trial_metrics.csv               one row per candidate
        trials/trial_summary.csv               denominators and counts (5,299 primary trials)
        trials/trial_share_by_start_year.csv   all primary trials per start year

Fixed rules:
  primary        conditions name a primary CNS tumor term. Trials whose conditions name
                 only brain metastases are dropped from BOTH numerator and denominator.
  ai_main        an AI term (not radiomics alone) in the title, brief summary, conditions,
                 keywords, intervention names/descriptions or outcome measures.
  ai_role        where the AI term sits: 'intervention', 'primary_outcome' or
                 'other_main_field'.
  due_results    primary completion date on or before one year before the data date.
  results        results posted on ClinicalTrials.gov, or a linked publication marked
                 RESULT in the record's reference list.
These keyword rules narrow the list; the final list comes from human screening
(src/screening/01_final_screening.py).
Run: python src/trials/02_trial_metrics.py
"""
import os, re, sys, json, gzip, datetime
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
config.use("literature")
import blocks as b

T = "trials"
DATA_DATE = config.CTGOV_DATA_DATE
PRIMARY = re.compile(r"glioma|glioblastoma|astrocytoma|oligodendroglioma|ependymoma|"
                     r"medulloblastoma|meningioma|craniopharyngioma|dipg|diffuse midline|"
                     r"brain (stem )?(tumou?r|neoplasm|cancer)|cns (tumou?r|neoplasm)|"
                     r"central nervous system (tumou?r|neoplasm)|atypical teratoid|"
                     r"pineoblastoma|ganglioglioma|cns lymphoma|primary central nervous", re.I)
METS = re.compile(r"metasta", re.I)
rx_ai = b.compile_block(b.A + ["neural network*", "computer-aided"])
rx_rad = re.compile(r"radiomic", re.I)


def g(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def primary_only(conds):
    text = " ; ".join(conds or [])
    if PRIMARY.search(text):
        return True
    return not METS.search(text)      # neither term: keep (matched the brain-tumor query)


def date_of(s):
    if not s:
        return None
    parts = [int(x) for x in s.split("-")]
    return datetime.date(parts[0], parts[1] if len(parts) > 1 else 12, parts[2] if len(parts) > 2 else 28)


def main():
    den = json.load(gzip.open(config.inp(f"{T}/raw/all_brain_tumour_trials.json.gz")))
    den_rows = []
    for r in den:
        ps = r["protocolSection"]
        den_rows.append([g(ps, "identificationModule", "nctId"),
                         primary_only(g(ps, "conditionsModule", "conditions", default=[])),
                         (g(ps, "statusModule", "startDateStruct", "date") or "")[:4]])
    den = pd.DataFrame(den_rows, columns=["nct_id", "primary", "start_year"])

    rows = []
    for r in json.load(gzip.open(config.inp(f"{T}/raw/candidates_full.json.gz"))):
        ps = r["protocolSection"]
        nct = g(ps, "identificationModule", "nctId")
        conds = g(ps, "conditionsModule", "conditions", default=[])
        kws = g(ps, "conditionsModule", "keywords", default=[])
        title = " ".join(filter(None, [g(ps, "identificationModule", "briefTitle"),
                                       g(ps, "identificationModule", "officialTitle")]))
        summary = g(ps, "descriptionModule", "briefSummary", default="")
        ints = g(ps, "armsInterventionsModule", "interventions", default=[])
        int_text = " ; ".join(f"{i.get('name', '')} {i.get('description', '')}" for i in ints)
        prim = " ; ".join(f"{o.get('measure', '')} {o.get('description', '')}"
                          for o in g(ps, "outcomesModule", "primaryOutcomes", default=[]))
        sec = " ; ".join(f"{o.get('measure', '')} {o.get('description', '')}"
                         for o in g(ps, "outcomesModule", "secondaryOutcomes", default=[]))
        fields = {"title": title, "summary": summary, "conditions": " ; ".join(conds),
                  "keywords": " ; ".join(kws), "intervention": int_text,
                  "primary_outcome": prim, "secondary_outcome": sec}
        hits = [k for k, v in fields.items() if rx_ai.search(v or "")]
        role = ("intervention" if "intervention" in hits else
                "primary_outcome" if "primary_outcome" in hits else
                "other_main_field" if hits else "")
        pcd = date_of(g(ps, "statusModule", "primaryCompletionDateStruct", "date"))
        due = bool(pcd and pcd <= DATA_DATE.replace(year=DATA_DATE.year - 1))
        refs = g(ps, "referencesModule", "references", default=[])
        pub = any(x.get("type") == "RESULT" for x in refs)
        rows.append([nct, g(ps, "identificationModule", "briefTitle"),
                     g(ps, "designModule", "studyType"),
                     (g(ps, "statusModule", "startDateStruct", "date") or "")[:4],
                     primary_only(conds), bool(hits), role, "|".join(hits),
                     bool(rx_rad.search(" ".join(fields.values()))), due,
                     bool(r.get("hasResults")), pub])
    c = pd.DataFrame(rows, columns=["nct_id", "brief_title", "study_type", "start_year", "primary",
                                    "ai_main", "ai_role", "ai_fields", "radiomics", "due_results",
                                    "results_posted", "result_publication_linked"])
    c.to_csv(config.out(f"{T}/trial_metrics.csv"), index=False)

    inc = c[c.primary & c.ai_main]
    due = inc[inc.due_results]
    summ = [
        ("denominator_all", len(den)),
        ("denominator_primary", int(den.primary.sum())),
        ("candidates_ai_or_radiomics", len(c)),
        ("candidates_primary", int(c.primary.sum())),
        ("ai_main_primary", len(inc)),
        ("ai_role_intervention", int((inc.ai_role == "intervention").sum())),
        ("ai_role_primary_outcome", int((inc.ai_role == "primary_outcome").sum())),
        ("ai_role_other_main_field", int((inc.ai_role == "other_main_field").sum())),
        ("ai_main_interventional", int((inc.study_type == "INTERVENTIONAL").sum())),
        ("ai_main_observational", int((inc.study_type == "OBSERVATIONAL").sum())),
        ("due_results", len(due)),
        ("due_results_posted", int(due.results_posted.sum())),
        ("due_results_publication_linked", int(due.result_publication_linked.sum())),
        ("due_any_results", int((due.results_posted | due.result_publication_linked).sum())),
        ("excluded_metastasis_only", int((~c.primary).sum())),
        ("excluded_no_ai_in_main_fields", int((c.primary & ~c.ai_main).sum())),
    ]
    by = inc.groupby("start_year").size().rename("ai_trials").to_frame().join(
        den[den.primary].groupby("start_year").size().rename("all_primary_trials"), how="right").fillna(0)
    by["share_pct"] = 100 * by.ai_trials / by.all_primary_trials
    for yr in ["2022", "2023", "2024", "2025", "2026"]:
        if yr in by.index:
            summ.append((f"share_start_{yr}", round(by.loc[yr, "share_pct"], 1)))
    pd.DataFrame(summ, columns=["name", "value"]).to_csv(config.out(f"{T}/trial_summary.csv"), index=False)
    by.to_csv(config.out(f"{T}/trial_share_by_start_year.csv"))
    for k, v in summ:
        print(f"  {k:<34} {v}")


if __name__ == "__main__":
    main()
