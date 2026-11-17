"""Supplementary Figure S1: how the three analyses were built (literature, knowledge bases,
trials and devices). Drawn as SVG in mm at print size (183 mm wide), printed to PDF with Chrome.
Colors follow the Fig. 1 ring: blue for the literature (data types), green for knowledge bases,
salmon for trials and devices (reaching patients). Icons: Bioicons (see icons_overview/CREDITS.txt).
Numbers are those reported in the paper (Methods, Supplementary Notes 1 to 3).
Needs Chrome (CHROME), cairosvg with the cairo library, Pillow and Arial (FONT_DIR or system).
Run: python src/figures/figS1_workflow.py      Output: FIG_DIR/figS1_workflow.{svg,html,pdf}
"""
import base64, io, os, subprocess, sys
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "icons_overview"))
sys.path.insert(0, os.path.join(HERE, ".."))
from topng import png as svg_png  # noqa: E402
import config  # noqa: E402

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def _font(name):
    for d in [os.environ.get("FONT_DIR", os.path.join(HERE, "fonts")), "/System/Library/Fonts/Supplemental",
              "/Library/Fonts", "/usr/share/fonts/truetype/msttcorefonts", "C:/Windows/Fonts"]:
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    sys.exit(f"{name} not found; put Arial in FONT_DIR (needed to measure text widths)")


FONT = ImageFont.truetype(_font("Arial.ttf"), 200)
FONT_B = ImageFont.truetype(_font("Arial Bold.ttf"), 200)
PT = 25.4 / 72                       # mm per point
W, H = 183.0, 121.0
INK, INK2, MUTED, LINE = "#1f1f1f", "#444444", "#6b6b6b", "#8a8a8a"
LANES = {"lit": ("#2F4A80", "#D5DFEF", "#EEF2F9"),
         "kb": ("#00745F", "#CBE9E0", "#EAF6F2"),
         "pat": ("#B23A26", "#FADBD1", "#FDF0EC")}
out, warnings = [], []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_w(s, pt, bold=False):
    return (FONT_B if bold else FONT).getlength(s) / 200 * pt * PT


def T(x, y, s, pt=6.5, bold=False, anchor="middle", color=INK, maxw=None):
    if maxw is not None and text_w(s, pt, bold) > maxw + 0.01:
        warnings.append(f"text too wide ({text_w(s, pt, bold):.1f} > {maxw:.1f} mm): {s!r}")
    fw = ' font-weight="bold"' if bold else ""
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{pt * PT:.3f}" text-anchor="{anchor}" '
               f'fill="{color}"{fw}>{esc(s)}</text>')


def rect(x, y, w, h, fill="white", stroke="none", sw=0.3, r=1.4, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(x1, y1, x2, y2, color=LINE, sw=0.4):
    out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2 - 1.1:.2f}" stroke="{color}" '
               f'stroke-width="{sw}"/>')
    out.append(f'<path d="M{x2 - 0.9:.2f},{y2 - 1.3:.2f} L{x2:.2f},{y2:.2f} L{x2 + 0.9:.2f},{y2 - 1.3:.2f} Z" '
               f'fill="{color}"/>')


_icons = {}


def icon(name, cx, cy, h):
    if name not in _icons:
        im = svg_png(os.path.join(HERE, "icons_overview", "svg", name), 500)
        b = io.BytesIO(); im.save(b, "PNG")
        _icons[name] = (base64.b64encode(b.getvalue()).decode(), im.size)
    data, (pw, ph) = _icons[name]
    w = h * pw / ph
    out.append(f'<image x="{cx - w / 2:.2f}" y="{cy - h / 2:.2f}" width="{w:.2f}" height="{h:.2f}" '
               f'href="data:image/png;base64,{data}"/>')


