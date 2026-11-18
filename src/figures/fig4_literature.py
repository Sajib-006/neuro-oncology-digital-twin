"""Figure 4: literature survey, AI share by data type and how rarely data types are combined.

Input : lit/counts_by_year_focused_research.csv and lit/tagged_records.csv.gz, through
        lit_data (same inputs as panels_landscape.py and panels_integration.py)
Output: FIG_DIR/fig4_literature.{pdf,png}; prints the numbers shown in panels b, d and e

The panels are drawn by the panel functions of the two older figure scripts, so the
numbers and the look are the same:
  a  AI share of papers per data type, by year     (panels_landscape.panel_lines)
  b  rarely named topics, one square per paper      (panels_landscape.panel_rare)
  c  data type x task, observed / expected          (panels_integration.panel_enrichment)
  d  share of papers naming >= 2 data types         (panels_integration.panel_share)
  e  which data-type pairs are named together       (panels_integration.panel_pairs)
Layout: a and b in the top row; c on the left of the bottom row, d above e on the right.
Run: python src/figures/fig4_literature.py
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
import panels_integration as F4

W_MM, H_MM = 183.0, 166.0


def axes_mm(fig, x, top, w, h):
    """Axes placed in mm: x from the left edge, top from the top edge."""
    return fig.add_axes([x / W_MM, 1 - (top + h) / H_MM, w / W_MM, h / H_MM])


def letter(fig, t, x, top):
    fig.text(x / W_MM, 1 - top / H_MM, t, fontsize=8, fontweight="bold",
             va="top", ha="left", color=style.INK)


def main():
    style.apply()
    plt.rcParams["savefig.bbox"] = "standard"   # keep the exact page size
    cnt = D.counts("focused_research")
    df = D.focused_research()
    fig = plt.figure(figsize=(W_MM * style.MM, H_MM * style.MM))

    # top row: same axes sizes as in panels_landscape (a 67.8 mm wide, b 42 mm, 53.6 mm tall)
    ax_a = axes_mm(fig, 15.6, 6.0, 67.8, 53.6); F3.panel_lines(ax_a, fig, cnt)
    ax_b = axes_mm(fig, 131.0, 6.0, 42.0, 53.6); F3.panel_rare(ax_b, df)

    # bottom row: c on the left, d above e on the right
    ax_c = axes_mm(fig, 25.0, 72.0, 62.0, 68.0); F4.panel_enrichment(ax_c, df, label=None)
    ax_d = axes_mm(fig, 122.0, 76.0, 54.0, 30.0); F4.panel_share(ax_d, df, label=None)
    ax_e = axes_mm(fig, 131.5, 120.0, 45.8, 34.0); F4.panel_pairs(ax_e, df, label=None)

    for t, x, top in [("a", 1.5, 1.5), ("b", 104.0, 1.5),
                      ("c", 1.5, 68.0), ("d", 104.0, 68.0), ("e", 104.0, 114.0)]:
        letter(fig, t, x, top)
    for ext in ("pdf", "png"):
        p = config.fig_path(f"fig4_literature.{ext}")
        fig.savefig(p, dpi=400)
        print("written ->", p)


if __name__ == "__main__":
    main()
