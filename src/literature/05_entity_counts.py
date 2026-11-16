"""Scopus counts per tumor class, 2015-2026 pooled (Fig. 2f,g).

Input : the Scopus Search API (network; needs SCOPUS_API_KEY in the environment)
Output: lit/entity_counts.csv   papers_all, papers_ai and ai_share per class

For each class E (blocks.E: the ten classes plus brain metastasis):
  GEN  class term in TITLE or AUTHKEY                          -> all papers on E
  AI   GEN AND the AI block in TITLE-ABS or AUTHKEY            -> AI papers on E
Research papers only (articles and conference papers), as in the rest of the survey.
The paper's counts were pulled on 2026-09-28.
Run: python -u src/literature/05_entity_counts.py
"""
import os, sys, csv, datetime, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import config
import blocks as b

spec = importlib.util.spec_from_file_location("c10", os.path.join(HERE, "01_scopus_counts.py"))
c10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c10)

YEARS = "AND PUBYEAR > 2014 AND PUBYEAR < 2027"


def title_or_key(terms):
    return "( TITLE" + b.scopus_or(terms) + " OR AUTHKEY" + b.scopus_or(terms) + " )"


def main():
    key = os.environ["SCOPUS_API_KEY"]
    rows = []
    for ent, terms in b.E.items():
        gen = f"{title_or_key(terms)} {YEARS} {b.FILTERS_RESEARCH}"
        ai = f"{title_or_key(terms)} AND {b.visible(b.A)} {YEARS} {b.FILTERS_RESEARCH}"
        n_gen, h1, _ = c10.count(gen, key)
        n_ai, h2, rem = c10.count(ai, key)
        rows.append([ent, n_gen, n_ai, round(n_ai / n_gen, 4) if n_gen else "",
                     datetime.date.today().isoformat(), h1, h2])
        print(f"  {ent:<22} all {n_gen:>7,}  AI {n_ai:>6,}  ({100*n_ai/max(n_gen,1):.1f}%)", flush=True)
    with open(config.out("lit/entity_counts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity", "papers_all", "papers_ai", "ai_share", "pull_date",
                    "sha_all", "sha_ai"])
        w.writerows(rows)
    print(f"written -> lit/entity_counts.csv (quota remaining {rem})")


if __name__ == "__main__":
    main()
