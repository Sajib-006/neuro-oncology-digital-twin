"""ClinicalTrials.gov inventory of AI trials in primary brain tumors (Fig. 5b, Table S7).

Input : the ClinicalTrials.gov API v2 (network, no key)
Output: trials/raw/all_brain_tumour_trials.json.gz   all trials matching the condition query
        trials/raw/candidates_full.json.gz           candidates, full records
        trials/provenance.csv                        API version, data timestamp, queries
        trials/candidates_tagged.csv                 one row per candidate, keyword flags
        trials/trial_screening_sheet.csv             blank sheet for two human screeners
        trials/denominator_by_start_year.csv
The paper used API version 2.0.5 with data of 24 September 2026. The registry changes
daily, so a new run will give other numbers; the stored downloads give the paper's.

Fixed BEFORE any trial was read (2026-09-24):
  Denominator  all trials whose CONDITION matches the brain tumor query (COND).
  Candidates   COND AND (AI terms OR radiomics) in any text field.
               Radiomics is flagged separately: in the literature search radiomics alone
               does not count as AI; for trials, human screeners decide whether machine
               learning is actually used.
  Inclusion    decided by TWO human screeners, not by keywords: AI or ML is the
               intervention, a diagnostic index test under evaluation, or the primary
               analysis method, in patients with PRIMARY CNS tumors. Trials of brain
               metastases only are excluded, matching the literature scope.
Run: python src/trials/01_pull_trials.py
"""
import os, re, sys, csv, json, gzip, time, datetime, hashlib
import urllib.parse, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
config.use("literature")
import blocks as b

API = "https://clinicaltrials.gov/api/v2"
OUT = str(config.OUT_DIR / "trials")

COND = ('glioma OR glioblastoma OR "brain tumor" OR "brain neoplasm" OR "CNS tumor" OR '
        'astrocytoma OR oligodendroglioma OR ependymoma OR medulloblastoma OR meningioma OR '
        'craniopharyngioma OR "diffuse midline glioma" OR DIPG')
AI_TERMS = ('"artificial intelligence" OR "machine learning" OR "deep learning" OR '
            '"neural network" OR "large language model" OR convolutional OR "computer-aided"')
RADIOMICS = 'radiomics OR radiomic'
CANDIDATE_TERM = f"({AI_TERMS}) OR ({RADIOMICS})"

rx_ai = b.compile_block(b.A + ["neural network*", "computer-aided"])
rx_rad = re.compile(r"radiomic", re.I)
rx_met = re.compile(r"metasta", re.I)


def get(path, params, tries=5):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def pull_all(params, fields=None):
    out, token, total = [], None, None
    while True:
        p = dict(params, pageSize=1000, format="json", countTotal="true")
        if fields:
            p["fields"] = ",".join(fields)
        if token:
            p["pageToken"] = token
        d = get("studies", p)
        if total is None:
            total = d.get("totalCount")          # only returned on the first page
        out += d.get("studies", [])
        token = d.get("nextPageToken")
        if not token:
            return out, total
        time.sleep(0.3)


