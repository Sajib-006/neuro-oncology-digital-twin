"""Figure 5: a roadmap for a brain tumor digital twin, and where current research stands.

Input : icons_svg/*.svg (cleaned Bioicons files, see icons_svg/CREDITS.txt); no data files
Output: FIG_DIR/fig5_digital_twin.{svg,html,pdf,png}
Needs Google Chrome or Chromium (headless, to print the SVG to PDF and PNG) and Arial
(text widths are measured with Arial.ttf, so the layout matches the paper).
Set CHROME to the browser path if it is not found automatically.

One vector SVG in millimetres (183 mm wide, Arial). Story, left to right and back:
  patient data (repeated vs once, plus prior knowledge)
  -> digital twin (tumor state with spatial ecology, dynamics, therapy simulation, data update)
  -> outputs (forecasts with uncertainty) -> testing in steps -> tumor board
  -> care goes on over time, new scans arrive -> data update -> state.
Status marks: green check = a published research prototype exists (Section 6), grey
circle = none found. Dark numbered squares: the three gaps measured in this review.
All charts and small glyphs are drawn here. Content follows the studies cited in
Section 6 (Lipkova 2019, Ezhov 2023, Rockne 2010, Hormuth 2021, Balcerak 2024, Miniere 2025).
The script stops with an error if any text is wider than its space.
Run: python src/figures/fig5_digital_twin.py
"""
import base64, os, shutil, subprocess, sys
import numpy as np
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import config

ICONS = os.path.join(HERE, "icons_svg")
W, H = 183.0, 105.5
PT = 0.3528                       # mm per point
FONT_DIRS = [os.environ.get("FONT_DIR", os.path.join(HERE, "fonts")),
             "/System/Library/Fonts/Supplemental", "/Library/Fonts",
             "/usr/share/fonts/truetype/msttcorefonts", "/usr/share/fonts/truetype/arial"]


def find_chrome():
    for c in [os.environ.get("CHROME"), shutil.which("google-chrome"), shutil.which("chromium"),
              shutil.which("chromium-browser"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if c and os.path.exists(c):
            return c
    sys.exit("Chrome not found: set CHROME to the path of Google Chrome or Chromium")


def arial(name):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, 200)
    sys.exit(f"{name} not found: copy it into src/figures/fonts/ or set FONT_DIR")


FONT = arial("Arial.ttf")
FONT_B = arial("Arial Bold.ttf")

INK, INK2, MUTED = "#1f1f1f", "#4d4d4d", "#8c8c8c"
# palette from the ggsci R package; ORANGE is the name kept for the update-loop colour
BLUE, ORANGE, GREEN, VERM, GREY = "#3C5488", "#4DBBD5", "#00A087", "#E64B35", "#9a9a9a"
SALMON = "#F39B7F"
ORANGE_DK = INK
SEQ = ["#91D1C2", "#4DBBD5", "#00A087", "#3C5488"]
ZONE_FILL = "#f5f4f1"

out, warnings = [], []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_w(s, pt, bold=False):
    return (FONT_B if bold else FONT).getlength(s) / 200 * pt * PT


def T(x, y, s, pt=6.5, bold=False, anchor="middle", color=INK, maxw=None, italic=False):
    if maxw is not None and text_w(s, pt, bold) > maxw:
        warnings.append(f"text too wide ({text_w(s, pt, bold):.1f} > {maxw:.1f} mm): {s!r}")
    fw = ' font-weight="bold"' if bold else ""
    fs = ' font-style="italic"' if italic else ""
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{pt * PT:.3f}" text-anchor="{anchor}" '
               f'fill="{color}"{fw}{fs}>{esc(s)}</text>')


def lines(x, y, rows, pt=6.5, lh=None, **k):
    lh = lh or pt * PT * 1.18
    for i, s in enumerate(rows):
        T(x, y + i * lh, s, pt=pt, **k)
    return y + (len(rows) - 1) * lh


def rect(x, y, w, h, fill="white", stroke="none", sw=0.3, r=1.4, dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d} {extra}/>')


