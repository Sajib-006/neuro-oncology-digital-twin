"""Build the final labels of the tag check from the two coder sheets and the third review.

Input : two filled coder sheets (sheet "Papers", same layout as 02_make_tag_check.py makes)
        and the completed third-review workbook, with two sheets:
          "Papers"           clinical-records rows: "FINAL clinical records (Yes or No)" and,
                             where needed, "FINAL combines 2+ (Yes or No)"
          "Other questions"  one row per remaining difference: question text and "FINAL (Yes or No)"
Output: one workbook in the coder-sheet layout, with the final answer for every question.
        Pass it to 03_score_tag_check.py as --resolved.

Rules: where the two coders agree, their answer is kept. Where they differ, the third-review
answer is used. Where one coder answered Unsure or left the cell blank, the other coder's
answer is used. The script stops if any difference is left unsettled.

Run:
  python src/screening/04_settle_tag_check.py --coder A=path/A.xlsx --coder B=path/B.xlsx \
      --third path/third_review_completed.xlsx --out path/FINAL_tag_labels.xlsx
"""
import argparse
import pandas as pd

# start of the question text in the "Other questions" sheet -> question id
OTHER = {"Original research": "Q1", "Uses an AI": "Q2", "Analyses imaging": "Q3a",
         "Analyses pathology": "Q3b", "Analyses bulk": "Q3c", "Analyses single-cell": "Q3d",
         "Analyses spatial": "Q3e", "Combines 2": "Q4", "Tests the model": "Q5"}


def answer(v):
    s = str(v).strip().lower()
    return {"yes": "Yes", "no": "No"}.get(s)          # Unsure and blank -> None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coder", action="append", required=True, help="Name=path.xlsx (give two)")
    ap.add_argument("--third", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    assert len(a.coder) == 2, "give exactly two coders"
    A, B = (pd.read_excel(c.split("=", 1)[1], sheet_name="Papers").set_index("paper_id")
            for c in a.coder)
    B = B.loc[A.index]
    cols = {c.split(".")[0]: c for c in A.columns if c.startswith("Q") and c.rstrip().endswith("?")}

    third = pd.read_excel(a.third, sheet_name=None)
    final = {}
    for _, r in third["Papers"].iterrows():
        final[(r.paper_id, "Q3f")] = answer(r["FINAL clinical records (Yes or No)"])
        if answer(r["FINAL combines 2+ (Yes or No)"]):
            final[(r.paper_id, "Q4")] = answer(r["FINAL combines 2+ (Yes or No)"])
    for _, r in third.get("Other questions", pd.DataFrame()).iterrows():
        q = [v for k, v in OTHER.items() if str(r.question).startswith(k)]
        assert len(q) == 1, r.question
        final[(r.paper_id, q[0])] = answer(r["FINAL (Yes or No)"])
    assert all(final.values()), "third review has an empty FINAL cell"

    out = A.copy()
    n = {"agreed": 0, "third": 0, "one_unsure": 0}
    for pid in A.index:
        for q, c in cols.items():
            x, y = answer(A.at[pid, c]), answer(B.at[pid, c])
            if (pid, q) in final:
                out.at[pid, c] = final[(pid, q)]; n["third"] += 1
            elif x and y:
                assert x == y, f"unsettled difference: {pid} {q}"
                out.at[pid, c] = x; n["agreed"] += 1
            else:
                out.at[pid, c] = x or y; n["one_unsure"] += 1
    out.reset_index().to_excel(a.out, sheet_name="Papers", index=False)
    print(f"final labels -> {a.out}  ({n})")


if __name__ == "__main__":
    main()