def g(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
    return d if d is not None else default


def year(datestr):
    return int(datestr[:4]) if datestr and datestr[:4].isdigit() else None


def main():
    os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
    ver = get("version", {})
    pull_date = datetime.date.today().isoformat()

    # ---- denominator
    dfields = ["NCTId", "BriefTitle", "StartDate", "StudyType", "Phase", "OverallStatus",
               "Condition"]
    allt, n_all = pull_all({"query.cond": COND}, dfields)
    assert len(allt) == n_all, f"denominator: got {len(allt)} of {n_all}"
    p_all = os.path.join(OUT, "raw", "all_brain_tumour_trials.json.gz")
    with gzip.open(p_all, "wt") as f:
        json.dump(allt, f)

    # ---- candidates (full records)
    cand, n_cand = pull_all({"query.cond": COND, "query.term": CANDIDATE_TERM})
    assert len(cand) == n_cand, f"candidates: got {len(cand)} of {n_cand}"
    p_cand = os.path.join(OUT, "raw", "candidates_full.json.gz")
    with gzip.open(p_cand, "wt") as f:
        json.dump(cand, f)

    with open(os.path.join(OUT, "provenance.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "value"])
        for k, v in [("api_version", ver.get("apiVersion")),
                     ("data_timestamp", ver.get("dataTimestamp")), ("pull_date", pull_date),
                     ("query_cond", COND), ("query_term_candidates", CANDIDATE_TERM),
                     ("n_brain_tumour_trials", n_all), ("n_candidates", n_cand),
                     ("sha256_denominator", hashlib.sha256(open(p_all, "rb").read()).hexdigest()[:16]),
                     ("sha256_candidates", hashlib.sha256(open(p_cand, "rb").read()).hexdigest()[:16])]:
            w.writerow([k, v])

    # ---- denominator by start year
    by = {}
    for s in allt:
        y = year(g(s, "protocolSection", "statusModule", "startDateStruct", "date"))
        by[y] = by.get(y, 0) + 1
    with open(os.path.join(OUT, "denominator_by_start_year.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["start_year", "n_trials"])
        for y in sorted(k for k in by if k):
            w.writerow([y, by[y]])

    # ---- tag candidates and write the screening sheet
    rows = []
    for s in cand:
        ps = s.get("protocolSection", {})
        idm, st, ds = ps.get("identificationModule", {}), ps.get("statusModule", {}), ps.get("designModule", {})
        desc = ps.get("descriptionModule", {})
        arms = ps.get("armsInterventionsModule", {})
        outc = ps.get("outcomesModule", {})
        conds = g(ps, "conditionsModule", "conditions", default=[])
        interv = [f"{i.get('type','')}: {i.get('name','')}" for i in arms.get("interventions", [])]
        prim = [o.get("measure", "") for o in outc.get("primaryOutcomes", [])]
        fields = {
            "title": (idm.get("briefTitle") or "") + " ; " + (idm.get("officialTitle") or ""),
            "summary": desc.get("briefSummary") or "",
            "detail": desc.get("detailedDescription") or "",
            "intervention": " ; ".join(interv) + " ; " + " ; ".join(
                i.get("description", "") for i in arms.get("interventions", [])),
            "primary_outcome": " ; ".join(prim),
            "keywords": " ; ".join(g(ps, "conditionsModule", "keywords", default=[])),
        }
        ai_where = [k for k, v in fields.items() if rx_ai.search(v)]
        rad_where = [k for k, v in fields.items() if rx_rad.search(v)]
        text = " ".join(fields.values())
        m = rx_ai.search(text) or rx_rad.search(text)
        snip = ""
        if m:
            a, z = max(0, m.start() - 160), min(len(text), m.end() + 160)
            snip = "…" + text[a:m.start()] + "[[" + text[m.start():m.end()] + "]]" + text[m.end():z] + "…"
        locs = g(ps, "contactsLocationsModule", "locations", default=[])
        rows.append({
            "nct_id": idm.get("nctId"),
            "brief_title": idm.get("briefTitle"),
            "study_type": ds.get("studyType"),
            "phase": "|".join(ds.get("phases", []) or []),
            "status": st.get("overallStatus"),
            "start_year": year(g(st, "startDateStruct", "date")),
            "enrollment": g(ds, "enrollmentInfo", "count"),
            "sponsor_class": g(ps, "sponsorCollaboratorsModule", "leadSponsor", "class"),
            "countries": "|".join(sorted({l.get("country", "") for l in locs if l.get("country")})),
            "has_results": s.get("hasResults"),
            "conditions": "|".join(conds),
            "metastasis_in_conditions": int(bool(rx_met.search(" ".join(conds)))),
            "ai_term_in": "|".join(ai_where),
            "radiomics_in": "|".join(rad_where),
            "radiomics_only": int(not ai_where and bool(rad_where)),
            "interventions": " | ".join(interv),
            "primary_outcomes": " | ".join(prim)[:400],
            "matched_snippet": snip,
        })
    rows.sort(key=lambda r: (r["start_year"] or 0, r["nct_id"]))
    keys = list(rows[0].keys()) if rows else []
    with open(os.path.join(OUT, "candidates_tagged.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

    sheet_cols = ["nct_id", "brief_title", "study_type", "phase", "status", "start_year",
                  "conditions", "metastasis_in_conditions", "ai_term_in", "radiomics_only",
                  "interventions", "primary_outcomes", "matched_snippet"]
    code_cols = ["include (1/0)", "exclusion_reason", "ai_role (intervention / diagnostic test / "
                 "prognostic model / analysis only)", "prospective_evaluation_of_ai (1/0)",
                 "coder", "coder_2_include (1/0)", "coder_2", "agreed_include (1/0)", "notes"]
    with open(os.path.join(OUT, "trial_screening_sheet.csv"), "w", newline="") as f:
        f.write("# INCLUDE if AI/ML is the intervention, a diagnostic index test under evaluation,\n"
                "# or the primary analysis method, in patients with PRIMARY CNS tumours.\n"
                "# EXCLUDE brain-metastasis-only trials, trials where AI is only mentioned in\n"
                "# background, and radiomics trials with no machine-learning model.\n"
                "# Two independent human coders; disagreements resolved by discussion.\n"
                "# Record any AI assistance in the coder column.\n")
        w = csv.writer(f)
        w.writerow(sheet_cols + code_cols)
        for r in rows:
            w.writerow([r[c] for c in sheet_cols] + [""] * len(code_cols))

    print(f"API {ver.get('apiVersion')}, data {ver.get('dataTimestamp')}")
    print(f"brain-tumour trials: {n_all:,}; candidates: {n_cand}")
    print(f"  AI term somewhere: {sum(1 for r in rows if r['ai_term_in'])}; "
          f"radiomics only: {sum(r['radiomics_only'] for r in rows)}; "
          f"metastasis in conditions: {sum(r['metastasis_in_conditions'] for r in rows)}")
    types = {}
    for r in rows:
        types[r["study_type"]] = types.get(r["study_type"], 0) + 1
    print("  study types:", types)
    print(f"written -> {OUT}/")


if __name__ == "__main__":
    main()
