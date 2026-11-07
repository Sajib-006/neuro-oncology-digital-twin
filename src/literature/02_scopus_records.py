"""Download every Scopus record in the AI set (T AND A), year by year.

Input : the Scopus Search API (network; needs SCOPUS_API_KEY in the environment)
Output: lit/records/T_A_<year>.jsonl.gz   title, abstract, keywords and other fields
        lit/records_manifest.csv          year, expected, written, sha256, pull date

COMPLETE view, 25 records per request, cursor paging, query sent by POST.
Hard check: the number of records written for a year must equal Scopus's totalResults
for that year's query. If not, the year file is deleted and the run stops, because a
partial year would bias every share computed later.
The paper's records were downloaded on 2026-09-24. Scopus terms do not allow the
abstracts to be shared, so the released data hold only record IDs, DOIs and tags.
Run: python -u src/literature/02_scopus_records.py [--years 2024]
"""
import os, sys, csv, json, gzip, time, hashlib, datetime, argparse
import urllib.parse, urllib.request, urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config
import blocks as b

URL = "https://api.elsevier.com/content/search/scopus"
OUT = str(config.OUT_DIR / "lit" / "records")
MANIFEST = str(config.out("lit/records_manifest.csv"))
YEARS = list(range(2000, 2027))
PAGE = 25


def call(params, key, tries=6):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(URL, data=data, headers={
        "X-ELS-APIKey": key, "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
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


def slim(e):
    """Keep what tagging, dedup and the venue/country analyses need."""
    affs = e.get("affiliation", []) or []
    auths = e.get("author", []) or []
    return {
        "eid": e.get("eid"),
        "doi": e.get("prism:doi"),
        "title": e.get("dc:title"),
        "abstract": e.get("dc:description"),
        "keywords": e.get("authkeywords"),
        "cover_date": e.get("prism:coverDate"),
        "venue": e.get("prism:publicationName"),
        "source_id": e.get("source-id"),
        "aggregation_type": e.get("prism:aggregationType"),
        "doctype": e.get("subtype"),
        "cited_by": e.get("citedby-count"),
        "open_access": e.get("openaccessFlag"),
        "author_ids": [a.get("authid") for a in auths],
        "affil_countries": [a.get("affiliation-country") for a in affs],
        "affil_names": [a.get("affilname") for a in affs],
    }


def pull_year(year, key, query):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"T_A_{year}.jsonl.gz")
    cursor, written, expected = "*", 0, None
    with gzip.open(path, "wt") as f:
        while True:
            d = call({"query": query, "view": "COMPLETE", "count": PAGE,
                      "cursor": cursor}, key)["search-results"]
            if expected is None:
                expected = int(d["opensearch:totalResults"])
                if expected == 0:
                    break
            entries = d.get("entry", [])
            if not entries or (len(entries) == 1 and "error" in entries[0]):
                break
            for e in entries:
                f.write(json.dumps(slim(e)) + "\n")
            written += len(entries)
            nxt = d.get("cursor", {}).get("@next")
            if not nxt or nxt == cursor or written >= expected:
                break
            cursor = nxt
            time.sleep(0.15)
    if written != expected:
        os.remove(path)
        raise SystemExit(f"{year}: wrote {written} but Scopus reports {expected} - "
                         "year file deleted, stopping.")
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
    return expected, written, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=YEARS)
    a = ap.parse_args()
    key = os.environ["SCOPUS_API_KEY"]
    base = b.tak(b.T, b.A)

    done = set()
    if os.path.exists(MANIFEST):
        done = {int(r["year"]) for r in csv.DictReader(open(MANIFEST))}
    new = not os.path.exists(MANIFEST)
    with open(MANIFEST, "a", newline="") as mf:
        w = csv.writer(mf)
        if new:
            w.writerow(["year", "expected", "written", "sha256_16", "pull_date", "query_id"])
        for year in a.years:
            if year in done:
                continue
            exp, got, h = pull_year(year, key, b.with_year(base, year))
            w.writerow([year, exp, got, h, datetime.date.today().isoformat(), "MASTER_T_A"])
            mf.flush()
            print(f"  {year}: {got:,} records (expected {exp:,})", flush=True)


if __name__ == "__main__":
    main()
