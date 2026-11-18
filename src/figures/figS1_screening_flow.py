"""Supplementary Figure S1: PRISMA-style flow of trial and device screening (counts only, few words).
Counts as reported in Methods and Supplementary Note 3: trials 6,008 -> 5,299 -> 118 screened -> 78 after
the third review -> 77 after removing one pituitary trial; devices 1,614 -> 1,313 -> 1,305 texts read
(8 unreadable) -> 35 screened -> 12.
Run: python figS1_screening_flow_svg.py   -> figures_out/figS1_screening_flow.pdf
"""
import os, subprocess, sys
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

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
W, H = 183.0, 104.0
INK, INK2, MUTED, LINE = "#1f1f1f", "#444444", "#7a7a7a", "#8a8a8a"
DARK, MID, LIGHT = "#B23A26", "#FADBD1", "#FDF0EC"
GREY_L = "#F2F2F0"
out, warnings = [], []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tw(s, pt, bold=False):
    return (FONT_B if bold else FONT).getlength(s) / 200 * pt * PT


def T(x, y, s, pt=6.5, bold=False, color=INK, anchor="middle", maxw=None):
    if maxw and tw(s, pt, bold) > maxw + 0.01:
        warnings.append(f"too wide ({tw(s, pt, bold):.1f}>{maxw:.1f}): {s!r}")
    fw = ' font-weight="bold"' if bold else ""
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{pt * PT:.3f}" text-anchor="{anchor}" '
               f'fill="{color}"{fw}>{esc(s)}</text>')


def rect(x, y, w, h, fill="white", stroke="none", sw=0.35, r=1.3, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" fill="{fill}" '
               f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(x1, y1, x2, y2):
    out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{LINE}" stroke-width="0.4"/>')
    if x1 == x2:      # down
        out.append(f'<path d="M{x2 - 0.9:.2f},{y2 - 1.3:.2f} L{x2:.2f},{y2:.2f} L{x2 + 0.9:.2f},{y2 - 1.3:.2f} Z" fill="{LINE}"/>')
    else:             # right
        out.append(f'<path d="M{x2 - 1.3:.2f},{y2 - 0.9:.2f} L{x2:.2f},{y2:.2f} L{x2 - 1.3:.2f},{y2 + 0.9:.2f} Z" fill="{LINE}"/>')


def main_box(x, y, w, h, num, label, fill="white", stroke=DARK, num_pt=9):
    rect(x, y, w, h, fill=fill, stroke=stroke)
    T(x + w / 2, y + h / 2 - 0.2, num, pt=num_pt, bold=True, color=DARK, maxw=w - 2)
    T(x + w / 2, y + h / 2 + 3.0, label, pt=6.5, color=INK, maxw=w - 2)


def excl_box(x, y, w, h, num, label, extra=None):
    rect(x, y, w, h, fill=GREY_L, stroke="#c9c9c4", sw=0.3)
    T(x + 2.0, y + h / 2 - 0.3 - (1.3 if extra else 0), num, pt=7.5, bold=True, color=INK2, anchor="start")
    T(x + 2.0 + tw(num, 7.5, True) + 1.5, y + h / 2 - 0.3 - (1.3 if extra else 0), label, pt=6.5, color=INK2,
      anchor="start", maxw=w - 4 - tw(num, 7.5, True))
    if extra:
        T(x + 2.0, y + h / 2 + 2.4, extra, pt=6, color=MUTED, anchor="start", maxw=w - 4)


def column(x0, letter, title, source, rows, final, final_note):
    """rows: list of (num, label, excl_num, excl_label, excl_extra, chip)"""
    mw, ew, gap = 40.0, 40.5, 5.5
    rect(x0, 2.0, mw + gap + ew, 8.0, fill=MID, r=1.6)
    T(x0 + 2.4, 7.5, letter, pt=8, bold=True, anchor="start")
    T(x0 + 6.4, 7.5, title, pt=7.5, bold=True, color=DARK, anchor="start")
    T(x0 + mw + gap + ew - 2.0, 7.5, source, pt=6, color=INK2, anchor="end")
    y, bh, step = 14.0, 10.5, 19.5
    for i, (num, lab, en, el, ex, chip) in enumerate(rows):
        main_box(x0, y, mw, bh, num, lab, fill=LIGHT if chip else "white")
        if chip:
            cw_ = tw(chip, 6, True) + 3.0
            rect(x0 + mw / 2 - cw_ / 2, y + bh - 1.6, cw_, 3.2, fill=DARK, r=1.6)
            T(x0 + mw / 2, y + bh + 0.6, chip, pt=6, bold=True, color="white")
        # exclusion branch
        arrow(x0 + mw, y + bh / 2, x0 + mw + gap, y + bh / 2)
        excl_box(x0 + mw + gap, y + 0.75, ew, bh - 1.5, en, el, ex)
        arrow(x0 + mw / 2, y + bh + (1.8 if chip else 0), x0 + mw / 2, y + step)
        y += step
    rect(x0, y, mw, bh + 1.5, fill=DARK, r=1.3)
    T(x0 + mw / 2, y + 5.0, final, pt=9.5, bold=True, color="white", maxw=mw - 2)
    T(x0 + mw / 2, y + 9.0, final_note, pt=6.5, color="white", maxw=mw - 2)


def build():
    column(0.5, "a", "Clinical trials", "ClinicalTrials.gov, 24 Sep 2026", [
        ("6,008", "studies, brain tumor query", "709", "brain metastases only", None, None),
        ("5,299", "on primary brain tumors", "5,181", "no AI or radiomics term", None, None),
        ("118", "screened by two people", "40", "not eligible", "after the third review", "κ = 0.81"),
        ("78", "after the third review", "1", "pituitary adenoma", "removed after screening", None),
    ], "77 trials", "Supplementary Table S7")
    column(94.0, "b", "AI-enabled devices", "FDA list, 4 Sep 2026", [
        ("1,614", "devices on the FDA list", "301", "other review panels", None, None),
        ("1,313", "radiology, neurology, pathology", "1,278", "no brain tumor named", "8 summaries unreadable", None),
        ("35", "screened by two people", "23", "not eligible", "after the third review", "κ = 0.20"),
    ], "12 devices", "11 products; Table S8")


def main():
    build()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" '
           f'font-family="Arial, Helvetica, sans-serif"><rect width="{W}" height="{H}" fill="white"/>'
           + "".join(out) + "</svg>")
    base = str(config.fig_path("figS1_screening_flow"))
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
