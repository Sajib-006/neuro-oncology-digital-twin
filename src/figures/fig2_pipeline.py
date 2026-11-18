"""Figure 2: how the evidence in this review was built, as a visual left-to-right pipeline.
Three lanes (literature, knowledge bases, trials and devices) in the Fig. 1 ring colors; four arrow-shaped
stages per lane with a light-to-dark gradient; one icon, one number and two or three words per stage.
Icons: Bioicons (icons_overview/CREDITS.txt). Numbers as in Methods.
Run: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python fig2_pipeline_svg.py -> figures_out/fig2_pipeline.pdf
"""
import base64, io, os, subprocess, sys
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "icons_overview"))
from topng import png as svg_png  # noqa: E402

sys.path.insert(0, os.path.join(HERE, ".."))
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
PT = 25.4 / 72
W, H = 183.0, 100.0
INK, INK2 = "#1f1f1f", "#3d3d3d"
# lane: (dark, stage gradient from light to mid)
LANES = {"lit": ("#2F4A80", ["#EEF2FA", "#DCE5F4", "#C6D4EC", "#2F4A80"]),
         "kb": ("#00745F", ["#EAF6F2", "#D3EDE5", "#B8E1D4", "#00745F"]),
         "pat": ("#B23A26", ["#FDF0EC", "#FADDD3", "#F6C5B6", "#B23A26"])}
out, defs, warnings = [], [], []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tw(s, pt, bold=False):
    return (FONT_B if bold else FONT).getlength(s) / 200 * pt * PT


def T(x, y, s, pt=7, bold=False, color=INK, anchor="middle", maxw=None):
    if maxw and tw(s, pt, bold) > maxw + 0.01:
        warnings.append(f"too wide ({tw(s, pt, bold):.1f}>{maxw:.1f}): {s!r}")
    fw = ' font-weight="bold"' if bold else ""
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{pt * PT:.3f}" text-anchor="{anchor}" '
               f'fill="{color}"{fw}>{esc(s)}</text>')


_ic = {}


def icon(name, cx, cy, h, white=False):
    key = (name, white)
    if key not in _ic:
        im = svg_png(os.path.join(HERE, "icons_overview", "svg", name), 500)
        if white:
            from PIL import Image
            a = im.split()[-1]; im = Image.new("RGBA", im.size, (255, 255, 255, 255)); im.putalpha(a)
        b = io.BytesIO(); im.save(b, "PNG"); _ic[key] = (base64.b64encode(b.getvalue()).decode(), im.size)
    data, (pw, ph) = _ic[key]; w = h * pw / ph
    out.append(f'<image x="{cx - w / 2:.2f}" y="{cy - h / 2:.2f}" width="{w:.2f}" height="{h:.2f}" '
               f'href="data:image/png;base64,{data}"/>')


def grad(gid, c1, c2):
    defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>')


def chevron(x, y, w, h, fill, first=False, notch=4.0, stroke="none"):
    """Arrow-shaped stage: flat or notched left side, pointed right side."""
    left = f"M{x},{y} " if first else f"M{x},{y} L{x + notch},{y + h / 2} L{x},{y + h} "
    if first:
        d = (f"M{x + 1.5},{y} L{x + w - notch},{y} L{x + w},{y + h / 2} L{x + w - notch},{y + h} "
             f"L{x + 1.5},{y + h} Q{x},{y + h} {x},{y + h - 1.5} L{x},{y + 1.5} Q{x},{y} {x + 1.5},{y} Z")
    else:
        d = (f"M{x},{y} L{x + w - notch},{y} L{x + w},{y + h / 2} L{x + w - notch},{y + h} L{x},{y + h} "
             f"L{x + notch},{y + h / 2} Z")
    out.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="0.3"/>')


def rect(x, y, w, h, fill, r=1.5):
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" fill="{fill}"/>')


def circle(cx, cy, r, fill, stroke="none", sw=0.4):
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


# ------------------------------------------------------------------ drawn glyphs (icon-sized, centered)
def g_papers(cx, cy, col):
    for i in range(3):
        x, y = cx - 5.5 + i * 1.5, cy - 5 + i * 1.2
        out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="8.5" height="7.5" rx="0.6" fill="white" stroke="{col}" stroke-width="0.35"/>')
    for k in range(3):
        rect(cx - 1.6, cy - 0.6 + k * 1.5, 6.0 - (k == 2) * 2.0, 0.6, "#b9c4d8", 0.3)


