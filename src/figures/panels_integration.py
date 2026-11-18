"""Panels for Figure 4 (c to e): few AI studies combine data types.

Input : lit/tagged_records.csv.gz (literature/03_tag_records.py), through lit_data.focused_research()
Output: FIG_DIR/panels_integration.{pdf,png}; prints the numbers shown in panels b and c

  a  data type x task: log2(observed / expected) co-occurrence in AI research papers
     2015-2026, expected = row total x column total / N. Counts printed in cells; cells
     with < 5 papers are hatched. A bold count marks a cell whose exact Poisson 95%
     interval for the observed count excludes the expected count.
  b  share of papers naming >= 2 data types, per year, with Wilson 95% bands: strict
     (title/keywords or >= 2 abstract mentions) and lenient (any mention). The word
     "multimodal" is NOT used to measure this.
  c  which data-type pairs are named together (strict), pooled 2015-2026.
Run: python src/figures/panels_integration.py
"""
import os, sys, itertools
import numpy as np
from scipy.stats import chi2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
config.use("literature")
import style
import lit_data as D

BLUE = "#2a78d6"
MIN_CELL = 5
MODS = list(D.MOD_LABEL)
TASKS = list(D.TASK_LABEL)
# short names for panel c, where two names share one label
SHORT = {"M1_neuroimaging": "Imaging", "M2_pathology": "Pathology", "M3_bulk_omics": "Bulk omics",
         "M4_single_cell": "Single-cell", "M5_spatial": "Spatial", "M6_clinical_text": "Clinical text"}


def panel_enrichment(ax, df, label="a"):
    N = len(df)
    O = np.array([[((df[f"{m}_used"] == 1) & (df[t] == 1)).sum() for t in TASKS] for m in MODS], float)
    rows = np.array([(df[f"{m}_used"] == 1).sum() for m in MODS], float)
    cols = np.array([(df[t] == 1).sum() for t in TASKS], float)
    E = np.outer(rows, cols) / N
    L = np.where(O >= MIN_CELL, np.log2(np.maximum(O, 0.5) / np.maximum(E, 1e-9)), np.nan)
    lim = 2.0
    im = ax.imshow(np.ma.masked_invalid(np.clip(L, -lim, lim)), cmap=style.CMAP_DIV,
                   vmin=-lim, vmax=lim, aspect="auto", extent=(0, len(TASKS), len(MODS), 0))
    for i in range(len(MODS)):
        for j in range(len(TASKS)):
            if np.isnan(L[i, j]):
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=style.NODATA,
                                       edgecolor=style.NODATA_HATCH, hatch="////", lw=0))
                txt, ink = f"{int(O[i, j])}", style.INK_2
                bold = False
            else:
                txt = f"{int(O[i, j]):,}"
                ink = style.SURFACE if abs(L[i, j]) > 1.2 else style.INK
                o = O[i, j]
                lo = chi2.ppf(0.025, 2 * o) / 2 if o > 0 else 0.0
                hi = chi2.ppf(0.975, 2 * (o + 1)) / 2
                bold = not (lo <= E[i, j] <= hi)
            ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center",
                    fontsize=style.SMALL_PT, color=ink, fontweight="bold" if bold else "normal")
    for k in range(len(MODS) + 1):
        ax.axhline(k, color=style.SURFACE, lw=1.0)
    for k in range(len(TASKS) + 1):
        ax.axvline(k, color=style.SURFACE, lw=1.0)
    ax.set_xticks(np.arange(len(TASKS)) + 0.5)
    ax.set_xticklabels([D.TASK_LABEL[t] for t in TASKS], rotation=35, ha="right",
                       fontsize=style.SMALL_PT)
    ax.set_yticks(np.arange(len(MODS)) + 0.5)
    ax.set_yticklabels([f"{D.MOD_LABEL[m]} ({int(r):,})" for m, r in zip(MODS, rows)],
                       fontsize=style.SMALL_PT)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cax = ax.inset_axes([1.03, 0.0, 0.035, 1.0])
    cb = plt.colorbar(im, cax=cax)
    cb.set_ticks([-2, -1, 0, 1, 2])
    cb.set_ticklabels(["¼×", "½×", "1×", "2×", "4×"])
    cb.set_label("Observed / expected", fontsize=style.SMALL_PT)
    cb.outline.set_linewidth(1.0)
    cax.tick_params(labelsize=style.SMALL_PT, length=2, width=0.4)
    if label:  # None when another figure places the letters
        style.panel_label(ax, label, dx=-0.62, dy=1.08)


