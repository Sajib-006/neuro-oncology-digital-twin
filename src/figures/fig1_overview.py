"""Figure 1: the landscape of AI in neuro-oncology and the gaps measured in this review.

Input : icons in src/figures/icons_overview/svg (Bioicons; licenses in CREDITS.txt there). No data.
Output: FIG_DIR/fig1_overview.pptx, an editable PowerPoint slide (10 x 10 in; printed at 183 mm
        wide, 10 pt on the slide is 7.2 pt). The paper's PDF was exported from this file with
        PowerPoint (File > Save as > PDF); LibreOffice also works:
        soffice --headless --convert-to pdf fig1_overview.pptx
Each part's content block is placed by a small search so that it stays inside its wedge, and
every tumor label and key is checked against the ring; any overlap is printed as a WARNING.
Needs python-pptx, cairosvg (with the cairo library) and Pillow, and Arial (FONT_DIR or system).
Run: python src/figures/fig1_overview.py
"""
import io, math, os, sys
from PIL import Image, ImageOps, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "icons_overview")
sys.path.insert(0, ICON)
sys.path.insert(0, os.path.join(HERE, ".."))
from topng import png as svg_png  # noqa: E402
import config  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else str(config.fig_path("fig1_overview.pptx"))
FONT = "Arial"


def _font(name):
    for d in [os.environ.get("FONT_DIR", os.path.join(HERE, "fonts")), "/System/Library/Fonts/Supplemental",
              "/Library/Fonts", "/usr/share/fonts/truetype/msttcorefonts", "C:/Windows/Fonts"]:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    sys.exit(f"{name} not found; put Arial in FONT_DIR (needed to measure text widths)")


FONT_FILES = {False: _font("Arial.ttf"), True: _font("Arial Bold.ttf")}
INK, MUTED = "1F1F1F", "3A3A3A"

W = H = 10.0
CX, CY, R_OUT, R_IN = 5.0, 5.0, 4.88, 2.2
START = -112.5            # center angle of part 1 (deg, clockwise from 3 o'clock); 45 deg per part
K = 1.0                  # icon scale
T_SIZE, TASK_SIZE, LBL_SIZE = 13.5, 10.5, 10

# groups: data types / combining and grounding / reaching patients (tints of NPG colors)
G = {"data": ("D5DFEF", "E5ECF6", "2F4A80"),
     "comb": ("CBE9E0", "DDF1EB", "00745F"),
     "pat":  ("FADBD1", "FADBD1", "B23A26")}

PARTS = [  # title lines, task lines, group, icon set, gap number, chips (example models or resources)
    (["Imaging"], ["Tumor segmentation", "Grade and IDH status", "Response, pseudoprogression"],
     "data", "imaging", None, ["nnU-Net", "CNN", "ViT"]),
    (["Pathology"], ["Diagnosis and grading", "IDH, MGMT from slides", "Links to cell states"],
     "data", "pathology", None, ["MIL", "UNI", "Virchow"]),
    (["Molecular omics"], ["DNA, RNA, methylation", "Tumor classification", "Liquid biopsy"],
     "data", "omics", None, ["Rapid-CNS2", "MNP-Flex"]),
    (["Single-cell and", "spatial omics"], ["Cell states", "Tissue niches", "Histology to expression"],
     "data", "spatial", None, ["Thor", "NePSTA"]),
    (["Clinical text and", "language models"], ["Reading reports", "Treatment advice", "Few external tests"],
     "data", "text", None, ["ChatGPT", "GPT-4"]),
    (["Combining", "data types"], ["One model, many inputs", "Survival and subtype", "Rare in published work"],
     "comb", "fusion", 2, ["Pathomic Fusion"]),
    (["Knowledge bases"], ["Genes and drugs per tumor", "Uneven across tumors"],
     "comb", "kb", 1, ["Open Targets", "CTD", "DisGeNET"]),
    (["Trials, devices", "and surgery"], ["Diagnosis during surgery", "Trial results not posted",
     "Few cleared devices"], "pat", "clinic", 3, ["SRH", "FastGlioma", "Sturgeon"]),
]
GAPS = [("1", "Uneven tumor knowledge"), ("2", "Data types studied apart"),
        ("3", "Little patient testing")]

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
s = prs.slides.add_slide(prs.slide_layouts[6])
SH = s.shapes


def rgb(h):
    return RGBColor.from_string(h)