def card(x, y, w, h, accent=None, fill="white", stroke="#d9dde2"):
    rect(x + 0.35, y + 0.45, w, h, fill="#0b3954", r=1.6, extra='opacity="0.10"')   # soft shadow
    rect(x, y, w, h, fill=fill, stroke=stroke, sw=0.25, r=1.6)
    if accent:
        out.append(f'<path d="M{x + 1.6:.2f},{y:.2f} h{w - 3.2:.2f} a1.6,1.6 0 0 1 1.6,1.6 v0.6 '
                   f'h{-w:.2f} v-0.6 a1.6,1.6 0 0 1 1.6,-1.6 z" fill="{accent}"/>')


def icon(name, x, y, w, h, opacity=1.0):
    data = base64.b64encode(open(os.path.join(ICONS, f"{name}.svg"), "rb").read()).decode()
    op = f' opacity="{opacity}"' if opacity < 1 else ""
    out.append(f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
               f'preserveAspectRatio="xMidYMid meet"{op} href="data:image/svg+xml;base64,{data}"/>')


def arrow(d, color=MUTED, sw=0.4, head=True, dash=None):
    m = f' marker-end="url(#ah-{color[1:]})"' if head else ""
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
               f'stroke-linecap="round" stroke-linejoin="round"{ds}{m}/>')


def chip(cx, y, s, exists, w=None):
    pt = 6.0
    w = w or text_w(s, pt) + 5.2
    x = cx - w / 2
    if exists:
        rect(x, y, w, 3.5, fill="#e2f3ec", stroke=GREEN, sw=0.3, r=1.75)
        out.append(f'<path d="M{x + 1.3:.2f},{y + 1.85:.2f} l0.6,0.6 l1.1,-1.3" fill="none" '
                   f'stroke="{GREEN}" stroke-width="0.35" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        rect(x, y, w, 3.5, fill="#f1f1f1", stroke=GREY, sw=0.3, r=1.75, dash="0.8,0.5")
        out.append(f'<circle cx="{x + 2.0:.2f}" cy="{y + 1.75:.2f}" r="0.6" fill="none" '
                   f'stroke="{GREY}" stroke-width="0.3"/>')
    T(x + 3.2 + (w - 3.2) / 2 - 0.3, y + 2.55, s, pt=pt, color=INK)


def gap(x, y, n):
    # gap marker: dark rounded square (not a circle, so it never looks like a testing step,
    # and no red next to the green checks)
    out.append(f'<rect x="{x - 1.5:.2f}" y="{y - 1.5:.2f}" width="3.0" height="3.0" rx="0.55" '
               f'fill="#2b2b2b" stroke="white" stroke-width="0.3"/>')
    T(x, y + 0.75, str(n), pt=6.0, bold=True, color="white")


def mri(x, y, s, tumor=1.0):
    """Axial brain slice (DBCLS) with a drawn lesion whose size tells the story over time."""
    icon("Horizontal_plane_of_the_brain", x, y, s, s)
    if tumor > 0:
        cx, cy = x + s * 0.66, y + s * 0.36
        out.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{0.13 * s * tumor:.2f}" '
                   f'ry="{0.11 * s * tumor:.2f}" fill="#b8323b" fill-opacity="0.85" '
                   f'stroke="#7a1c22" stroke-width="0.15"/>')


def spatial_glyph(x, y, s):
    """Tissue outline with spots coloured by cell niche (drawn, not an icon)."""
    rect(x, y, s, s, fill="#fbe9ee", stroke="#d7a1b1", sw=0.25, r=1.2)
    rng = np.random.default_rng(3)
    cols = [SEQ[0], SEQ[1], VERM, SALMON]
    n = 5
    for i in range(n):
        for j in range(n):
            cx, cy = x + (i + 0.5 + 0.5 * (j % 2)) * s / (n + 0.5), y + (j + 0.5) * s / n
            d = np.hypot(cx - (x + s * 0.45), cy - (y + s * 0.5)) / s
            c = cols[2] if d < 0.18 else cols[3] if d < 0.3 else cols[int(rng.integers(0, 2))]
            out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{s * 0.075:.2f}" fill="{c}"/>')


