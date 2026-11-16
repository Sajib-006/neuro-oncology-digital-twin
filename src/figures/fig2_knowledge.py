"""Figure 2: knowledge and AI research both concentrate on a few common tumors.

Input : support_counts.csv, similarity_long.csv, null_similarity/, similarity_robust/
        (src/knowledge_bases/), lit/entity_counts.csv (src/literature/05_entity_counts.py)
Output: FIG_DIR/fig2_knowledge.{pdf,png}; prints the correlations shown in panels c-e and g

  row 1  a coverage matrix; b evidence-level bars           (knowledge is uneven)
  row 2  c-e similarity vs size: Jaccard, cosine, null      (so similarity tracks coverage)
  row 3  f AI share per tumor; g AI papers vs genes          (and AI attention follows it)
Okabe-Ito resource colors, ColorBrewer YlGnBu heatmap, plain tick labels on log axes,
one shared key for row 2, panel letters on one grid.
Run: python src/figures/fig2_knowledge.py
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
config.use("knowledge_bases")
import style
import panels_knowledge as F1
import panels_attention as F4
from entities import MIN_SUPPORT


def main():
    style.apply()
    style.panel_label = lambda *a, **k: None          # letters placed on one grid below
    sup = pd.read_csv(config.inp("support_counts.csv"))
    sim = pd.read_csv(config.inp("similarity_long.csv"))
    ent = pd.read_csv(config.inp("lit/entity_counts.csv"))
    pairs = F1.pair_table(sup, sim)

    fig = plt.figure(figsize=(style.DOUBLE_COL, 8.0))
    top = fig.add_gridspec(1, 2, width_ratios=[1.5, 1.0], wspace=0.62,
                           left=0.17, right=0.97, top=0.935, bottom=0.66)
    mid = fig.add_gridspec(1, 3, wspace=0.45, left=0.085, right=0.97, top=0.535, bottom=0.36)
    bot = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=0.42,
                           left=0.17, right=0.97, top=0.255, bottom=0.05)

    ax_a = fig.add_subplot(top[0]); im = F1.panel_matrix(ax_a, sup, "a")
    ax_a.set_title("Genes per tumor class", loc="center", fontsize=style.SMALL_PT, pad=20)
    cax = ax_a.inset_axes([1.03, 0.0, 0.03, 1.0])
    cb = fig.colorbar(im, cax=cax)
    ticks = [k for k in range(1, 6) if np.log10(MIN_SUPPORT) <= k <= im.norm.vmax + 1e-9]
    cb.set_ticks(ticks); cb.set_ticklabels([f"{10 ** k:,}" for k in ticks])
    cb.outline.set_linewidth(1.0); cb.outline.set_edgecolor(style.INK_MUTED)
    cax.tick_params(labelsize=style.SMALL_PT, width=1.0, length=3)
    fig.legend(handles=[Patch(facecolor=style.NODATA, edgecolor=style.NODATA_HATCH, hatch="//",
                              linewidth=1.0, label=f"< {MIN_SUPPORT} genes")],
               loc="upper left", bbox_to_anchor=(0.535, 0.652), fontsize=style.SMALL_PT,
               handlelength=1.4, frameon=False)
    ax_b = fig.add_subplot(top[1]); F1.panel_tier(ax_b, sup, "b")

    ax_c = fig.add_subplot(mid[0])
    F1.panel_confound(ax_c, pairs, "jaccard", "Jaccard similarity", "c", title="Gene overlap")
    ax_d = fig.add_subplot(mid[1])
    F1.panel_confound(ax_d, pairs, "cosine", "Cosine similarity", "d", title="Score similarity")
    ax_e = fig.add_subplot(mid[2])
    F1.panel_confound(ax_e, pairs, "curveball", "log2(observed / expected)", "e",
                      title="Chance-corrected overlap")
    keys = [Line2D([], [], marker="o", ls="", color=style.KG_COLOR[k], markersize=4,
                   label=style.KG_LABEL[k]) for k in F1.KGS if (pairs.kg == k).any()]   # only resources with points
    keys += [Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=style.INK_2,
                    markersize=4, label="Curated level"),
             Line2D([], [], marker="o", ls="", color=style.INK_2, markersize=4, label="All evidence")]
    fig.legend(handles=keys, loc="center", bbox_to_anchor=(0.53, 0.585), ncol=5,
               fontsize=style.SMALL_PT, frameon=False, handletextpad=0.3, columnspacing=1.6)

    ax_f = fig.add_subplot(bot[0]); F4.panel_share(ax_f, ent, "f")
    ax_g = fig.add_subplot(bot[1]); F4.panel_scatter(ax_g, ent, "g")

    # ---- panel letters on one grid: same x per column, same y per row (8 pt bold)
    def letter(t, x, y):
        fig.text(x, y, t, fontsize=8, fontweight="bold", va="top", ha="left", color=style.INK)
    xl = 0.012
    xr = ax_b.get_position().x0 - 0.075
    row1, row2, row3 = 0.985, 0.565 + 0.0, 0.295
    letter("a", xl, row1); letter("b", xr, row1)
    letter("c", xl, row2); letter("d", ax_d.get_position().x0 - 0.065, row2)
    letter("e", ax_e.get_position().x0 - 0.065, row2)
    letter("f", xl, row3); letter("g", xr, row3)

    for ext in ("pdf", "png"):
        p = config.fig_path(f"fig2_knowledge.{ext}")
        fig.savefig(p, dpi=400)
        print("written ->", p)


if __name__ == "__main__":
    main()