def header(x, w, letter, title, lane, icons_):
    dark, mid, light = LANES[lane]
    rect(x, 2.0, w, 9.0, fill=mid, r=1.6)
    T(x + 2.4, 7.9, letter, pt=8, bold=True, anchor="start", color=INK)
    T(x + 6.2, 7.9, title, pt=7.5, bold=True, anchor="start", color=dark, maxw=w - 20)
    for i, (nm, h) in enumerate(icons_):
        icon(nm, x + w - 4.5 - 8.0 * i, 6.5, h)


def step(x, y, w, h, lane, number=None, label=(), small=(), num_pt=9.5, lab_pt=6.5):
    """White box with a lane-colored border: optional big number, then label lines."""
    dark, mid, light = LANES[lane]
    rect(x, y, w, h, fill="white", stroke=dark, sw=0.35, r=1.3)
    cy = y + 4.3
    if number:
        T(x + w / 2, cy, number, pt=num_pt, bold=True, color=dark, maxw=w - 2)
        cy += 3.0
    for s in label:
        T(x + w / 2, cy, s, pt=lab_pt, color=INK, maxw=w - 2); cy += 2.6
    for s in small:
        T(x + w / 2, cy, s, pt=6, color=INK2, maxw=w - 2); cy += 2.4


def note(x, y, s, w=None):
    T(x, y, s, pt=6, color=MUTED, anchor="start", maxw=w)


