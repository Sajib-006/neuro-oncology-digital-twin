"""Panels a-e of Figure 2 (knowledge-base coverage), used by fig2_knowledge.py.

Input : support_counts.csv, similarity_long.csv (knowledge_bases/06, 07),
        similarity_robust/pairs_<kb>_<level>.csv (knowledge_bases/10),
        null_similarity/gene_<kb>_<level>_log2oe.csv (knowledge_bases/09)
Output: none (drawing functions)

  a  coverage matrix: genes per class, for each knowledge base x evidence level;
     cells below MIN_SUPPORT hatched grey
  b  total gene-tumor links per knowledge base at each evidence level
  c-e  pair similarity against the smaller gene list's size, for three measures:
     Jaccard, cosine and the chance-corrected log2(observed/expected)
Colors: gene counts are a magnitude (sequential ramp, log scale); knowledge bases are
identities (fixed categorical colors); below-support cells are neutral grey + hatch.
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
config.use("knowledge_bases")
import style
from entities import KEYS, MIN_SUPPORT

KGS = ["OpenTargets", "DisGeNET", "CTD"]
TIERS = ["curated", "all"]
TESTED = [("OpenTargets", "curated"), ("OpenTargets", "all"),
          ("CTD", "all")]                                # >= 6 measurable entities
# DisGeNET: v7.0 curated only (the all-evidence file is no longer openly available)
COLS = [("OpenTargets", "curated"), ("OpenTargets", "all"), ("DisGeNET", "curated"),
        ("CTD", "curated"), ("CTD", "all")]

ROWLAB = {
    "GBM": "Glioblastoma", "Astrocytoma": "Astrocytoma (non-GBM)",
    "Oligodendroglioma": "Oligodendroglioma", "DMG_H3K27": "DMG, H3K27-altered",
    "Medulloblastoma": "Medulloblastoma", "Ependymoma": "Ependymoma",
    "ATRT": "ATRT", "PilocyticAstrocytoma": "Pilocytic astrocytoma",
    "Meningioma": "Meningioma", "Craniopharyngioma": "Craniopharyngioma",
}


def panel_matrix(ax, sup, letter="a"):
    cols = COLS
    M = np.array([[int(sup[(sup.kg == kg) & (sup.tier == t) & (sup.entity == e)]["genes"].sum())
                   for (kg, t) in cols] for e in KEYS], dtype=float)
    n_r, n_c = M.shape
    # log10 applied here rather than via LogNorm: the server's matplotlib 3.3 LogNorm
    # colourbar path calls np.Inf, which NumPy 2 removed.
    lo, hi = np.log10(MIN_SUPPORT), np.log10(max(M.max(), MIN_SUPPORT * 10))
    norm = Normalize(vmin=lo, vmax=hi)
    shown = np.where(M >= MIN_SUPPORT, np.log10(np.maximum(M, 1)), np.nan)
    im = ax.imshow(np.ma.masked_invalid(shown), cmap=style.CMAP_SEQ, norm=norm,
                   extent=(0, n_c, n_r, 0), interpolation="nearest", aspect="auto", zorder=2)
    for i in range(n_r):
        for j in range(n_c):
            v = M[i, j]
            if v < MIN_SUPPORT:
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=style.NODATA,
                                       edgecolor=style.NODATA_HATCH, hatch="////",
                                       linewidth=0, zorder=3))
                ink = style.INK_2
            else:
                ink = style.SURFACE if norm(np.log10(v)) > 0.55 else style.INK
            ax.text(j + 0.5, i + 0.5, f"{int(v):,}", ha="center", va="center",
                    fontsize=style.SMALL_PT, color=ink, zorder=5)
    for k in range(n_r + 1):
        ax.axhline(k, color=style.SURFACE, lw=1.0, zorder=4)
    bounds = [j for j in range(1, n_c) if cols[j][0] != cols[j - 1][0]]
    for k in range(n_c + 1):
        ax.axvline(k, color=style.SURFACE, lw=2.4 if k in bounds else 0.8, zorder=4)
    ax.set_xticks(np.arange(n_c) + 0.5)
    ax.set_xticklabels([t.capitalize() for (_, t) in cols], fontsize=style.SMALL_PT)
    for kg in KGS:
        js = [j for j, (k2, _) in enumerate(cols) if k2 == kg]
        ax.text(np.mean(js) + 0.5, -0.55, style.KG_LABEL[kg], ha="center", va="bottom",
                fontsize=style.SMALL_PT, color=style.INK, fontweight="bold")
        ax.plot([min(js) + 0.08, max(js) + 0.92], [-0.22, -0.22], color=style.KG_COLOR[kg],
                lw=2.5, solid_capstyle="butt", clip_on=False)
    ax.set_yticks(np.arange(n_r) + 0.5)
    ax.set_yticklabels([ROWLAB[e] for e in KEYS], fontsize=style.SMALL_PT)
    ax.tick_params(length=0)
    ax.set_xlim(0, n_c); ax.set_ylim(n_r, 0)
    for s in ax.spines.values():
        s.set_visible(False)
    style.panel_label(ax, letter, dx=-0.42, dy=1.10)
    return im


def panel_tier(ax, sup, letter="b"):
    """b - grouped bars: total gene-tumor links per resource at each evidence level.
    Open bar = curated only, filled bar = all evidence (same encoding as open/filled
    points in c-e). Fold change printed above each pair."""
    tot = sup.groupby(["kg", "tier"])["genes"].sum().unstack().reindex(KGS)
    x = np.arange(len(KGS))
    w = 0.34
    for i, kg in enumerate(KGS):
        c = tot.loc[kg, "curated"]
        a = tot.loc[kg, "all"] if "all" in tot.columns else np.nan
        col = style.KG_COLOR[kg]
        ax.bar(i - w / 2, c, w, facecolor=style.SURFACE, edgecolor=col, linewidth=1.0, zorder=3)
        if np.isfinite(a) and a > 0:
            ax.bar(i + w / 2, a, w, facecolor=col, edgecolor=col, linewidth=1.0, zorder=3)
            # per-bar counts dropped: at 7 pt they collide; panel a shows the counts
            print(f"  panel {letter}: {kg} all / curated links = {a:,.0f} / {c:,.0f} = {a / c:.1f}-fold")
            ax.text(i, a * 1.6, f"×{a / c:,.0f}", ha="center", va="bottom",
                    fontsize=style.BASE_PT, color=style.INK, fontweight="bold")
        else:
            ax.text(i + w / 2, c * 1.6, "curated\nonly", ha="center", va="bottom",
                    fontsize=style.SMALL_PT, color=style.INK_2, linespacing=0.95)
    ax.set_yscale("log")
    ax.set_ylim(30, 3e6)
    ax.set_yticks([1e2, 1e3, 1e4, 1e5, 1e6])
    style.plain_log_axis(ax.yaxis)
    ax.set_title("Links by evidence level", loc="center", fontsize=style.SMALL_PT, pad=4)
    ax.set_xticks(x)
    ax.set_xticklabels([style.KG_LABEL[k] for k in KGS])
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("Gene–tumor links (all classes)")
    ax.legend(handles=[Patch(facecolor=style.SURFACE, edgecolor=style.INK_2, lw=1.0, label="Curated only"),
                       Patch(facecolor=style.INK_2, edgecolor=style.INK_2, lw=1.0, label="All evidence")],
              loc="upper left", ncol=2, handlelength=1.0, handletextpad=0.4, borderpad=0.1,
              columnspacing=1.0, fontsize=style.SMALL_PT)
    style.panel_label(ax, letter, dx=-0.30, dy=1.10)


def pair_table(sup, sim_long):
    rows = []
    for kg, tier in TESTED:
        n = {r.entity: r.genes for r in sup[(sup.kg == kg) & (sup.tier == tier)].itertuples()}
        null = pd.read_csv(config.inp(f"null_similarity/gene_{kg}_{tier}_log2oe.csv"), index_col=0)
        rob = pd.read_csv(config.inp(f"similarity_robust/pairs_{kg}_{tier}.csv"))
        cb = {(r.entity_1, r.entity_2): r.curveball_log2oe for r in rob.itertuples()}
        cb.update({(b_, a_): v for (a_, b_), v in list(cb.items())})
        s = sim_long[(sim_long.kg == kg) & (sim_long.tier == tier)]
        for i, a in enumerate(KEYS):
            for b in KEYS[i + 1:]:
                if n.get(a, 0) < MIN_SUPPORT or n.get(b, 0) < MIN_SUPPORT:
                    continue
                g = lambda m: s[(s.metric == m) & (s.entity_1 == a) & (s.entity_2 == b)]["similarity"].iloc[0]
                rows.append(dict(kg=kg, tier=tier, minsize=min(n[a], n[b]),
                                 jaccard=g("jaccard"), cosine=g("cosine"),
                                 null=null.loc[a, b], curveball=cb.get((a, b), np.nan)))
    return pd.DataFrame(rows)


def panel_confound(ax, d, col, ylabel, letter, show_legend=False, title=None):
    for kg in KGS:
        sub = d[d.kg == kg]
        if sub.empty:
            continue
        mk = {"curated": "o", "all": "o"}
        for tier in TIERS:
            s2 = sub[sub.tier == tier]
            if s2.empty:
                continue
            ax.scatter(s2.minsize, s2[col], s=11, marker="o",
                       facecolor=style.KG_COLOR[kg] if tier == "all" else style.SURFACE,
                       edgecolor=style.KG_COLOR[kg], linewidth=1.0, alpha=0.9, zorder=3)
    # one rho per resource and level, never pooled: a pooled value mixes resources whose
    # sizes differ by orders of magnitude and can look like a pass when no setting passes
    rhos = [g[col].corr(np.log10(g.minsize), method="spearman")
            for _, g in d.groupby(["kg", "tier"]) if g[col].notna().sum() >= 3]
    ax.set_xscale("log")
    ax.set_xlabel("Genes linked to the smaller tumor")
    ax.set_ylabel(ylabel)
    if col in ("null", "curveball"):
        ax.axhline(0, color=style.INK_MUTED, lw=1.0, ls=(0, (3, 2)), zorder=1)
    # rho in the title: inside the plot it collides with the densest points
    ax.set_title(title or ylabel, loc="center", fontsize=style.SMALL_PT, color=style.INK, pad=4)
    print(f"  panel {letter} ({col}): rho = {min(rhos):.3f} to {max(rhos):.3f}")
    ax.text(0.97, 0.04, f"ρ = {min(rhos):.2f} to {max(rhos):.2f}", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=style.SMALL_PT, color=style.INK_2)
    style.plain_log_axis(ax.xaxis)
    if show_legend:
        h = [Line2D([], [], marker="o", ls="", color=style.KG_COLOR[k], markersize=3.5, label=k) for k in KGS]
        h += [Line2D([], [], marker="o", ls="", markerfacecolor=style.SURFACE,
                     markeredgecolor=style.INK_2, markersize=3.5, label="Curated level")]
        ax.legend(handles=h, loc="upper left", fontsize=style.SMALL_PT,
                  handletextpad=0.2, borderpad=0.1, labelspacing=0.25)
    style.panel_label(ax, letter, dx=-0.28, dy=1.12)
