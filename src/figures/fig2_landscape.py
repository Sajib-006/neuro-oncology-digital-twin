"""Figure 2: how AI entered brain tumor research.

Input : lit/counts_by_year_focused_research.csv (literature/01_scopus_counts.py) and
        lit/tagged_records.csv.gz (literature/03_tag_records.py)
Output: FIG_DIR/fig2_landscape.{pdf,png}; prints the counts shown in panel b

  a  AI share of papers per data type, by year (Scopus counts, focused form, articles and
     conference papers). Lines start once a data type reaches 50 papers a year. A key
     column on the right shows each data type's icon and name, joined to its line end.
  b  rarely named topics, 2015-2026, as horizontal bars with counts.
  c  one heatmap: rows are model families (top block) and clinical tasks (bottom block),
     columns are years, the cell shows the % of AI research papers that name the family
     or task. ColorBrewer YlGnBu on a log scale.
Icons: Bioicons (see icons/CREDITS.txt). 2026 is partial (data to 24 Sep).
Run: python src/figures/fig2_landscape.py
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
config.use("literature")
import style
import lit_data as D

O = style.OKABE
MOD_COLOR = {"M1_neuroimaging": O["blue"], "M2_pathology": O["vermillion"], "M3_bulk_omics": O["green"],
             "M4_single_cell": O["orange"], "M5_spatial": O["purple"], "M6_clinical_text": O["sky"]}
MOD_ICON = {"M1_neuroimaging": "brain-1", "M2_pathology": "microscope", "M3_bulk_omics": "dna-1",
            "M4_single_cell": "sc_droplet", "M5_spatial": "glassslide-top", "M6_clinical_text": "notepad"}
ICON_DIR = os.path.join(HERE, "icons")
MIN_DENOM = 50
pct = FuncFormatter(lambda v, _: f"{v:g}%")


def icon(ax, name, xy, height_mm, fig, xycoords="axes fraction", width_mm=None):
    """Icon fitted inside a height_mm x width_mm box (same box for every icon)."""
    img = plt.imread(os.path.join(ICON_DIR, f"{name}_icon.png"))
    width_mm = width_mm or height_mm
    zoom = min(height_mm / img.shape[0], width_mm / img.shape[1]) / 25.4 * fig.dpi
    ab = AnnotationBbox(OffsetImage(img, zoom=zoom), xy, xycoords=xycoords, frameon=False,
                        box_alignment=(0.5, 0.5), annotation_clip=False)
    ax.add_artist(ab)


def panel_lines(ax, fig, cnt):
    ends = []
    for mk, lab in D.MOD_LABEL.items():
        gen, ai = cnt[f"{mk}_GEN"], cnt[f"{mk}_AI"]
        ok = gen >= MIN_DENOM
        if not ok.any():
            continue
        first = max(gen[ok].index.min(), 2015)
        yrs = np.array([y for y in gen.index if y >= first])
        sh = (100 * ai.loc[yrs] / gen.loc[yrs]).values
        col = MOD_COLOR[mk]
        full = yrs < D.PARTIAL_YEAR
        ax.plot(yrs[full], sh[full], color=col, lw=1.4, solid_capstyle="round", zorder=3)
        ax.plot(yrs[-2:], sh[-2:], color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=3)
        ax.scatter([yrs[-1]], [sh[-1]], s=14, facecolor="white", edgecolor=col, lw=1.2, zorder=4)
        ends.append((sh[-1], mk, lab, col))
    ax.set_xlim(2014.6, 2026.4)
    ax.set_xticks([2015, 2017, 2019, 2021, 2023, 2025])
    ax.set_ylim(0, 70)
    ax.yaxis.set_major_formatter(pct)
    ax.set_ylabel("Papers on the data type that name AI")
    ax.set_title("AI share by data type", loc="center", fontsize=style.SMALL_PT, pad=4)
    # key column outside the plot: icon + name, joined to the line end by a leader
    ends.sort(key=lambda e: -e[0])
    n = len(ends)
    ys = np.linspace(0.95, 0.10, n)
    for (v, mk, lab, col), yk in zip(ends, ys):
        ax.annotate("", xy=(2026, v), xycoords="data", xytext=(1.06, yk), textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-", color="#b5b5b5", lw=0.6, ls=(0, (1.5, 1.2)),
                                    shrinkA=0, shrinkB=3),
                    annotation_clip=False)
        icon(ax, MOD_ICON[mk], (1.105, yk), 3.6, fig, width_mm=4.6)
        ax.text(1.17, yk, lab.replace("Clinical text / EHR", "Clinical text"), transform=ax.transAxes,
                ha="left", va="center", fontsize=style.SMALL_PT, color=style.INK)


def panel_heatmap(ax, fig, df):
    years = D.YEARS
    tot = df.groupby("year").size().reindex(years)
    fams = [(k, v) for k, v in D.ARCH_LABEL.items() if k not in ("R7_agentic", "R8_KG")]
    tasks = list(D.TASK_LABEL.items())
    rows = [("Model family", None)] + fams + [("Clinical task", None)] + tasks
    M = np.full((len(rows), len(years)), np.nan)
    for i, (k, lab) in enumerate(rows):
        if lab is None:
            continue
        M[i] = (100 * df.groupby("year")[k].sum().reindex(years).fillna(0) / tot).values
    norm = LogNorm(vmin=0.1, vmax=80)
    cmap = style.CMAP_SEQ.copy(); cmap.set_bad("white")
    shown = np.where(M > 0, np.clip(M, 0.1, 80), np.nan)
    im = ax.imshow(np.ma.masked_invalid(shown), cmap=cmap, norm=norm, aspect="auto",
                   extent=(0, len(years), len(rows), 0), interpolation="nearest")
    for i, (k, lab) in enumerate(rows):
        if lab is None:
            ax.text(-0.15, i + 0.62, k, ha="right", va="center", fontsize=style.SMALL_PT,
                    fontweight="bold", color=style.INK)
            continue
        for j in range(len(years)):
            v = M[i, j]
            if np.isnan(v):
                continue
            txt = "0" if v == 0 else (f"{v:.1f}" if v < 99.95 else "100")
            dark = v > 0 and norm(np.clip(v, 0.1, 80)) > 0.62
            ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=style.SMALL_PT,
                    color="white" if dark else style.INK)
    for i in range(len(rows) + 1):
        ax.axhline(i, color="white", lw=1.2)
    for j in range(len(years) + 1):
        ax.axvline(j, color="white", lw=1.2)
    ax.set_xticks(np.arange(len(years)) + 0.5)
    ax.set_xticklabels([f"{y}*" if y == D.PARTIAL_YEAR else str(y) for y in years])
    ax.xaxis.set_ticks_position("top"); ax.xaxis.set_label_position("top")
    ax.set_yticks([i + 0.5 for i, (k, lab) in enumerate(rows) if lab is not None])
    ax.set_yticklabels([lab for k, lab in rows if lab is not None])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlim(0, len(years)); ax.set_ylim(len(rows), 0)
    cax = ax.inset_axes([1.015, 0.15, 0.012, 0.7])
    cb = fig.colorbar(im, cax=cax)
    cb.set_ticks([0.1, 1, 10, 50]); cb.set_ticklabels(["0.1%", "1%", "10%", "50%"])
    cb.minorticks_off(); cb.outline.set_linewidth(0.8); cb.outline.set_edgecolor(style.INK_MUTED)
    cax.tick_params(labelsize=style.SMALL_PT, length=2)
    cb.set_label("AI research papers naming it", fontsize=style.SMALL_PT)
    ax.set_title("Model families and clinical tasks in AI research papers, by year",
                 loc="center", fontsize=style.SMALL_PT, pad=14)


def panel_rare(ax, df):
    rare = [("R7_agentic", "Agentic AI"), ("R8_KG", "Knowledge graphs"),
            ("X4_regulatory", "Regulatory clearance"), ("X9_digital_twin", "Digital twin")]
    vals = [int(df[c].sum()) for c, _ in rare]
    print("  panel b:", ", ".join(f"{l} {v}" for (_, l), v in zip(rare, vals)), f"(of {len(df):,})")
    y = np.arange(len(rare))
    ax.barh(y, vals, height=0.58, color=O["blue"], lw=0)
    for yi, v in zip(y, vals):
        ax.text(v + 0.3, yi, str(v), va="center", fontsize=style.SMALL_PT, color=style.INK)
    ax.set_yticks(y); ax.set_yticklabels([l for _, l in rare])
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, max(vals) * 1.3)
    ax.set_xlabel(f"Papers, 2015–2026 (of {len(df):,})")
    ax.set_title("Rarely named topics", loc="center", fontsize=style.SMALL_PT, pad=4)


def main():
    style.apply()
    cnt = D.counts("focused_research")
    df = D.focused_research()
    fig = plt.figure(figsize=(style.DOUBLE_COL, 6.3))
    top = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.62], wspace=0.95,
                           left=0.085, right=0.97, top=0.955, bottom=0.62)
    ax_a = fig.add_subplot(top[0]); panel_lines(ax_a, fig, cnt)
    ax_c = fig.add_subplot(top[1]); panel_rare(ax_c, df)
    ax_b = fig.add_axes([0.235, 0.035, 0.66, 0.46]); panel_heatmap(ax_b, fig, df)

    def letter(t, x, y):
        fig.text(x, y, t, fontsize=8, fontweight="bold", va="top", ha="left", color=style.INK)
    letter("a", 0.012, 0.99); letter("c", 0.012, 0.555)
    letter("b", ax_c.get_position().x0 - 0.17, 0.99)
    for ext in ("pdf", "png"):
        p = config.fig_path(f"fig2_landscape.{ext}")
        fig.savefig(p, dpi=400)
        print("written ->", p)


if __name__ == "__main__":
    main()