def polar(r, deg, cx=CX, cy=CY):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def text_w(line, size, bold=False):
    f = ImageFont.truetype(FONT_FILES[bold], 200)
    return f.getlength(line) / 200 * size / 72          # inches


def set_alpha(shape, alpha):
    clr = shape.fill._xPr.find(qn("a:solidFill"))[0]
    a = etree.SubElement(clr, qn("a:alpha")); a.set("val", str(int(alpha * 100000)))


def no_line(sh):
    sh.line.fill.background()


def text(x, y, w, h, lines_, size=12, bold=False, color=INK, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, spacing=1.0, wrap=False):
    tb = SH.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, ln in enumerate(lines_):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = spacing
        r = p.add_run(); r.text = ln
        f = r.font; f.name = FONT; f.size = Pt(size); f.bold = bold; f.color.rgb = rgb(color)
    return tb


_cache = {}


def icon_img(name, px=800, gray=False):
    key = (name, gray)
    if key not in _cache:
        im = svg_png(os.path.join(ICON, "svg", name), px)
        if gray:
            a = im.split()[-1]
            g = ImageOps.autocontrast(ImageOps.grayscale(im.convert("RGB")), cutoff=1)
            im = Image.merge("RGBA", (g, g, g, a))
        b = io.BytesIO(); im.save(b, "PNG")
        _cache[key] = (b.getvalue(), im.size)
    return _cache[key]


def pic(name, cx, cy, w=None, h=None, gray=False):
    data, (pw, ph) = icon_img(name, gray=gray)
    if w and not h: h = w * ph / pw
    if h and not w: w = h * pw / ph
    return SH.add_picture(io.BytesIO(data), Inches(cx - w / 2), Inches(cy - h / 2), Inches(w), Inches(h))


def oval(cx, cy, w, h, fill, line=None, lw=0.75):
    o = SH.add_shape(MSO_SHAPE.OVAL, Inches(cx - w / 2), Inches(cy - h / 2), Inches(w), Inches(h))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(fill)
    if line: o.line.color.rgb = rgb(line); o.line.width = Pt(lw)
    else: no_line(o)
    o.shadow.inherit = False
    return o


def rect(x, y, w, h, fill, line=None, radius=0.12):
    r = SH.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.adjustments[0] = radius
    r.fill.solid(); r.fill.fore_color.rgb = rgb(fill)
    if line: r.line.color.rgb = rgb(line); r.line.width = Pt(0.75)
    else: no_line(r)
    r.shadow.inherit = False
    return r


def line(x1, y1, x2, y2, color="555555", w=1.0, arrow=False):
    c = SH.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(w)
    if arrow:
        t = etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd"))
        t.set("type", "triangle"); t.set("w", "med"); t.set("len", "med")
    return c


# ------------------------------------------------------------------ ring
def wedge(a0, a1, fill):
    pts = [polar(R_OUT, a0 + (a1 - a0) * k / 72) for k in range(73)] + \
          [polar(R_IN, a1 - (a1 - a0) * k / 72) for k in range(73)]
    fb = SH.build_freeform(Inches(pts[0][0]), Inches(pts[0][1]), scale=1.0)
    fb.add_line_segments([(Inches(x), Inches(y)) for x, y in pts[1:]], close=True)
    w = fb.convert_to_shape()
    w.fill.solid(); w.fill.fore_color.rgb = rgb(fill)
    w.line.color.rgb = rgb("FFFFFF"); w.line.width = Pt(3.5)
    w.shadow.inherit = False
    return w


for i, (title, tasks, grp, ic, gap, chips) in enumerate(PARTS):
    a = START + 45 * i
    light, alt, dark = G[grp]
    wedge(a - 22.5, a + 22.5, light if i % 2 == 0 else alt).name = f"part {i+1} {title[0]}"


# ------------------------------------------------------------------ icons per part (centered at cx, cy)
ICON_W, ICON_H = 1.72 * K, 0.84 * K


