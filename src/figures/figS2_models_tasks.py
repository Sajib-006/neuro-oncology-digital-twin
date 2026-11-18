"""Supplementary Figure S2: model families and clinical tasks in AI research papers, by year.

Input : lit/tagged_records.csv.gz (literature/03_tag_records.py), through lit_data.focused_research()
Output: FIG_DIR/figS2_models_tasks.{pdf,png}

One heatmap drawn by panels_landscape.panel_heatmap (same numbers and look): rows are model
families (top block) and clinical tasks (bottom block), columns are years, the cell shows
the % of AI research papers that name the family or task. 2026 is partial (data to 24 Sep).
Run: python src/figures/figS2_models_tasks.py
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
config.use("literature")
import style
import lit_data as D
import panels_landscape as F3

W_MM, H_MM = 183.0, 86.0


def main():
    style.apply()
    plt.rcParams["savefig.bbox"] = "standard"   # keep the exact page size
    df = D.focused_research()
    fig = plt.figure(figsize=(W_MM * style.MM, H_MM * style.MM))
    # same axes size as panel c of panels_landscape (120.8 x 73.6 mm)
    x, top, w, h = 40.0, 10.0, 120.8, 73.6
    ax = fig.add_axes([x / W_MM, 1 - (top + h) / H_MM, w / W_MM, h / H_MM])
    F3.panel_heatmap(ax, fig, df)
    for ext in ("pdf", "png"):
        p = config.fig_path(f"figS2_models_tasks.{ext}")
        fig.savefig(p, dpi=400)
        print("written ->", p)


if __name__ == "__main__":
    main()