def g_tags(cx, cy, col):
    for (dx, dy, w, fill) in [(-3.5, -2.3, 7.5, col), (4.0, -2.3, 6.0, "white"), (-2.5, 1.5, 6.0, "white"), (4.5, 1.5, 7.0, col)]:
        out.append(f'<rect x="{cx + dx - w / 2:.2f}" y="{cy + dy - 1.4:.2f}" width="{w}" height="2.8" rx="1.4" '
                   f'fill="{fill}" stroke="{col}" stroke-width="0.3"/>')


def g_matrix(cx, cy, col):
    pat = [[1, 1, 1, 1], [1, 1, 1, 0], [1, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]]
    for c in range(8):
        for r in range(4):
            rect(cx - 8 + c * 2.0, cy - 4 + r * 2.0, 1.65, 1.65, col if pat[c][r] else "#ffffff", 0.25)


def g_screen(cx, cy, col):
    for dx in (-4.0, 4.0):
        circle(cx + dx, cy, 3.2, "white", stroke=col, sw=0.4)
        out.append(f'<path d="M{cx + dx - 1.5},{cy} L{cx + dx - 0.3},{cy + 1.2} L{cx + dx + 1.7},{cy - 1.3}" '
                   f'fill="none" stroke="{col}" stroke-width="0.7" stroke-linecap="round" stroke-linejoin="round"/>')


def g_trend(cx, cy, col):
    x0, y0, w, h = cx - 7, cy - 4.5, 14, 9
    out.append(f'<path d="M{x0},{y0} V{y0 + h} H{x0 + w}" fill="none" stroke="white" stroke-width="0.4"/>')
    pts = [0.3, 0.8, 1.8, 3.4, 5.4, 7.4]
    d = " ".join(f"{'M' if i == 0 else 'L'}{x0 + 1 + i * 2.4:.2f},{y0 + h - 1 - v:.2f}" for i, v in enumerate(pts))
    out.append(f'<path d="{d}" fill="none" stroke="white" stroke-width="0.8" stroke-linecap="round"/>')
    d2 = " ".join(f"{'M' if i == 0 else 'L'}{x0 + 1 + i * 2.4:.2f},{y0 + h - 1.2:.2f}" for i in range(6))
    out.append(f'<path d="{d2}" fill="none" stroke="#A9BBDD" stroke-width="0.8" stroke-linecap="round"/>')


def g_bars(cx, cy, col):
    for i, v in enumerate([1.0, 0.72, 0.5, 0.34, 0.24, 0.15, 0.08, 0.04]):
        rect(cx - 8 + i * 2.1, cy + 4.5 - 9 * v, 1.5, max(9 * v, 0.3), "white", 0.2)


def g_lists(cx, cy, col):
    for i in range(4):
        rect(cx - 7, cy - 4.5 + i * 2.4, 2.0, 1.6, "white", 0.3)
        rect(cx - 4.2, cy - 4.3 + i * 2.4, 11 - (i % 2) * 3, 1.2, "#F3B9A9", 0.4)


# ------------------------------------------------------------------ layout
LX, LW = 0.5, 22.0
CX0, CW, CH, OV = LX + LW + 2.5, 40.0, 26.0, 1.3        # stages overlap slightly (arrow look)
Y0, RG = 11.5, 4.2


def sx(i):
    return CX0 + i * (CW - OV)


def header():
    for i, lab in enumerate(["Data sources", "Records", "Analysis", "Results"]):
        x = sx(i) + (CW - 4) / 2 + (2 if i else 0)
        circle(x - tw(lab, 8, True) / 2 - 3.8, 6.0, 2.4, INK)
        T(x - tw(lab, 8, True) / 2 - 3.8, 7.05, str(i + 1), pt=6.8, bold=True, color="white")
        T(x, 7.1, lab, pt=8, bold=True, anchor="middle")