def icons(kind, cx, cy):
    k = K
    if kind == "imaging":                                    # MRI (T1-like) and PET-like slices
        for dx, glow in [(-0.42, "F0A23B"), (0.42, "FFD34D")]:
            rect(cx + (dx - 0.37) * k, cy - 0.37 * k, 0.74 * k, 0.74 * k, "111111")
            pic("DBCLS__Horizontal_plane_of_the_brain.svg", cx + dx * k, cy, h=0.63 * k, gray=True)
            o = oval(cx + (dx + 0.13) * k, cy - 0.12 * k, (0.19 if dx < 0 else 0.25) * k,
                     (0.17 if dx < 0 else 0.22) * k, glow); set_alpha(o, 0.95 if dx < 0 else 0.75)
            oval(cx + (dx + 0.13) * k, cy - 0.12 * k, 0.09 * k, 0.08 * k, "E64B35")
    elif kind == "pathology":                                # microscope and H&E slide
        pic("Servier__microscope.svg", cx - 0.45 * k, cy, h=0.84 * k)
        pic("Servier__glassslide-top.svg", cx + 0.4 * k, cy + 0.05 * k, w=0.9 * k)
        o = oval(cx + 0.5 * k, cy + 0.06 * k, 0.44 * k, 0.26 * k, "E9A3C9"); set_alpha(o, 0.9)
        for dx, dy in [(-0.1, -0.03), (0.02, 0.05), (0.12, -0.02), (0.05, -0.07), (-0.04, 0.06), (0.15, 0.06)]:
            oval(cx + (0.5 + dx) * k, cy + (0.06 + dy) * k, 0.05 * k, 0.05 * k, "6A3D9A")
    elif kind == "omics":                                    # DNA and sequencer
        pic("Servier__dna-1.svg", cx - 0.42 * k, cy, h=0.82 * k)
        pic("DBCLS__DNA_sequencer.svg", cx + 0.42 * k, cy + 0.04 * k, w=0.82 * k)
    elif kind == "spatial":                                  # spatial spots on tissue and a cell map
        ox = cx - 0.42 * k
        oval(ox, cy, 0.8 * k, 0.68 * k, "F6D7E4", line="D99AB8")
        cols = ["4DBBD5", "E64B35", "00A087", "3C5488", "F39B7F", "91D1C2"]
        for r_ in range(-3, 4):
            for c_ in range(-4, 5):
                x = ox + (c_ * 0.105 + (0.052 if r_ % 2 else 0)) * k; y = cy + r_ * 0.095 * k
                if ((x - ox) / (0.36 * k)) ** 2 + ((y - cy) / (0.3 * k)) ** 2 <= 1:
                    oval(x, y, 0.07 * k, 0.07 * k, cols[(r_ * 3 + c_ * 2 + 9) % 6])
        pic("James-Lloyd__SingleCell_Clustering_DataReduction_UMAP.svg", cx + 0.45 * k, cy, h=0.74 * k)
    elif kind == "text":                                     # report and a language model
        pic("notepad.svg", cx - 0.42 * k, cy + 0.02 * k, h=0.82 * k)
        for j in range(4):
            line(cx - 0.65 * k, cy + (-0.13 + j * 0.12) * k, cx + (-0.2 - (0.13 if j == 3 else 0)) * k,
                 cy + (-0.13 + j * 0.12) * k, color="7A8BA8", w=1.5)
        b = SH.add_shape(MSO_SHAPE.ROUNDED_RECTANGULAR_CALLOUT, Inches(cx + 0.06 * k), Inches(cy - 0.36 * k),
                         Inches(0.78 * k), Inches(0.52 * k))
        b.fill.solid(); b.fill.fore_color.rgb = rgb("3C5488"); no_line(b); b.shadow.inherit = False
        b.adjustments[0] = -0.35; b.adjustments[1] = 0.75
        tf = b.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = "LLM"
        r.font.name = FONT; r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = rgb("FFFFFF")
    elif kind == "fusion":                                   # three inputs into one network
        for j, c in enumerate(["3C5488", "E9A3C9", "00A087"]):
            y = cy + (-0.28 + j * 0.28) * k
            oval(cx - 0.66 * k, y, 0.18 * k, 0.18 * k, c)
            line(cx - 0.55 * k, y, cx - 0.27 * k, cy + (y - cy) * 0.3, color="777777", w=1.25, arrow=True)
        pic("Simon_Dürr__neural-network-1.svg", cx + 0.24 * k, cy, h=0.76 * k)
    elif kind == "kb":                                       # database and gene network
        pic("OpenClipart__database-colored.svg", cx - 0.45 * k, cy, h=0.76 * k)
        pic("ChenxinLi__Network.svg", cx + 0.4 * k, cy, h=0.7 * k)
    elif kind == "clinic":                                   # clinic visit and treatment
        pic("Examination_Man.svg", cx - 0.22 * k, cy, h=0.84 * k)
        pic("Marcel_Tisch__drugs.svg", cx + 0.58 * k, cy + 0.2 * k, w=0.52 * k)


