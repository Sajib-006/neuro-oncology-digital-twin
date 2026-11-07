"""Scopus hit counts by year: denominators, the AI set and each data type (Fig. 2a, checks).

Input : the Scopus Search API (network; needs SCOPUS_API_KEY in the environment)
Output: lit/queries_<form>.csv          query registry with the exact query strings
        lit/counts_by_year_<form>.csv   one count per query and year, with a response hash

Only numbers are needed here, so these are count queries (count=1). Records of the AI set
are downloaded separately (02_scopus_records.py) and tagged locally.

Per year 2000-2026:
  N1_T                  all primary CNS tumor papers                   T
  N2_onc_A              AI in oncology overall (T joined in)           (ONC or T) AND A
  MASTER_T_A            AI in brain tumors                             T AND A
  <Mk>_GEN, <Mk>_AI     each data type, general and AI                 T AND Mk [AND A]
Nesting holds by construction (the AI query = the general query AND A); 04_checks.py
checks it on the returned numbers.

The paper uses --form focused --research (Fig. 2a) and --form visible (checks); the
counts were pulled on 2026-09-28. The output file is appended to, so a stopped run resumes.
Run: python -u src/literature/01_scopus_counts.py --form focused --research
"""
import os, sys, csv, json, time, hashlib, datetime, argparse
import urllib.parse, urllib.request, urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
import blocks as b

URL = "https://api.elsevier.com/content/search/scopus"
OUT = str(config.OUT_DIR / "lit")
YEARS = list(range(2000, 2027))


def registry(form):
    """form 'visible' (PRIMARY): title / abstract / author keywords, via b.visible().
    form 'tak': TITLE-ABS-KEY, which also searches hidden indexed keywords - upper bound."""
    f = {"visible": b.visible, "tak": b.tak, "focused": b.focused}[form]
    onc = b.NORMALIZER_ONCOLOGY + b.T
    q = [
        ("N1_T", "normalizer", "T", f(b.T), "", "2a,denominator"),
        ("N2_onc_A", "normalizer", "(ONC or T) AND A", f(onc, b.A), "", "context"),
        ("MASTER_T_A", "master", "T AND A", f(b.T, b.A), "N1_T", "all"),
    ]
    for mk, terms in b.M.items():
        q.append((f"{mk}_GEN", "modality", f"T AND {mk}", f(b.T, terms), "N1_T", "2a"))
        q.append((f"{mk}_AI", "modality", f"T AND {mk} AND A", f(b.T, terms, b.A),
                  f"{mk}_GEN", "2a"))
    return q


def count(query, key, tries=6):
    # POST, not GET: the modality x AI queries run to ~3,400 characters and Scopus
    # rejects URLs that long with HTTP 413. Verified 2026-09-24 that POST returns the
    # identical count to GET on a query short enough for both (T AND A, 2024: 3,352).
    data = urllib.parse.urlencode({"query": query, "count": 1, "view": "STANDARD"}).encode()
    req = urllib.request.Request(URL, data=data, headers={
        "X-ELS-APIKey": key, "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                remaining = r.headers.get("X-RateLimit-Remaining")
            d = json.loads(raw)
            n = int(d["search-results"]["opensearch:totalResults"])
            return n, hashlib.sha256(raw).hexdigest()[:16], remaining
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(2 ** attempt + 1)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=YEARS)
    ap.add_argument("--form", default="visible", choices=["visible", "tak", "focused"])
    ap.add_argument("--research", action="store_true",
                    help="articles and conference papers only (no reviews); output form "
                         "name gets the suffix _research")
    a = ap.parse_args()
    filters = b.FILTERS_RESEARCH if a.research else b.FILTERS
    tag = a.form + ("_research" if a.research else "")
    key = os.environ["SCOPUS_API_KEY"]
    os.makedirs(OUT, exist_ok=True)

    reg = registry(a.form)
    with open(os.path.join(OUT, f"queries_{tag}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "family", "block_expr", "query_string_without_year",
                    "parent_id", "feeds_figure", "year_and_filter_suffix"])
        for qid, fam, expr, qs, parent, feeds in reg:
            w.writerow([qid, fam, expr, qs, parent, feeds,
                        f"AND PUBYEAR = <year> {filters}"])

    out_path = os.path.join(OUT, f"counts_by_year_{tag}.csv")
    done = set()
    if os.path.exists(out_path):                      # resumable
        for r in csv.DictReader(open(out_path)):
            done.add((r["query_id"], int(r["year"])))
    new_file = not os.path.exists(out_path)
    pull_date = datetime.date.today().isoformat()
    with open(out_path, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["query_id", "year", "count", "database", "pull_date",
                        "response_sha256_16"])
        for year in a.years:
            for qid, fam, expr, qs, parent, feeds in reg:
                if (qid, year) in done:
                    continue
                n, h, rem = count(b.with_year(qs, year, filters), key)
                w.writerow([qid, year, n, "scopus", pull_date, h])
                f.flush()
                time.sleep(0.15)
            print(f"  {year}: done  (quota remaining {rem})", flush=True)
    print(f"written -> {out_path}")


if __name__ == "__main__":
    main()