def lane(ri, key, name, purpose, lane_icon, stages):
    dark, fills = LANES[key]
    y = Y0 + ri * (CH + RG)
    circle(LX + LW / 2, y + 8.0, 7.2, fills[1])
    icon(lane_icon[0], LX + LW / 2, y + 8.0, lane_icon[1])
    for j, t in enumerate(name):
        T(LX + LW / 2, y + 19.0 + j * 3.1, t, pt=7.5, bold=True, color=dark, maxw=LW)
    for j, t in enumerate(purpose):
        T(LX + LW / 2, y + 19.0 + len(name) * 3.1 + 0.3 + j * 2.6, t, pt=6.2, color=INK2, maxw=LW + 1)
    for i, (glyph, big, small) in enumerate(stages):
        x = sx(i)
        last = i == 3
        gid = f"g_{key}_{i}"
        c2 = fills[i] if not last else dark
        grad(gid, fills[max(i - 1, 0)] if not last else "#4b6aa8" if key == "lit" else
             "#1f9a80" if key == "kb" else "#cf5a45", c2)
        chevron(x, y, CW, CH, f"url(#{gid})", first=(i == 0))
        cx = x + CW / 2 + (1.2 if i else -0.6)
        txt = "white" if last else dark
        if isinstance(glyph, tuple):
            icon(glyph[0], cx, y + 7.0, glyph[1], white=last)
        else:
            glyph(cx, y + 7.0, dark)
        T(cx, y + 15.8, big, pt=8.5, bold=True, color=txt, maxw=CW - 9)
        for k, line in enumerate(small):
            T(cx, y + 19.3 + k * 2.75, line, pt=6.5, color="white" if last else INK2, maxw=CW - 8.5)


def build():
    header()
    lane(0, "lit", ["Literature"], ["what AI studies"], ("notepad.svg", 8.5), [
        (("OpenClipart__database-colored.svg", 9.5), "Scopus search", ["tumor terms AND AI terms", "2015 to 2026"]),
        (g_papers, "13,423 papers", ["AI research articles", "reviews removed"]),
        (g_tags, "Keyword tags", ["data types, tasks, models", "hand check, \u03ba = 0.92"]),
        (g_trend, "1.8%", ["name 2+ data types", "Fig. 4, gap 2"]),
    ])
    lane(1, "kb", ["Knowledge", "bases"], ["genes per tumor"], ("Servier__dna-1.svg", 10.0), [
        (("ChenxinLi__Network.svg", 8.5), "3 resources", ["Open Targets, CTD,", "DisGeNET"]),
        (g_matrix, "10 tumor classes", ["gene \u00d7 tumor maps", "two evidence levels"]),
        (("Servier__brain-2.svg", 10.0), "Similarity test", ["versus coverage:", "planned test failed"]),
        (g_bars, "3 vs 779 genes", ["curated, DMG vs GBM", "Fig. 3, gap 1"]),
    ])
    lane(2, "pat", ["Trials and", "devices"], ["what reaches patients"], ("Marcel_Tisch__patient.svg", 10.0), [
        (("Examination_Man.svg", 10.0), "6,008 | 1,614", ["trials | FDA devices", "registry and FDA list"]),
        (("notepad.svg", 9.0), "118 | 35", ["name AI and", "a primary brain tumor"]),
        (g_screen, "Two screeners", ["\u03ba = 0.81 | 0.20", "third reviewer settles"]),
        (g_lists, "77 | 12", ["0 of 28 overdue trials", "posted results; Fig. 5"]),
    ])


def main():
    build()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" '
           f'font-family="Arial, Helvetica, sans-serif"><defs>{"".join(defs)}</defs>'
           f'<rect width="{W}" height="{H}" fill="white"/>' + "".join(out) + "</svg>")
    base = str(config.fig_path("fig2_pipeline"))
    open(base + ".svg", "w").write(svg)
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:{W}mm {H}mm;margin:0}}'
            f'html,body{{margin:0;padding:0}}svg{{display:block}}</style></head><body>{svg}</body></html>')
    open(base + ".html", "w").write(html)
    prof = str(config.fig_path(".chrome_profile"))
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={prof}",
                    "--no-pdf-header-footer", f"--print-to-pdf={base}.pdf", f"file://{base}.html"],
                   check=True, capture_output=True, timeout=120)
    print("written ->", base + ".pdf")
    for w in warnings:
        print("WARNING", w)


if __name__ == "__main__":
    main()