def gap_marker(cx, cy, n, size=0.3):
    r = rect(cx - size / 2, cy - size / 2, size, size, "2B2B2B", radius=0.2)
    tf = r.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; run = p.add_run(); run.text = str(n)
    run.font.name = FONT; run.font.size = Pt(12); run.font.bold = True; run.font.color.rgb = rgb("FFFFFF")


# ------------------------------------------------------------------ fit each content block inside its wedge
LH_T, LH_K, GAP = T_SIZE / 72 * 1.08, TASK_SIZE / 72 * 1.12, 0.1
GAPSZ = 0.3


CHIP_SIZE, CHIP_H, CHIP_PAD, CHIP_GAP = 9, 0.21, 0.08, 0.05


def chips_w(chips):
    return sum(text_w(c, CHIP_SIZE, True) + 2 * CHIP_PAD for c in chips) + CHIP_GAP * (len(chips) - 1)


def block(title, tasks, gap, chips):
    """Rectangles of the block relative to its center: list of (x0, y0, x1, y1)."""
    tw = max(text_w(t, T_SIZE, True) for t in title) + (GAPSZ + 0.08 if gap else 0)
    kw = max(text_w(t, TASK_SIZE) for t in tasks)
    cw = chips_w(chips)
    th, kh = LH_T * len(title), LH_K * len(tasks)
    tot = th + GAP + ICON_H + GAP + kh + GAP + CHIP_H
    y0 = -tot / 2
    yk = y0 + th + 2 * GAP + ICON_H
    return [(-tw / 2, y0, tw / 2, y0 + th),
            (-ICON_W / 2, y0 + th + GAP, ICON_W / 2, y0 + th + GAP + ICON_H),
            (-kw / 2, yk, kw / 2, yk + kh),
            (-cw / 2, yk + kh + GAP, cw / 2, y0 + tot)], th, tot


def draw_chips(chips, cx, y, dark):
    x = cx - chips_w(chips) / 2
    for c in chips:
        w = text_w(c, CHIP_SIZE, True) + 2 * CHIP_PAD
        r = rect(x, y, w, CHIP_H, "FFFFFF", radius=0.5)
        r.line.color.rgb = rgb(dark); r.line.width = Pt(0.9)
        tf = r.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE; tf.word_wrap = False
        p_ = tf.paragraphs[0]; p_.alignment = PP_ALIGN.CENTER; run = p_.add_run(); run.text = c
        run.font.name = FONT; run.font.size = Pt(CHIP_SIZE); run.font.bold = True; run.font.color.rgb = rgb(dark)
        x += w + CHIP_GAP


def clearance(rects, bx, by, a0, a1):
    worst = 9
    u0 = (math.cos(math.radians(a0)), math.sin(math.radians(a0)))
    u1 = (math.cos(math.radians(a1)), math.sin(math.radians(a1)))
    for x0, y0, x1, y1 in rects:
        for t in range(11):
            f = t / 10
            for px, py in [(x0 + f * (x1 - x0), y0), (x0 + f * (x1 - x0), y1),
                           (x0, y0 + f * (y1 - y0)), (x1, y0 + f * (y1 - y0))]:
                X, Y = bx + px - CX, by + py - CY
                rho = math.hypot(X, Y)
                d0 = u0[0] * Y - u0[1] * X            # >0 inside (clockwise of a0)
                d1 = u1[1] * X - u1[0] * Y            # >0 inside (anticlockwise of a1)
                worst = min(worst, rho - R_IN, R_OUT - rho, d0, d1)
    return worst


