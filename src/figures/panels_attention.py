"""Panels f and g of Figure 2 (AI attention per tumor class), used by fig2_knowledge.py.

Input : lit/entity_counts.csv (literature/05_entity_counts.py) and support_counts.csv
        (knowledge_bases/06_build_matrices.py)
Output: none (drawing functions)

  f  share of each class's papers (2015-2026) that name AI, with Wilson 95% CI, sorted;
     brain metastasis shown below a rule as a reference (not in the tumor scope).
  g  AI papers per class against genes linked in Open Targets (all evidence), log-log,
     labelled points, Spearman rho with a bootstrap 95% CI (5,000 resamples).
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import config
config.use("knowledge_bases", "literature")
import style
import lit_data as D
from entities import KEYS

BLUE, GREY = "#0072B2", "#999999"
NAME = {"GBM": "Glioblastoma", "Astrocytoma": "Astrocytoma (non-GBM)",
        "Oligodendroglioma": "Oligodendroglioma", "DMG_H3K27": "DMG, H3K27-altered",
        "Medulloblastoma": "Medulloblastoma", "Ependymoma": "Ependymoma", "ATRT": "ATRT",
        "PilocyticAstrocytoma": "Pilocytic astrocytoma", "Meningioma": "Meningioma",
        "Craniopharyngioma": "Craniopharyngioma", "BrainMetastasis": "Brain metastasis"}


def panel_share(ax, e, letter="a"):
    """Horizontal bars: share of each class's research papers that name AI, one number per
    bar (the share). Thin black lines give the Wilson 95% CI. Counts are in the caption."""
    tum = e[e.entity != "BrainMetastasis"].sort_values("ai_share")
    ref = e[e.entity == "BrainMetastasis"]
    rows = list(ref.itertuples()) + [None] + list(tum.itertuples())
    for y, r in enumerate(rows):
        if r is None:
            ax.axhline(y, color=style.INK_MUTED, lw=1.0, ls=(0, (2, 2)))
            continue
        p, lo, hi = D.wilson(r.papers_ai, r.papers_all)
        col = GREY if r.entity == "BrainMetastasis" else BLUE
        ax.barh(y, 100 * p, height=0.62, color=col, lw=0, zorder=2)
        ax.plot([100 * lo, 100 * hi], [y, y], color=style.INK, lw=1.0, zorder=3)
        ax.text(100 * hi + 0.2, y, f"{100 * p:.1f}%", va="center",
                fontsize=style.SMALL_PT, color=style.INK)
    ax.set_yticks([i for i, r in enumerate(rows) if r is not None])
    ax.set_yticklabels([NAME[r.entity] for r in rows if r is not None], fontsize=style.SMALL_PT)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlim(0, 8.5)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.set_xlabel("Research papers naming AI, 2015–2026")
    ax.set_title("AI share of papers by tumor class", loc="center", fontsize=style.SMALL_PT, pad=4)
    style.panel_label(ax, letter, dx=-0.62, dy=1.06)


def panel_scatter(ax, e, letter="b"):
    sup = pd.read_csv(config.inp("support_counts.csv"))
    ot = sup[(sup.kg == "OpenTargets") & (sup.tier == "all")].set_index("entity").genes
    d = e[e.entity.isin(KEYS)].copy()
    d["genes"] = d.entity.map(ot)
    ax.scatter(d.genes, d.papers_ai, s=18, color=BLUE, lw=0, zorder=3)
    nudge = {"Oligodendroglioma": (1.15, 0.80), "Ependymoma": (1.15, 1.18),
             "Astrocytoma": (1.15, 0.95), "Medulloblastoma": (1.15, 1.12), "ATRT": (1.15, 1.0),
             "PilocyticAstrocytoma": (1.15, 1.0), "DMG_H3K27": (1.15, 1.0),
             "Craniopharyngioma": (1.0, 1.55), "Meningioma": (1.15, 1.0), "GBM": (1.15, 1.0)}
    for r in d.itertuples():
        fx, fy = nudge.get(r.entity, (1.12, 1.0))
        label = {"DMG_H3K27": "DMG", "Astrocytoma": "Astrocytoma", "PilocyticAstrocytoma": "Pilocytic astro."}.get(r.entity, NAME[r.entity])
        ax.text(r.genes * fx, r.papers_ai * fy, label, fontsize=style.SMALL_PT,
                va="center", color=style.INK, linespacing=0.95,
                ha="center" if r.entity == "Craniopharyngioma" else "left")
    # with ten classes the estimate is weak: report p and a bootstrap interval
    from scipy.stats import spearmanr
    rho, p = spearmanr(d.genes, d.papers_ai)
    rng = np.random.default_rng(20260928)
    boots = []
    for _ in range(5000):
        i = rng.integers(0, len(d), len(d))
        if len(set(i)) > 2:
            boots.append(spearmanr(d.genes.values[i], d.papers_ai.values[i])[0])
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    print(f"  panel {letter}: rho = {rho:.3f} (95% CI {lo:.3f} to {hi:.3f}), P = {p:.3f}, n = {len(d)}")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(150, 100000); ax.set_ylim(5, 3000)
    style.plain_log_axis(ax.xaxis); style.plain_log_axis(ax.yaxis)
    ax.set_xlabel("Genes linked in Open Targets (all evidence)")
    ax.set_ylabel("AI papers, 2015–2026")
    ax.set_title("Knowledge and AI attention", loc="center", fontsize=style.SMALL_PT, pad=4)
    ax.text(0.03, 0.97, f"ρ = {rho:.2f} (95% CI {lo:.2f} to {hi:.2f})\nP = {p:.2f}, 10 classes",
            transform=ax.transAxes, ha="left", va="top", fontsize=style.SMALL_PT, color=style.INK_2,
            linespacing=1.15)
    style.panel_label(ax, letter, dx=-0.22, dy=1.06)