def panel_share(ax, df, label="b"):
    tot = df.groupby("year").size().reindex(D.YEARS)
    mcols = [f"{m}_mention" for m in MODS]
    lenient = (df[mcols].sum(axis=1) >= 2).groupby(df.year).sum().reindex(D.YEARS)
    strict = df.groupby("year")["multimodal_used"].sum().reindex(D.YEARS)
    for k, ls, lab in [(strict, "-", "≥ 2 data types named (main measure)"),
                       (lenient, (0, (3, 2)), "≥ 2 data types mentioned")]:
        p, lo, hi = D.wilson(k.values, tot.values)
        yrs = np.array(D.YEARS)
        ax.fill_between(yrs, 100 * lo, 100 * hi, color=BLUE, alpha=0.13 if ls == "-" else 0.07,
                        lw=0, zorder=1)
        full = yrs < D.PARTIAL_YEAR
        ax.plot(yrs[full], 100 * p[full], color=BLUE, lw=1.1, ls=ls, zorder=3, label=lab)
        ax.plot(yrs[-2:], 100 * p[-2:], color=BLUE, lw=1.1, ls=(0, (1, 1.5)), zorder=3)
        ax.scatter([yrs[-1]], [100 * p[-1]], s=10, facecolor=style.SURFACE, edgecolor=BLUE,
                   lw=1.0, zorder=4)
    ax.set_ylim(0, None)
    ax.set_xticks([2015, 2018, 2021, 2024, 2026])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.set_ylabel("% of papers")
    ax.legend(loc="upper left", fontsize=style.SMALL_PT, handlelength=2.2)
    p_all = 100 * df.multimodal_used.mean()
    print(f"  panel b: overall {p_all:.2f}% ({int(df.multimodal_used.sum()):,} of {len(df):,}); "
          f"lenient total {int(lenient.sum()):,}")
    ax.set_title(f"Overall {p_all:.1f}% ({int(df.multimodal_used.sum()):,} of {len(df):,})",
                 loc="center", fontsize=style.SMALL_PT, pad=3)
    if label:  # None when another figure places the letters
        style.panel_label(ax, label, dx=-0.30, dy=1.10)


def panel_pairs(ax, df, label="c"):
    pairs = []
    for a, b in itertools.combinations(MODS, 2):
        n = int(((df[f"{a}_used"] == 1) & (df[f"{b}_used"] == 1)).sum())
        if n:
            pairs.append((n, f"{SHORT[a]} + {SHORT[b]}"))
    pairs = sorted(pairs)[-8:]
    print("  panel c:", "; ".join(f"{lab} {n}" for n, lab in reversed(pairs)))
    y = np.arange(len(pairs))
    ax.barh(y, [n for n, _ in pairs], height=0.62, color=BLUE, lw=0)
    for yi, (n, _) in zip(y, pairs):
        ax.text(n + 1.5, yi, f"{n}", va="center", fontsize=style.SMALL_PT, color=style.INK)
    ax.set_yticks(y)
    ax.set_yticklabels([lab for _, lab in pairs], fontsize=style.SMALL_PT)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Papers naming both, 2015–2026")
    ax.set_xlim(0, max(n for n, _ in pairs) * 1.18)
    if label:  # None when another figure places the letters
        style.panel_label(ax, label, dx=-0.40, dy=1.10)


def main():
    style.apply()
    df = D.focused_research()

    fig = plt.figure(figsize=(style.DOUBLE_COL, 5.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1.0], height_ratios=[1, 1],
                          hspace=0.6, wspace=0.85, left=0.15, right=0.97, top=0.92, bottom=0.12)
    panel_enrichment(fig.add_subplot(gs[:, 0]), df)
    panel_share(fig.add_subplot(gs[0, 1]), df)
    panel_pairs(fig.add_subplot(gs[1, 1]), df)
    for ext in ("pdf", "png"):
        p = config.fig_path(f"panels_integration.{ext}")
        fig.savefig(p, dpi=400)
        print("written ->", p)


if __name__ == "__main__":
    main()
