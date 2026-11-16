"""Final human screening of trials and devices (Methods; Fig. 5b,c; Tables S7 and S8).

Two reviewers screened independently; a third reviewer settled every row with a
difference or a missing rating.
Input : audit/human_review/screening_Erin.xlsx, screening_Rafi.xlsx   the two independent sheets
        audit/human_review/screening_RESOLVE_Erin_Rafi_done.xlsx     third-reviewer decisions
        trials/trial_metrics.csv, trials/trial_share_by_start_year.csv (trials/02_trial_metrics.py)
        devices/device_metrics.csv                                    (devices/02_device_metrics.py)
Output: audit/screening_final_trials.csv, audit/screening_final_devices.csv   one row per candidate
        audit/screening_summary.csv     kappa, agreement, final counts, roles, results posting
        trials/trial_share_by_start_year_screened.csv
Kappa is computed on the rows both reviewers rated. For rows both included, the AI role
is taken from the second reviewer. One trial that both reviewers included breaks a written
exclusion rule (pituitary adenoma) and is removed after screening (POST_SCREEN_EXCLUDE).
Run: python src/screening/01_final_screening.py
"""
import os, sys
import pandas as pd
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config

H = config.inp("audit/human_review")
E = pd.read_excel(f"{H}/screening_Erin.xlsx", sheet_name=None)
R = pd.read_excel(f"{H}/screening_Rafi.xlsx", sheet_name=None)
F = pd.read_excel(f"{H}/screening_RESOLVE_Erin_Rafi_done.xlsx", sheet_name=None)
summ = []

def final(sheet, key, role, resolve_sheet):
    e, r = E[sheet], R[sheet]
    m = e[[key, "include (1 or 0)", role]].merge(r[[key, "include (1 or 0)", role]], on=key, suffixes=("_1", "_2"))
    a, b = m["include (1 or 0)_1"], m["include (1 or 0)_2"]
    both = a.notna()
    kap = cohen_kappa_score(a[both].astype(int), b[both].astype(int))
    agree = int((a[both] == b[both]).sum())
    f = F[resolve_sheet].set_index(key)
    m["final"] = a.where(a == b)
    m["final_role"] = m[role + "_1"].where(a == b)
    m.loc[m.final == 1, "final_role"] = m.loc[m.final == 1, role + "_2"]          # agreed rows: reviewer-2 role
    for k, row in f.iterrows():
        i = m.index[m[key] == k][0]
        m.loc[i, "final"] = row["FINAL include (1 or 0)"]
        m.loc[i, "final_role"] = row.get(f"FINAL {role}")
    assert m.final.notna().all()
    summ.extend([(f"{sheet}_screened", len(m)), (f"{sheet}_both_rated", int(both.sum())),
                 (f"{sheet}_agree", agree), (f"{sheet}_kappa", round(kap, 2)),
                 (f"{sheet}_resolved_by_third", len(f)), (f"{sheet}_included_final", int(m.final.sum()))])
    return m

t = final("Trials", "nct_id", "AI role", "Trials to resolve")
d = final("Devices", "submission", "device function", "Devices to resolve")

# Eligibility corrections found after screening (2026-11-06). Both reviewers
# included these, but the record breaks a written exclusion rule. Kappa above uses the
# original ratings; only the final list changes.
POST_SCREEN_EXCLUDE = {"NCT07568366": "pituitary adenoma surgery; pituitary tumors are outside scope"}
summ.append(("trials_included_before_correction", int(t.final.sum())))
for k, why in POST_SCREEN_EXCLUDE.items():
    assert (t.nct_id == k).sum() == 1, k
    t.loc[t.nct_id == k, ["final", "final_role"]] = [0, None]
    print(f"  removed after screening: {k} ({why})")
summ.append(("trials_removed_after_screening", len(POST_SCREEN_EXCLUDE)))
summ.append(("trials_included_final_corrected", int(t.final.sum())))

tm = pd.read_csv(config.inp("trials/trial_metrics.csv"))
t = t.merge(tm[["nct_id", "brief_title", "study_type", "start_year", "due_results", "results_posted",
                "result_publication_linked"]], on="nct_id")
ti = t[t.final == 1]
due = ti[ti.due_results]
summ += [("trials_included_interventional", int((ti.study_type == "INTERVENTIONAL").sum())),
         ("trials_included_observational", int((ti.study_type == "OBSERVATIONAL").sum())),
         ("trials_due_results", len(due)), ("trials_due_results_posted", int(due.results_posted.sum())),
         ("trials_due_result_paper_linked", int(due.result_publication_linked.sum()))]
for r_, n in ti.final_role.value_counts().items():
    summ.append((f"trials_role_{r_}", int(n)))
t.to_csv(config.out("audit/screening_final_trials.csv"), index=False)

dm = pd.read_csv(config.inp("devices/device_metrics.csv"))
dm["submission"] = dm.submission.str.split("/").str[0]
d = d.merge(dm[["submission", "device", "company", "year"]], on="submission")
di = d[d.final == 1]
summ += [("devices_earliest_year", int(di.year.min()))]
for r_, n in di.final_role.value_counts().items():
    summ.append((f"devices_function_{r_}", int(n)))
d.to_csv(config.out("audit/screening_final_devices.csv"), index=False)

# share of primary brain tumor trials per start year (denominator from trials/02_trial_metrics.py)
by = pd.read_csv(config.inp("trials/trial_share_by_start_year.csv"), dtype={"start_year": str})
k = ti.start_year.astype(str).value_counts()
by["ai_trials_screened"] = by.start_year.map(k).fillna(0).astype(int)
by["share_pct_screened"] = 100 * by.ai_trials_screened / by.all_primary_trials
by.to_csv(config.out("trials/trial_share_by_start_year_screened.csv"), index=False)
for y in ["2022", "2023", "2024", "2025", "2026"]:
    v = by.loc[by.start_year == y, "share_pct_screened"]
    if len(v): summ.append((f"trials_share_start_{y}", round(float(v.iloc[0]), 1)))
pd.DataFrame(summ, columns=["name", "value"]).to_csv(config.out("audit/screening_summary.csv"), index=False)
for a, b in summ: print(f"  {a:<36} {b}")
print(di[["submission", "year", "device", "final_role"]].to_string(index=False))