def network_glyph(x, y, s):
    """Small knowledge graph: genes, drugs and tumors as linked nodes."""
    pts = [(0.15, 0.3), (0.5, 0.12), (0.85, 0.35), (0.3, 0.8), (0.72, 0.82), (0.52, 0.5)]
    edges = [(0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (0, 1), (2, 4), (3, 4)]
    for a, b in edges:
        out.append(f'<line x1="{x + pts[a][0] * s:.2f}" y1="{y + pts[a][1] * s:.2f}" '
                   f'x2="{x + pts[b][0] * s:.2f}" y2="{y + pts[b][1] * s:.2f}" stroke="{MUTED}" stroke-width="0.25"/>')
    cols = [BLUE, GREEN, ORANGE, BLUE, GREEN, VERM]
    for (px, py), c in zip(pts, cols):
        out.append(f'<circle cx="{x + px * s:.2f}" cy="{y + py * s:.2f}" r="{s * 0.1:.2f}" '
                   f'fill="{c}" stroke="white" stroke-width="0.2"/>')


def loop_glyph(cx, cy, r, color=ORANGE):
    for a0, a1 in ((200, 340), (20, 160)):
        t0, t1 = np.radians(a0), np.radians(a1)
        x0, y0 = cx + r * np.cos(t0), cy + r * np.sin(t0)
        x1, y1 = cx + r * np.cos(t1), cy + r * np.sin(t1)
        out.append(f'<path d="M{x0:.2f},{y0:.2f} A{r},{r} 0 0 1 {x1:.2f},{y1:.2f}" fill="none" '
                   f'stroke="{color}" stroke-width="{r * 0.28:.2f}" stroke-linecap="round" '
                   f'marker-end="url(#ah-{color[1:]})"/>')


def defs():
    marks = "".join(
        f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4.2" '
        f'markerHeight="4.2" orient="auto-start-reverse" markerUnits="strokeWidth">'
        f'<path d="M0,0.8 L9.2,5 L0,9.2 z" fill="{c}"/></marker>'
        for c in (MUTED, ORANGE, BLUE, INK2))
    return (f'<defs>{marks}'
            '<linearGradient id="twin" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#eef6fb"/><stop offset="1" stop-color="#d3e7f3"/></linearGradient>'
            '<linearGradient id="band" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#fff8ea"/><stop offset="1" stop-color="#fdebc6"/></linearGradient>'
            '<linearGradient id="fanB" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{BLUE}" stop-opacity="0.45"/>'
            f'<stop offset="1" stop-color="{BLUE}" stop-opacity="0.10"/></linearGradient>'
            '<linearGradient id="fanV" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{SALMON}" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="{SALMON}" stop-opacity="0.12"/></linearGradient>'
            '<linearGradient id="dyn" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{SEQ[1]}" stop-opacity="0.30"/>'
            f'<stop offset="1" stop-color="{SEQ[3]}" stop-opacity="0.10"/></linearGradient>'
            '</defs>')


def status(x, y, s, exists, anchor="middle"):
    """Plain status line: green check = published prototype, grey open circle = none found."""
    pt = 6.0
    w = text_w(s, pt) + 2.6
    x0 = x - w / 2 if anchor == "middle" else x
    if exists:
        out.append(f'<path d="M{x0 + 0.1:.2f},{y - 1.0:.2f} l0.6,0.65 l1.15,-1.45" fill="none" stroke="{GREEN}" '
                   'stroke-width="0.4" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        out.append(f'<circle cx="{x0 + 0.85:.2f}" cy="{y - 0.95:.2f}" r="0.7" fill="none" stroke="{GREY}" stroke-width="0.3"/>')
    T(x0 + 2.6, y, s, pt=pt, anchor="start", color="#00806e" if exists else "#6b6b6b")


def build():
    # ================= patient data =================
    icon("patient", 1.2, 25.0, 6.8, 22.5)
    T(4.6, 51.0, "Patient", pt=6.5, color=INK2)
    T(13.0, 8.8, "Collected repeatedly", pt=6.5, bold=True, anchor="start", color=ORANGE_DK)
    T(13.0, 37.0, "Usually once, at diagnosis", pt=6.5, bold=True, anchor="start", color=INK2)
    for (y0, y1, col) in ((10.6, 32.4, ORANGE), (38.8, 60.6, GREY)):
        out.append(f'<path d="M11.4,{y0} H10.8 V{y1} H11.4" fill="none" stroke="{col}" stroke-width="0.45"/>')
    arrow("M8.4,33.0 C9.8,33.0 9.6,21.5 10.8,21.5", color=ORANGE, sw=0.4, head=False)
    arrow("M8.4,40.0 C9.8,40.0 9.6,49.7 10.8,49.7", color=GREY, sw=0.4, head=False)

    def item(y, title, sub, draw):
        draw(13.0, y, 6.4, 6.4)
        T(21.0, y + 4.0, title, pt=6.5, anchor="start", maxw=22.5)
        T(21.0, y + 5.3, sub, pt=6.0, anchor="start", color=INK2, maxw=22.5)
        return y + 3.2

    mids = [
        item(11.0, "MRI and PET", "", lambda x, y, w, h: mri(x, y, h, 1.0)),
        item(18.5, "Clinical records", "", lambda x, y, w, h: icon("notepad", x, y, w, h)),
        item(26.0, "Liquid biopsy", "", lambda x, y, w, h: icon("blood_sample_tube", x, y, w, h)),
        item(39.2, "Pathology", "", lambda x, y, w, h: icon("microscope", x, y, w, h)),
        item(46.7, "Methylation, omics", "", lambda x, y, w, h: icon("dna-1", x, y, w, h)),
        item(54.2, "Spatial omics", "", lambda x, y, w, h: spatial_glyph(x + 0.4, y + 0.4, 5.6)),
    ]
    mids.append(item(66.0, "Prior knowledge", "",
                     lambda x, y, w, h: network_glyph(x, y, w)))
    gap(21.0 + text_w("Prior knowledge", 6.5) + 2.4, 67.9, 1)
    # one collecting line, then a single arrow into the tumor state
    bus = 46.6
    for m in mids:
        out.append(f'<line x1="44.6" y1="{m:.2f}" x2="{bus}" y2="{m:.2f}" stroke="{MUTED}" stroke-width="0.3"/>')
    out.append(f'<line x1="{bus}" y1="{mids[0]:.2f}" x2="{bus}" y2="{mids[-1]:.2f}" stroke="{MUTED}" stroke-width="0.3"/>')
    arrow(f"M{bus},22.0 H54.6", color=INK2, sw=0.4)
    gap(bus, 43.0, 2)

    # ================= digital twin =================
    icon("patient", 50.3, 1.6, 2.6, 8.4, opacity=0.4)
    T(54.2, 5.4, "Digital twin", pt=7.5, bold=True, anchor="start", color=BLUE)
    T(54.2, 8.7, "A model of one patient that updates over time", pt=6.0,
      anchor="start", color=INK2, maxw=74)
    out.append(f'<line x1="50.3" y1="10.9" x2="128.5" y2="10.9" stroke="{BLUE}" stroke-width="0.35"/>')

    c1, c2, c3 = 63.0, 90.0, 116.4
    # tumor state: brain with tumor and an uncertainty ring
    icon("brain-2", c1 - 7.4, 13.2, 14.8, 14.0)
    tx, ty = c1 - 1.6, 17.6
    icon("tumor", tx - 2.0, ty - 2.0, 4.0, 4.0)
    out.append(f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="3.3" fill="none" stroke="{BLUE}" '
               'stroke-width="0.3" stroke-dasharray="0.7,0.5"/>')
    T(c1, 31.6, "Tumor state", pt=7.0, bold=True)
    lines(c1, 35.0, ["Tumor and surroundings,", "with uncertainty"], pt=6.5, maxw=26)
    status(c1, 41.6, "MRI, PET", True)

    # tumor dynamics: growth curve with growing tumors
    x0, x1, y0, y1 = c2 - 11.0, c2 + 8.4, 27.0, 14.0
    arrow(f"M{x0},{y1} V{y0} H{x1 + 0.4}", color=MUTED, sw=0.3, head=False)
    xs = np.linspace(x0 + 0.6, x1, 40)
    f = lambda v: y0 - 1.0 - (y0 - y1 - 2.6) * ((v - x0) / (x1 - x0)) ** 1.8
    up = [f(v) - 0.2 - 1.6 * ((v - x0) / (x1 - x0)) ** 1.3 for v in xs]
    lo = [f(v) + 0.2 + 1.6 * ((v - x0) / (x1 - x0)) ** 1.3 for v in xs]
    band = " ".join(f"{a:.2f},{b:.2f}" for a, b in zip(xs, up)) + " " + \
           " ".join(f"{a:.2f},{b:.2f}" for a, b in zip(xs[::-1], lo[::-1]))
    out.append(f'<polygon points="{band}" fill="{SEQ[2]}" fill-opacity="0.18"/>')
    out.append('<polyline points="' + " ".join(f"{a:.2f},{f(a):.2f}" for a in xs) +
               f'" fill="none" stroke="{SEQ[3]}" stroke-width="0.45"/>')
    for frac, s in ((0.15, 1.8), (0.52, 2.6), (0.9, 3.6)):
        px = x0 + frac * (x1 - x0)
        icon("tumor", px - s / 2, f(px) - s - 0.8, s, s)
    T(c2, 31.6, "Tumor dynamics", pt=7.0, bold=True)
    lines(c2, 35.0, ["Projects the state", "forward in time"], pt=6.5, maxw=23)
    status(c2, 41.6, "MRI-fitted", True)

    # therapy simulation: beams on a head, and what-if branches
    hx, hy = c3 - 7.2, 18.8
    for ang in (205, 270, 335):
        t = np.radians(ang)
        out.append(f'<line x1="{hx + 4.6 * np.cos(t):.2f}" y1="{hy + 4.6 * np.sin(t):.2f}" x2="{hx:.2f}" '
                   f'y2="{hy:.2f}" stroke="{VERM}" stroke-width="0.55" stroke-opacity="0.75" stroke-linecap="round"/>')
    out.append(f'<ellipse cx="{hx:.2f}" cy="{hy + 0.3:.2f}" rx="2.5" ry="2.9" fill="#f6e3d3" stroke="#b9927a" stroke-width="0.25"/>')
    out.append(f'<circle cx="{hx + 0.2:.2f}" cy="{hy:.2f}" r="0.7" fill="#b8323b"/>')
    bx0, by0, bx1 = c3 - 3.2, 21.0, c3 + 7.0
    out.append(f'<circle cx="{bx0:.2f}" cy="{by0:.2f}" r="0.5" fill="{INK2}"/>')
    for dyy, col, lab, dash in ((-5.0, GREY, "None", "0.8,0.5"), (-0.8, BLUE, "A", None), (3.6, GREEN, "B", None)):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<path d="M{bx0:.2f},{by0:.2f} C{bx0 + 4:.2f},{by0:.2f} {bx1 - 4:.2f},{by0 + dyy:.2f} '
                   f'{bx1:.2f},{by0 + dyy:.2f}" fill="none" stroke="{col}" stroke-width="0.45"{ds}/>')
        T(bx1 + 0.6, by0 + dyy + 0.8, lab, pt=6.0, anchor="start", bold=bool(dash is None),
          color=INK2 if dash else col)
    T(c3, 31.6, "Therapy simulation", pt=7.0, bold=True)
    lines(c3, 35.0, ["Compares treatment", "plans before use"], pt=6.5, maxw=24)
    status(c3, 41.6, "RT plans", True)

    arrow(f"M{c1 + 8.2},20.4 H{x0 - 1.2}", color=INK2, sw=0.4)
    arrow(f"M{x1 + 1.4},20.4 H{hx - 5.0}", color=INK2, sw=0.4)

    # spatial ecology, part of the state
    for nm, (dx, dy, s) in zip(["cancerous-cell-1", "macrophage", "t-lymphocyte", "neuron"],
                               [(-5.2, 0.6, 5.0), (-0.6, -0.4, 4.4), (3.4, 1.4, 4.0), (-2.4, 3.8, 4.6)]):
        icon(nm, c1 + dx - s / 2, 51.6 + dy, s, s)
    arrow(f"M{c1},50.8 V44.2", color=MUTED, sw=0.35, dash="0.8,0.5")
    T(c1, 63.4, "Spatial ecology", pt=7.0, bold=True)
    T(c1, 66.8, "Cell types and layout", pt=6.5, maxw=30)
    status(c1, 70.4, "None yet", False)

    # data update (feedback into the state)
    ux = 84.0
    loop_glyph(ux + 3.2, 58.4, 2.8)
    T(ux + 8.4, 55.6, "Data update", pt=7.0, bold=True, anchor="start", color=ORANGE_DK)
    lines(ux + 8.4, 59.0, ["New scans and events", "correct the state"], pt=6.5, anchor="start", maxw=128.5 - ux - 8.4)
    status(ux + 8.4, 65.0, "Weekly MRI, 21 patients", True, anchor="start")
    arrow(f"M{ux - 0.4},57.0 H78.6 Q76.6,57.0 76.6,55.0 V33.4 Q76.6,31.4 74.6,31.4 H72.6",
          color=ORANGE, sw=0.5)

    # ================= outputs and use =================
    T(133.6, 5.4, "Outputs and use", pt=7.5, bold=True, anchor="start")
    out.append(f'<line x1="133.6" y1="10.9" x2="181.5" y2="10.9" stroke="{MUTED}" stroke-width="0.35"/>')
    arrow(f"M{c3 + 12.6},20.4 H134.6", color=INK2, sw=0.4)
    ax0, ax1, ay0, ay1 = 137.0, 167.0, 24.8, 13.2
    arrow(f"M{ax0},{ay1} V{ay0} H{ax1}", color=MUTED, sw=0.3, head=False)
    now = ax0 + 10.0
    out.append(f'<line x1="{now:.2f}" y1="{ay1:.2f}" x2="{now:.2f}" y2="{ay0:.2f}" stroke="{MUTED}" '
               'stroke-width="0.25" stroke-dasharray="0.6,0.5"/>')
    T(now, ay0 + 2.4, "Now", pt=6.0, color=INK2)
    T(ax1, ay0 + 2.4, "Time", pt=6.0, anchor="end", color=INK2)
    for px, py in [(ax0 + 1.6, ay0 - 2.6), (ax0 + 4.4, ay0 - 3.3), (ax0 + 7.2, ay0 - 4.4), (now, ay0 - 5.4)]:
        out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="0.55" fill="{BLUE}"/>')
    for (yy, grow, grad, col, lab, sp) in ((ay0 - 5.4, -4.4, "fanB", BLUE, "Tumor", 2.0),
                                           (ay0 - 1.2, -2.2, "fanV", VERM, "Harm", 1.5)):
        xe = ax1 - 0.5
        out.append(f'<polygon points="{now:.2f},{yy:.2f} {xe:.2f},{yy + grow - sp:.2f} {xe:.2f},{yy + grow + sp:.2f}" '
                   f'fill="url(#{grad})"/>')
        out.append(f'<line x1="{now:.2f}" y1="{yy:.2f}" x2="{xe:.2f}" y2="{yy + grow:.2f}" stroke="{col}" stroke-width="0.45"/>')
        T(xe + 1.0, yy + grow + 0.8, lab, pt=6.0, anchor="start", color=col, bold=True)
    T(157.5, 31.6, "Forecasts", pt=7.0, bold=True)
    T(157.5, 35.0, "Tumor and harm, with uncertainty", pt=6.5, maxw=46)
    arrow("M157.5,39.6 V42.2", color=INK2, sw=0.4)

    T(157.5, 46.0, "Testing in steps", pt=7.0, bold=True)
    gap(169.4, 45.2, 3)
    for i, s in enumerate(["Forecast the next scan", "Run silently in care", "Compare with trials",
                           "Interventional trial"]):
        yy = 49.4 + i * 2.8
        out.append(f'<circle cx="{142.0:.2f}" cy="{yy - 0.85:.2f}" r="1.15" fill="{SEQ[i]}"/>')
        T(142.0, yy - 0.12, str(i + 1), pt=6.0, bold=True, color=INK if i < 2 else "white")
        T(144.4, yy, s, pt=6.5, anchor="start", maxw=36)
    status(157.5, 61.4, "Not yet in patients", False)
    arrow("M157.5,63.0 V65.4", color=INK2, sw=0.4)

    icon("Examination_Man", 137.0, 66.4, 11.0, 11.0)
    T(150.4, 70.2, "Tumor board", pt=7.0, bold=True, anchor="start")
    T(150.4, 73.6, "Clinician decides", pt=6.5, anchor="start", maxw=30)

    # ================= care over time closes the loop =================
    T(50.3, 80.4, "Over the course of treatment", pt=6.5, bold=True, anchor="start", color=ORANGE_DK)
    ax_y = 89.2
    arrow(f"M50.3,{ax_y} H180.4", color=ORANGE, sw=0.45)
    T(180.6, ax_y + 3.3, "Time", pt=6.0, anchor="end", color=ORANGE_DK)
    for i, (lab, tsz) in enumerate([("Diagnosis", 1.0), ("Surgery", 0.45), ("Radiotherapy", 0.35),
                                    ("Follow-up", 0.5), ("Follow-up", 0.95)]):
        ex = 92.0 + i * 18.6
        mri(ex - 2.7, 81.2, 5.4, tsz)
        out.append(f'<line x1="{ex:.2f}" y1="{ax_y - 0.9:.2f}" x2="{ex:.2f}" y2="{ax_y + 0.9:.2f}" '
                   f'stroke="{ORANGE_DK}" stroke-width="0.3"/>')
        T(ex, ax_y + 3.3, lab, pt=6.0, color=INK2)
    # tumor board -> time line -> data update
    arrow("M176.5,78.2 V87.4", color=ORANGE, sw=0.5)
    arrow("M101.4,87.4 V67.2", color=ORANGE, sw=0.5)

    # ================= key =================
    T(1.5, 99.0, "Published prototype", pt=6.5, bold=True, anchor="start")
    k2 = 36.5 + text_w("Uneven knowledge across tumors (Fig. 1)", 6.5) + 11.0
    status(36.5, 99.0, "Exists", True, anchor="start")
    status(k2, 99.0, "None found", False, anchor="start")
    T(1.5, 103.6, "Gaps measured in this review", pt=6.5, bold=True, anchor="start")
    kx = 36.5
    for i, s in enumerate(["Uneven knowledge across tumors (Fig. 1)", "Data types studied apart (Figs 2, 3)",
                           "Little validation in patients (Fig. 4)"]):
        gap(kx + 1.5, 102.9, i + 1)
        T(kx + 4.0, 103.6, s, pt=6.5, anchor="start")
        kx += text_w(s, 6.5) + 11.0


def main():
    build()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" '
           f'font-family="Arial, Helvetica, sans-serif">{defs()}'
           f'<rect width="{W}" height="{H}" fill="white"/>' + "".join(out) + "</svg>")
    base = str(config.fig_path("fig5_digital_twin"))
    open(base + ".svg", "w").write(svg)
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:{W}mm {H}mm;margin:0}}'
            f'html,body{{margin:0;padding:0}}svg{{display:block}}</style></head><body>{svg}</body></html>')
    open(base + ".html", "w").write(html)
    common = [find_chrome(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars"]
    subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={base}.pdf",
                             f"file://{base}.html"], check=True, capture_output=True)
    px_w, px_h = round(W / 25.4 * 96), round(H / 25.4 * 96)
    subprocess.run(common + ["--force-device-scale-factor=5", f"--window-size={px_w},{px_h}",
                             f"--screenshot={base}.png", f"file://{base}.html"], check=True, capture_output=True)
    print("written ->", base + ".{svg,html,pdf,png}")
    for w in warnings:
        print("WARNING", w)
    if warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