# ------------------------------------------------------------------ lane a: literature survey
def lane_literature(x, w):
    lane = "lit"; dark, mid, light = LANES[lane]
    header(x, w, "a", "Literature survey", lane, [("notepad.svg", 6.5), ("OpenClipart__database-colored.svg", 6.0)])
    cx = x + w / 2
    step(x + 3, 14.5, w - 6, 13.0, lane, "Scopus Search API",
         ["Tumor terms (31) AND AI terms (91)"], ["Title, abstract, keywords; 2015 to Sep 2026"], num_pt=7.5)
    arrow(cx, 27.5, cx, 33.5)
    note(cx + 1.5, 31.2, "Articles and conference papers;", )
    note(cx + 1.5, 33.4, "337 reviews removed")
    step(x + 3, 35.0, w - 6, 10.0, lane, "13,423", ["AI research papers"])
    arrow(cx, 45.0, cx, 50.5)
    # keyword tags with four chips
    rect(x + 3, 52.0, w - 6, 15.5, fill="white", stroke=dark, sw=0.35, r=1.3)
    T(cx, 56.3, "Keyword tags", pt=7, bold=True, color=dark)
    chips = [["Data types", "Clinical tasks"], ["Model families", "Evaluation"]]
    for r_, row in enumerate(chips):
        tw = [text_w(c, 6) + 3.0 for c in row]; tot = sum(tw) + 1.5
        xx = cx - tot / 2
        for c, cw in zip(row, tw):
            rect(xx, 58.2 + r_ * 4.3, cw, 3.4, fill=light, stroke=dark, sw=0.25, r=1.7)
            T(xx + cw / 2, 60.65 + r_ * 4.3, c, pt=6, color=dark)
            xx += cw + 1.5
    # split: counts (left) and hand check (right)
    lx, rx = x + 3, x + w / 2 + 1.0
    bw = w / 2 - 4.0
    arrow(cx, 67.5, lx + bw / 2, 73.0)
    arrow(cx, 67.5, rx + bw / 2, 73.0)
    step(lx, 74.0, bw, 43.5, lane, None, ["Counts and", "trends"], ["Figs. 2f,g, 3, 4, 5a"])
    # small trend glyph: axes and two lines (one rising, one flat)
    gx0, gy0, gw, gh = lx + 3.0, 88.0, bw - 6.0, 16.5
    out.append(f'<path d="M{gx0},{gy0} V{gy0 + gh} H{gx0 + gw}" fill="none" stroke="{MUTED}" stroke-width="0.3"/>')
    pts1 = [(0, 0.95), (0.2, 0.85), (0.4, 0.62), (0.6, 0.45), (0.8, 0.25), (1.0, 0.1)]
    pts2 = [(0, 0.95), (0.2, 0.93), (0.4, 0.92), (0.6, 0.9), (0.8, 0.91), (1.0, 0.89)]
    for pts, col in [(pts1, dark), (pts2, "#8DA3C9")]:
        d = " ".join(f"{'M' if i == 0 else 'L'}{gx0 + 1 + px * (gw - 2):.2f},{gy0 + py * gh:.2f}"
                     for i, (px, py) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="0.6" stroke-linejoin="round"/>')
    T(gx0 + gw / 2, gy0 + gh + 2.8, "2015 to 2025", pt=6, color=MUTED)
    for j, (lab_, col) in enumerate([("AI share", dark), ("2+ data types", "#8DA3C9")]):
        yl = gy0 + gh + 6.6 + j * 3.0
        out.append(f'<line x1="{gx0:.2f}" y1="{yl - 0.7:.2f}" x2="{gx0 + 3.0:.2f}" y2="{yl - 0.7:.2f}" '
                   f'stroke="{col}" stroke-width="0.8"/>')
        T(gx0 + 4.0, yl, lab_, pt=6, color=INK2, anchor="start")
    # hand check with precision/recall bars
    rect(rx, 74.0, bw, 43.5, fill="white", stroke=dark, sw=0.35, r=1.3)
    T(rx + bw / 2, 78.3, "Hand check", pt=7, bold=True, color=dark)
    T(rx + bw / 2, 81.2, "100 papers, 2 coders", pt=6, color=INK2, maxw=bw - 1.5)
    T(rx + bw / 2, 83.6, "+ third reviewer", pt=6, color=INK2, maxw=bw - 1.5)
    T(rx + bw / 2, 86.2, "κ = 0.92", pt=6.5, bold=True, color=INK, maxw=bw - 1.5)
    rows = [("Imaging", 0.95, 0.79), ("Combining", 0.70, 0.28), ("External val.", 0.81, 0.25)]
    bx0, bmax = rx + 2.0, bw - 4.0
    yy = 89.0
    for name, p, r in rows:
        T(bx0, yy, name, pt=6, color=INK, anchor="start", maxw=bmax)
        rect(bx0, yy + 1.0, bmax, 1.6, fill="#ececec", r=0.6)
        rect(bx0, yy + 1.0, bmax * p, 1.6, fill=dark, r=0.6)
        rect(bx0, yy + 3.0, bmax, 1.6, fill="#ececec", r=0.6)
        rect(bx0, yy + 3.0, bmax * r, 1.6, fill="#8DA3C9", r=0.6)
        yy += 7.0
    # key for bars
    rect(bx0, yy - 1.4, 2.4, 1.6, fill=dark, r=0.5); T(bx0 + 3.2, yy, "Precision", pt=6, anchor="start", color=INK2)
    rect(bx0, yy + 1.2, 2.4, 1.6, fill="#8DA3C9", r=0.5); T(bx0 + 3.2, yy + 2.6, "Recall", pt=6, anchor="start", color=INK2)
    T(rx + bw / 2, yy + 5.6, "Weighted to all papers", pt=6, color=MUTED, maxw=bw - 1.5)


# ------------------------------------------------------------------ lane b: knowledge bases
def lane_kb(x, w):
    lane = "kb"; dark, mid, light = LANES[lane]
    header(x, w, "b", "Knowledge bases", lane, [("ChenxinLi__Network.svg", 6.0), ("Servier__dna-1.svg", 7.0)])
    cx = x + w / 2
    srcs = [("Open Targets", "release 26.09"), ("CTD", "28 Aug 2026"), ("DisGeNET", "v7.0")]
    bw = (w - 6 - 2 * 1.5) / 3
    for i, (n, v) in enumerate(srcs):
        bx = x + 3 + i * (bw + 1.5)
        rect(bx, 14.5, bw, 9.0, fill="white", stroke=dark, sw=0.35, r=1.3)
        T(bx + bw / 2, 18.4, n, pt=6.5, bold=True, color=dark, maxw=bw - 1)
        T(bx + bw / 2, 21.3, v, pt=6, color=INK2, maxw=bw - 1)
        arrow(bx + bw / 2, 23.5, cx, 30.0)
    # gene x tumor matrix
    rect(x + 3, 31.0, w - 6, 21.0, fill="white", stroke=dark, sw=0.35, r=1.3)
    T(cx, 35.3, "Genes × 10 tumor classes", pt=7, bold=True, color=dark, maxw=w - 8)
    T(cx, 38.0, "curated and all-evidence levels", pt=6, color=INK2, maxw=w - 8)
    import random
    rnd = random.Random(7)
    cols = 10; rows_ = 4; cell = 2.2
    gx = cx - cols * cell / 2
    dens = [0.95, 0.9, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1]      # coverage falls off for rare classes
    for c in range(cols):
        for r in range(rows_):
            on = rnd.random() < dens[c]
            rect(gx + c * cell, 40.0 + r * cell, cell - 0.35, cell - 0.35,
                 fill=(dark if on else "#e6e6e6"), r=0.3)
    T(gx - 1.0, 44.6, "genes", pt=6, color=MUTED, anchor="end")
    T(cx, 50.4, "common  →  rare tumors", pt=6, color=MUTED)
    arrow(cx, 52.0, cx, 57.5)
    rect(x + 3, 58.5, w - 6, 13.0, fill="white", stroke=dark, sw=0.35, r=1.3)
    T(x + 6.0, 63.6, "Coverage per class", pt=6.5, color=INK, anchor="start")
    T(x + 6.0, 66.4, "Fig. 2a,b", pt=6, color=INK2, anchor="start")
    for i, v in enumerate([1.0, 0.8, 0.55, 0.4, 0.3, 0.2, 0.12, 0.07, 0.04, 0.02]):
        bh_ = 8.0 * v
        rect(x + w - 21.0 + i * 1.6, 69.6 - bh_, 1.15, max(bh_, 0.3), fill=dark, r=0.15)
    arrow(cx, 71.5, cx, 77.0)
    rect(x + 3, 78.0, w - 6, 39.5, fill="white", stroke=dark, sw=0.35, r=1.3)
    T(cx, 82.3, "Does similarity follow coverage?", pt=7, bold=True, color=dark, maxw=w - 8)
    T(cx, 85.0, "Fig. 2c–e", pt=6, color=INK2)
    # pre-specified test, then two follow-up checks
    rect(x + 6, 87.5, w - 12, 10.5, fill=light, stroke=dark, sw=0.25, r=1.2)
    T(cx, 91.6, "Pre-specified null test", pt=6.5, bold=True, color=INK, maxw=w - 14)
    T(cx, 94.4, "Failed: ρ = −0.63 to −0.42", pt=6, color=INK2, maxw=w - 14)
    arrow(cx, 98.0, cx, 102.5)
    rect(x + 6, 103.5, w - 12, 11.0, fill="white", stroke=dark, sw=0.25, r=1.2, dash="1.0,0.7")
    T(cx, 107.6, "Two follow-up checks", pt=6.5, bold=True, color=INK, maxw=w - 14)
    T(cx, 110.4, "Curveball null, size-matched Jaccard", pt=6, color=INK2, maxw=w - 14)
    T(cx, 112.9, "(not pre-specified)", pt=6, color=MUTED, maxw=w - 14)


# ------------------------------------------------------------------ lane c: trials and devices
def lane_trials(x, w):
    lane = "pat"; dark, mid, light = LANES[lane]
    header(x, w, "c", "Trials and devices", lane, [("Examination_Man.svg", 7.0)])
    half = (w - 6 - 2.0) / 2
    tx, dx = x + 3, x + 3 + half + 2.0
    T(tx + half / 2, 15.6, "ClinicalTrials.gov", pt=6.5, bold=True, color=dark, maxw=half)
    T(dx + half / 2, 15.6, "FDA AI device list", pt=6.5, bold=True, color=dark, maxw=half)
    trials = [("6,008", "brain tumor studies"), ("5,299", "no metastases only"), ("118", "AI or radiomics")]
    devs = [("1,614", "AI-enabled devices"), ("1,313", "radiology, neurology"), ("35", "name a brain tumor")]
    devs2 = ["", "or pathology panel", ""]
    y = 17.5
    for i in range(3):
        shrink = i * 0.8                                     # funnel: boxes narrow as records drop out
        for (bx, (n, lab), extra) in [(tx, trials[i], ""), (dx, devs[i], devs2[i])]:
            step(bx + shrink, y, half - 2 * shrink, 10.5 if not extra else 12.0, lane, n,
                 [lab] + ([extra] if extra else []), num_pt=8.5, lab_pt=6)
        if i < 2:
            arrow(tx + half / 2, y + 12.0 - (1.5 if True else 0), tx + half / 2, y + 15.0)
            arrow(dx + half / 2, y + 12.0, dx + half / 2, y + 15.0)
        y += 15.5
    # shared screening
    arrow(tx + half / 2, 61.0, tx + half / 2, 66.0)
    arrow(dx + half / 2, 61.0, dx + half / 2, 66.0)
    rect(x + 3, 67.0, w - 6, 21.0, fill=light, stroke=dark, sw=0.35, r=1.3)
    T(x + w / 2, 71.4, "Two independent screeners", pt=7, bold=True, color=dark, maxw=w - 8)
    T(x + w / 2, 74.3, "Written rules; κ = 0.81 trials, 0.20 devices", pt=6, color=INK2, maxw=w - 8)
    arrow(x + w / 2, 75.6, x + w / 2, 79.6)
    T(x + w / 2, 82.6, "Third reviewer settled differences", pt=6.5, bold=True, color=INK, maxw=w - 8)
    T(x + w / 2, 85.4, "15 trials, 19 devices", pt=6, color=INK2, maxw=w - 8)
    arrow(tx + half / 2, 88.0, tx + half / 2, 93.0)
    arrow(dx + half / 2, 88.0, dx + half / 2, 93.0)
    step(tx + 3.2, 94.0, half - 6.4, 13.0, lane, "77", ["trials"], ["Table S7"], num_pt=10)
    step(dx + 3.2, 94.0, half - 6.4, 13.0, lane, "12", ["devices"], ["Table S8"], num_pt=10)
    T(tx + half / 2, 110.8, "Fig. 5b; 0 of 28", pt=6, color=INK2, maxw=half)
    T(tx + half / 2, 113.2, "overdue posted results", pt=6, color=INK2, maxw=half)
    T(dx + half / 2, 110.8, "Fig. 5c; 11 products", pt=6, color=INK2, maxw=half)
    T(dx + half / 2, 113.2, "none for diagnosis", pt=6, color=INK2, maxw=half)
    note(x + 3, 118.8, "Pituitary trial removed after screening (78 to 77).", w - 6)


def build():
    lw, gap = 56.5, 6.0
    lane_literature(0.5, lw)
    lane_kb(0.5 + lw + gap, lw)
    lane_trials(0.5 + 2 * (lw + gap), lw)


def main():
    build()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">'
           f'<rect width="{W}" height="{H}" fill="white"/>' + "".join(out) + "</svg>")
    base = str(config.fig_path("figS1_workflow"))
    open(base + ".svg", "w").write(svg)
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:{W}mm {H}mm;margin:0}}'
            f'html,body{{margin:0;padding:0}}svg{{display:block}}</style></head><body>{svg}</body></html>')
    open(base + ".html", "w").write(html)
    prof = str(config.fig_path(".chrome_profile"))          # own profile: no clash with open Chrome
    common = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
              f"--user-data-dir={prof}"]
    subprocess.run(common + ["--no-pdf-header-footer", f"--print-to-pdf={base}.pdf", f"file://{base}.html"],
                   check=True, capture_output=True, timeout=120)
    print("written ->", base + ".{svg,html,pdf}")
    for w_ in warnings:
        print("WARNING", w_)


if __name__ == "__main__":
    main()
