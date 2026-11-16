"""Figure 5: from papers to patients. Three separate groups, each with its own unit.

Input : lit/tagged_records.csv.gz (literature/03_tag_records.py)
        trials/trial_share_by_start_year_screened.csv, audit/screening_summary.csv,
        audit/screening_final_devices.csv (screening/01_final_screening.py)
        trials/trial_summary.csv (trials/02_trial_metrics.py)
        devices/devices_tagged.csv (devices/01_fda_devices.py)
Output: FIG_DIR/fig5_translation.{pdf,png}; prints the panel titles (they hold the counts)

Not a funnel: papers, trials and devices are different groups, not nested stages.
  a  papers: % of AI research papers whose title, abstract or keywords report external
     validation or a prospective study in patients (flags X2, X3a); reader studies (X3b)
     are counted in the title. Sentences about future work are not counted. Wilson 95% bands.
  b  trials: human-screened AI trials on primary brain tumors as % of all primary brain
     tumor trials, by start year.
  c  devices: FDA AI-enabled devices per decision year (radiology, neurology and pathology
     panels, the 1,313 searched) and the human-screened ones indicated for primary brain
     tumors. Metastasis-only devices are not counted.
Run: python src/figures/fig5_translation.py
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
config.use("literature")
import style
import lit_data as D

BLUE, ORANGE, VIOLET, GREY = "#2a78d6", "#eb6834", "#4a3aa7", "#c9c8c2"
pct = FuncFormatter(lambda v, _: f"{v:g}%")


def panel_papers(ax, df):
    tot = df.groupby("year").size().reindex(D.YEARS)
    yrs = np.array(D.YEARS)
    for col, colr, lab in [("X2_external_validation", BLUE, "External\nvalidation"),
                           ("X3a_prospective_patients", ORANGE, "Prospective\nin patients")]:
        k = df.groupby("year")[col].sum().reindex(D.YEARS).fillna(0)
        p, lo, hi = D.wilson(k.values, tot.values)
        ax.fill_between(yrs, 100 * lo, 100 * hi, color=colr, alpha=0.12, lw=0)
        full = yrs < D.PARTIAL_YEAR
        ax.plot(yrs[full], 100 * p[full], color=colr, lw=1.1)
        ax.plot(yrs[-2:], 100 * p[-2:], color=colr, lw=1.1, ls=(0, (1, 1.5)))
        ax.scatter([yrs[-1]], [100 * p[-1]], s=10, facecolor=style.SURFACE, edgecolor=colr, lw=1.0)
        ax.text(D.PARTIAL_YEAR + 0.4, 100 * p[-1], f"{lab} ({int(k.sum()):,})",
                fontsize=style.SMALL_PT, va="center", color=style.INK, linespacing=0.95)
    ax.set_xlim(2014.5, D.PARTIAL_YEAR + 6.5)
    ax.spines["bottom"].set_bounds(2015, D.PARTIAL_YEAR)
    ax.set_xticks([2015, 2020, 2025])
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(pct)
    ax.set_ylabel("% of AI research papers")
    ax.set_title(f"Papers (n = {len(df):,}; {int(df.X3b_reader_study.sum())} name a reader study)",
                 loc="center", fontsize=style.SMALL_PT, pad=3)
    style.panel_label(ax, "a", dx=-0.30, dy=1.10)


def panel_trials(ax):
    by = pd.read_csv(config.inp("trials/trial_share_by_start_year_screened.csv"), dtype={"start_year": str})
    by = by[by.start_year.fillna("").str.fullmatch(r"\d{4}")].copy()
    by["start_year"] = by.start_year.astype(int)
    by = by.set_index("start_year")
    yrs = np.arange(2010, 2027)
    share = by.share_pct_screened.reindex(yrs).fillna(0)
    ax.bar(yrs, share, width=0.72, color=[BLUE if y < D.PARTIAL_YEAR else style.SURFACE for y in yrs],
           edgecolor=BLUE, linewidth=1.0)
    ax.set_xticks([2010, 2015, 2020, 2025])
    ax.yaxis.set_major_formatter(pct)
    ax.set_ylabel("% of primary brain tumor\ntrials using AI (screened)")
    sm = pd.read_csv(config.inp("trials/trial_summary.csv")).set_index("name").value
    sc = pd.read_csv(config.inp("audit/screening_summary.csv")).set_index("name").value
    ax.set_title(f"Trials ({int(sc['trials_included_final_corrected'])} of {int(sm['denominator_primary']):,}; "
                 f"{int(sc['trials_due_results_posted'])} of {int(sc['trials_due_results'])} due have posted results)",
                 loc="center", fontsize=style.SMALL_PT, pad=3)
    style.panel_label(ax, "b", dx=-0.30, dy=1.10)


def panel_devices(ax):
    t = pd.read_csv(config.inp("devices/devices_tagged.csv"))
    t["year"] = pd.to_datetime(t.decision_date, errors="coerce").dt.year
    yrs = np.arange(2014, 2027)
    allk = t.groupby("year").size().reindex(yrs).fillna(0)
    fin = pd.read_csv(config.inp("audit/screening_final_devices.csv"))
    keep = set(fin.loc[fin.final == 1, "submission"])        # human-screened primary brain tumor tools
    bt = t[t.submission.str.split("/").str[0].isin(keep)]
    btk = bt.groupby("year").size().reindex(yrs).fillna(0)
    part = yrs == D.PARTIAL_YEAR                      # 2026: list of 4 Sep, drawn hollow
    ax.bar(yrs[~part], allk[~part], width=0.72, color=GREY, lw=0,
           label="All radiology, neurology and\npathology AI devices")
    ax.bar(yrs[part], allk[part], width=0.72, color=style.SURFACE, edgecolor=GREY, lw=1.0)
    ax.bar(yrs[~part], btk[~part], width=0.72, color=BLUE, lw=0,
           label="Indicated for primary\nbrain tumors (screened)")
    ax.bar(yrs[part], btk[part], width=0.72, color=style.SURFACE, edgecolor=BLUE, lw=1.0)
    for y, n in zip(yrs, btk):
        if n:
            ax.text(y, n + 3, f"{int(n)}", ha="center", va="bottom", fontsize=style.SMALL_PT,
                    color=BLUE, fontweight="bold")
    ax.set_xticks([2015, 2020, 2025])
    ax.set_ylabel("Devices cleared per year")
    ax.set_ylim(0, allk.max() * 1.45)
    ax.legend(loc="upper left", fontsize=style.SMALL_PT, handlelength=1.0)
    ax.set_title(f"FDA devices ({len(bt)} of {len(t):,} searched)", loc="left",
                 fontsize=style.SMALL_PT, pad=3)
    style.panel_label(ax, "c", dx=-0.30, dy=1.10)


def main():
    style.apply()
    df = D.focused_research()
    fig, axs = plt.subplots(1, 3, figsize=(style.DOUBLE_COL, 2.5),
                            gridspec_kw=dict(wspace=0.75, left=0.08, right=0.985, top=0.82, bottom=0.14))
    panel_papers(axs[0], df)
    panel_trials(axs[1])
    panel_devices(axs[2])
    for ax in axs:
        print("  title:", ax.get_title(loc="center") or ax.get_title(loc="left"))
    for ext in ("pdf", "png"):
        p = config.fig_path(f"fig5_translation.{ext}")
        fig.savefig(p, dpi=400)
        print("written ->", p)


if __name__ == "__main__":
    main()