for i, (title, tasks, grp, ic, gap, chips) in enumerate(PARTS):
    a = START + 45 * i
    light, alt, dark = G[grp]
    rects, th, tot = block(title, tasks, gap, chips)
    best = None
    for rr in [R_IN + 0.3 + 0.05 * j for j in range(int((R_OUT - R_IN - 0.6) / 0.05) + 1)]:
        for da in [-10 + 0.5 * j for j in range(41)]:
            bx, by = polar(rr, a + da)
            c = clearance(rects, bx, by, a - 22.5, a + 22.5)
            score = c - 0.02 * abs(da) / 10 - 0.03 * abs(rr - (R_IN + R_OUT) / 2)
            if best is None or score > best[0]:
                best = (score, c, bx, by)
    _, c, bx, by = best
    print(f"part {i+1} {title[0]:<18} clearance {c:.2f} in")
    top = by - tot / 2
    tw = max(text_w(t, T_SIZE, True) for t in title)
    shift = -(GAPSZ + 0.08) / 2 if gap else 0
    text(bx + shift - tw / 2 - 0.05, top, tw + 0.1, th, title, size=T_SIZE, bold=True, color=dark, spacing=0.92)
    if gap:
        gap_marker(bx + shift + tw / 2 + 0.08 + GAPSZ / 2, top + LH_T / 2, gap, GAPSZ)
    icons(ic, bx, top + th + GAP + ICON_H / 2)
    kw = max(text_w(t, TASK_SIZE) for t in tasks)
    text(bx - kw / 2 - 0.05, top + th + 2 * GAP + ICON_H, kw + 0.1, LH_K * len(tasks), tasks,
         size=TASK_SIZE, color=MUTED, spacing=0.95)
    draw_chips(chips, bx, top + th + 3 * GAP + ICON_H + LH_K * len(tasks), dark)

# ------------------------------------------------------------------ center: brain and the ten tumor classes
# Servier brain-2 is a lateral view facing right: frontal lobe right, cerebellum lower left.
BW_, BCX, BCY = 1.6, CX, CY - 0.75
brain = pic("Servier__brain-2.svg", BCX, BCY, w=BW_)
bh = brain.height / 914400
bl, bt = BCX - BW_ / 2, BCY - bh / 2


def B(fx, fy):
    return bl + fx * BW_, bt + fy * bh


def inside_center(x0, y0, x1, y1, m=0.06):
    return all(math.hypot(x - CX, y - CY) <= R_IN - m for x in (x0, x1) for y in (y0, y1))


def label(lines_, x, y, align, anchor_frac, side):
    """side 'right': x is the label's right edge; 'left': left edge; 'above': x is the center.
    A line joins the label to a dot on the brain."""
    ws = [text_w(t, LBL_SIZE) for t in lines_]
    w = max(ws) + 0.04
    lh = LBL_SIZE / 72 * 1.1
    h = lh * len(lines_)
    x0 = {"right": x - w, "left": x}.get(side, x - w / 2)
    text(x0, y - h / 2, w, h, lines_, size=LBL_SIZE, align=align, spacing=0.92)
    for j, wj in enumerate(ws):                     # check each line stays inside the center circle
        ly = y - h / 2 + j * lh
        lx0 = {PP_ALIGN.RIGHT: x0 + w - wj, PP_ALIGN.LEFT: x0}.get(align, x0 + (w - wj) / 2)
        if not inside_center(lx0, ly, lx0 + wj, ly + lh):
            print("  WARNING label outside center circle:", lines_[j])
    px, py = B(*anchor_frac)
    sx, sy = {"right": (x + 0.05, y), "left": (x - 0.05, y), "above": (x, y + h / 2 + 0.03)}[side]
    line(sx, sy, px, py, color="2F4A80", w=1.0)
    oval(px, py, 0.075, 0.075, "2F4A80")


label(["Meningioma"], BCX - 0.13, CY - 1.83, PP_ALIGN.CENTER, (0.42, 0.045), "above")
label(["Glioblastoma", "Astrocytoma", "Oligodendroglioma"], CX + 0.85, CY - 0.72, PP_ALIGN.LEFT,
      (0.75, 0.25), "left")
label(["Craniopharyngioma"], CX + 0.66, CY - 0.27, PP_ALIGN.LEFT, (0.58, 0.575), "left")
label(["Diffuse midline glioma"], CX + 0.3, CY + 0.08, PP_ALIGN.LEFT, (0.49, 0.72), "left")
label(["Medulloblastoma", "Ependymoma", "Pilocytic astrocytoma", "ATRT"], CX - 0.55, CY - 0.1,
      PP_ALIGN.RIGHT, (0.32, 0.7), "right")

text(CX - 1.5, CY + 0.36, 3.0, 0.52, ["AI toward precision", "neuro-oncology"], size=17, bold=True,
     color=INK, spacing=0.92)


# patient <-> digital twin loop (bottom of the center)
def tinted(name, color, px=600):
    key = (name, color)
    if key not in _cache:
        im = svg_png(os.path.join(ICON, "svg", name), px)
        a = im.split()[-1]
        out = Image.new("RGB", im.size, "#" + color)
        out.putalpha(a)
        b = io.BytesIO(); out.save(b, "PNG"); _cache[key] = (b.getvalue(), out.size)
    return _cache[key]


