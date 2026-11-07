"""Shared figure style for all paper figures (sizes, fonts, colors, helpers).

Input : none (Arial .ttf files are read from FONT_DIR, default src/figures/fonts/)
Output: none (helper module)

Print figures: 89 mm single column, 183 mm double column, sans-serif, 7 pt text,
vector output.

Colour roles follow the dataviz method - the job picks the ramp:
  similarity, Jaccard (0..1, no midpoint)  -> SEQUENTIAL, one hue light->dark
  similarity, cosine  (-1..1, real zero)   -> DIVERGING, two hues + neutral grey
  knowledge graph identity (3 series)      -> CATEGORICAL, fixed slot order
  cells with too little data               -> neutral grey + hatch, on NEITHER ramp

The categorical trio was validated with the dataviz validator, light surface,
--pairs all: CVD dE 9.2, normal-vision dE 24.0, all checks pass. Aqua sits at
2.74:1 contrast, so bars using it carry printed value labels (the relief rule).
"""
from matplotlib.colors import LinearSegmentedColormap
import os
import matplotlib as mpl
from matplotlib import font_manager

MM = 1 / 25.4
SINGLE_COL = 89 * MM      # inches
DOUBLE_COL = 183 * MM

# --- categorical: knowledge graph identity, fixed order, never cycled ---
# Okabe-Ito (colour-blind safe, standard in journals); one meaning per colour, paper-wide
OKABE = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "sky": "#56B4E9",
         "vermillion": "#D55E00", "purple": "#CC79A7", "yellow": "#F0E442", "grey": "#999999"}
KG_COLOR = {
    "OpenTargets": OKABE["blue"],
    "DisGeNET":    OKABE["orange"],
    "CTD":         OKABE["green"],
}
KG_LABEL = {"OpenTargets": "Open Targets", "DisGeNET": "DisGeNET", "CTD": "CTD"}

# --- sequential: single hue, light -> dark (blue ramp steps 100..700) ---
SEQ_STEPS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# standard ColorBrewer YlGnBu, light end trimmed so the lowest cells are not white
import matplotlib.pyplot as _plt
import numpy as _np
CMAP_SEQ = LinearSegmentedColormap.from_list("ylgnbu_trim", _plt.get_cmap("YlGnBu")(_np.linspace(0.12, 1.0, 256)))

# --- diverging: blue <-> red with a NEUTRAL GREY midpoint (never a hue at zero) ---
CMAP_DIV = LinearSegmentedColormap.from_list(
    "div_blue_red",
    ["#0d366b", "#256abf", "#86b6ef", "#f0efec", "#f0a0a0", "#d03b3b", "#8f1f1f"],
)

# --- ink ---
SURFACE = "#ffffff"          # plain white (journal figures)
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8a84"
NODATA = "#e4e3df"        # grey, deliberately off both ramps
NODATA_HATCH = "#b9b8b2"

BASE_PT = 7                 # 7 pt text, 8 pt bold panel letters
SMALL_PT = 7                # one text size in all figures (7 pt)


FONT_DIR = os.environ.get("FONT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
FALLBACK_FONTS = ["Liberation Sans", "Helvetica", "DejaVu Sans"]


def _register_fonts():
    """Register Arial from FONT_DIR (Arial.ttf, Arial Bold.ttf, Arial Italic.ttf) or the
    system fonts. If Arial is unavailable, a metric-similar font is used and a warning
    is printed; data values are unaffected."""
    if os.path.isdir(FONT_DIR):
        for f in os.listdir(FONT_DIR):
            if f.lower().endswith(".ttf"):
                font_manager.fontManager.addfont(os.path.join(FONT_DIR, f))
    names = {f.name for f in font_manager.fontManager.ttflist}
    if "Arial" in names:
        return "Arial"
    family = next((n for n in FALLBACK_FONTS if n in names), "DejaVu Sans")
    print(f"WARNING: Arial not found (FONT_DIR={FONT_DIR}); using {family}. "
          "Figures will differ slightly in text layout.")
    return family


def apply():
    family = _register_fonts()
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [family],
        "mathtext.fontset": "custom",       # math text (10^4, log_2) in the same font
        "mathtext.rm": family,
        "mathtext.it": f"{family}:italic",
        "mathtext.bf": f"{family}:bold",
        "mathtext.default": "regular",
        "font.size": BASE_PT,
        "axes.labelsize": BASE_PT,
        "axes.titlesize": BASE_PT,
        "xtick.labelsize": SMALL_PT,
        "ytick.labelsize": SMALL_PT,
        "legend.fontsize": SMALL_PT,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK_MUTED,      # recessive axes
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "axes.linewidth": 1.0,          # journal rule: thinnest line >= 1 pt
        "xtick.major.width": 1.0,
        "ytick.major.width": 1.0,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.titlepad": 6,
        "hatch.linewidth": 1.0,
        "lines.linewidth": 1.2,
        "xtick.minor.width": 1.0,
        "ytick.minor.width": 1.0,
        "legend.frameon": False,
        "pdf.fonttype": 42,               # embed as TrueType, editable text
        "ps.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    })


def panel_label(ax, letter, dx=-0.16, dy=1.06):
    """Bold lowercase panel letter, nudged 5 pt left and 6 pt up from
    (dx, dy) so it sits clear of the panel and its title."""
    ax.annotate(letter, xy=(dx, dy), xycoords="axes fraction", xytext=(-5, 6),
                textcoords="offset points", fontsize=BASE_PT + 1, fontweight="bold",
                va="top", ha="left", color=INK, annotation_clip=False)


def plain_log_axis(axis):
    """Plain tick labels (100, 1,000, 10,000) on a log axis: exponent labels print at
    about 5 pt, below the 7 pt text size."""
    import matplotlib.ticker as mt
    axis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))
    axis.set_minor_locator(mt.NullLocator())