def arc(cx, cy, r, a0, a1, color="555555", w=1.5):
    sh_ = SH.add_shape(MSO_SHAPE.ARC, Inches(cx - r), Inches(cy - r), Inches(2 * r), Inches(2 * r))
    sh_.adjustments[0] = a0; sh_.adjustments[1] = a1
    sh_.fill.background()
    sh_.line.color.rgb = rgb(color); sh_.line.width = Pt(w); sh_.shadow.inherit = False
    t = etree.SubElement(sh_.line._get_or_add_ln(), qn("a:tailEnd"))
    t.set("type", "triangle"); t.set("w", "med"); t.set("len", "med")


LY = CY + 1.38                                  # loop center line
PX, TX = CX - 0.58, CX + 0.58
pic("Marcel_Tisch__patient.svg", PX, LY, h=0.56)
data, (pw, ph) = tinted("Marcel_Tisch__patient.svg", "2F4A80")
hh = 0.46; ww = hh * pw / ph
oval(TX, LY, 0.6, 0.6, "E5ECF6", line="4DBBD5", lw=1.25)
SH.add_picture(io.BytesIO(data), Inches(TX - ww / 2), Inches(LY - hh / 2), Inches(ww), Inches(hh))
arc(CX, LY + 0.03, 0.3, 0.6 * 200, 0.6 * 340, color="4D6A9C")     # top: patient data to the twin
arc(CX, LY - 0.03, 0.3, 0.6 * 20, 0.6 * 160, color="4D6A9C")      # bottom: forecasts back to care
text(PX - 0.4, LY + 0.32, 0.8, 0.16, ["Patient"], size=9.5, bold=True, color=INK)
text(TX - 0.5, LY + 0.34, 1.0, 0.16, ["Digital twin"], size=9.5, bold=True, color="2F4A80")

# ------------------------------------------------------------------ keys (three corners outside the ring)
KS, KR, KM = 9.5, 0.25, 0.12          # key text size, row height, margin from the slide edge


def key(corner, title, rows):
    """rows: list of (kind, value, label); kind 'gap', 'swatch' or 'chip'. Checks the ring is clear."""
    chip_w = text_w("CNN", CHIP_SIZE, True) + 2 * CHIP_PAD + 0.1
    lw = max([text_w(title, KS, True)] + [text_w(l, KS) + (chip_w if k in ("chip", "blank") else 0.3)
                                          for k, v, l in rows]) + 0.04
    h = 0.22 + KR * len(rows)
    x0 = KM if "l" in corner else W - KM - lw
    y0 = KM if "t" in corner else H - KM - h
    xi, yi = (x0 + lw, y0 + h) if corner == "tl" else (x0, y0 + h) if corner == "tr" else \
             (x0 + lw, y0) if corner == "bl" else (x0, y0)
    if math.hypot(xi - CX, yi - CY) < R_OUT + 0.06:
        print("  WARNING key overlaps the ring:", title)
    text(x0, y0, lw + 0.1, 0.2, [title], size=KS, bold=True, align=PP_ALIGN.LEFT)
    for j, (k, v, l) in enumerate(rows):
        yc = y0 + 0.22 + KR * j + KR / 2
        if k == "gap":
            gap_marker(x0 + 0.11, yc, v, 0.21); tx = x0 + 0.3
        elif k == "swatch":
            rect(x0, yc - 0.1, 0.22, 0.2, G[v][0], line=G[v][2], radius=0.2); tx = x0 + 0.3
        elif k == "blank":
            tx = x0 + text_w("CNN", CHIP_SIZE, True) + 2 * CHIP_PAD + 0.1
        else:
            draw_chips([v], x0 + (text_w(v, CHIP_SIZE, True) + 2 * CHIP_PAD) / 2, yc - CHIP_H / 2, "2F4A80")
            tx = x0 + text_w(v, CHIP_SIZE, True) + 2 * CHIP_PAD + 0.1
        text(tx, yc - 0.09, lw, 0.18, [l], size=KS, align=PP_ALIGN.LEFT)


key("tl", "Ring colors", [("swatch", "data", "Data types"), ("swatch", "comb", "Combining, grounding"),
                          ("swatch", "pat", "Reaching patients")])
key("tr", "Rounded labels", [("chip", "CNN", "Example models,"), ("blank", "", "tools and resources")])
key("bl", "Gaps measured here", [("gap", n, t) for n, t in GAPS])

prs.save(OUT)
print("saved", OUT)
