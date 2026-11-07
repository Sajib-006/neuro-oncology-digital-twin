"""Clean and crop the Bioicons SVGs used in Figure 5 (kept as vector). Optional: the
cleaned files are already in icons_svg/.

Input : icons_svg_raw/*.svg   (files as downloaded from Bioicons)
Output: icons_svg/<name>.svg

For each file: replace Illustrator DTD entities with their values, drop the DOCTYPE and
Illustrator metadata, render once with cairosvg to find the drawn area, and set the
viewBox to that area plus a 2% margin. Sources and licenses: icons_svg/CREDITS.txt.
Needs cairosvg (pip install cairosvg) and the cairo library. On macOS with Homebrew:
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python src/figures/prep_svg_icons.py
"""
import io, os, re, glob
import numpy as np
import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW, OUT = os.path.join(HERE, "icons_svg_raw"), os.path.join(HERE, "icons_svg")


def clean(t):
    ents = dict(re.findall(r'<!ENTITY\s+(\w+)\s+"([^"]*)"\s*>', t))
    t = re.sub(r"<!DOCTYPE[^>\[]*(\[.*?\])?\s*>", "", t, flags=re.S)
    for k, v in ents.items():
        t = t.replace(f"&{k};", v)
    t = re.sub(r"<i:pgf[^>]*>.*?</i:pgf>", "", t, flags=re.S)
    t = re.sub(r"<metadata>.*?</metadata>", "", t, flags=re.S)
    t = re.sub(r"<\?xml[^>]*\?>", "", t)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    return t.strip()


def viewbox(t):
    m = re.search(r'<svg[^>]*\sviewBox="([^"]+)"', t)
    if m:
        return [float(v) for v in re.split(r"[ ,]+", m.group(1).strip())]
    w = float(re.search(r'<svg[^>]*\swidth="([\d.]+)', t).group(1))
    h = float(re.search(r'<svg[^>]*\sheight="([\d.]+)', t).group(1))
    return [0, 0, w, h]


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(RAW, "*.svg"))):
        t = clean(open(f, encoding="utf-8").read())
        x0, y0, w, h = viewbox(t)
        px = 1200
        png = cairosvg.svg2png(bytestring=t.encode(), output_width=px, unsafe=True)
        a = np.array(Image.open(io.BytesIO(png)).convert("RGBA"))[..., 3]
        ys, xs = np.nonzero(a > 8)
        s = w / a.shape[1]
        bx0, bx1 = x0 + xs.min() * s, x0 + (xs.max() + 1) * s
        by0, by1 = y0 + ys.min() * s, y0 + (ys.max() + 1) * s
        pad = 0.02 * max(bx1 - bx0, by1 - by0)
        vb = f"{bx0 - pad:.2f} {by0 - pad:.2f} {bx1 - bx0 + 2 * pad:.2f} {by1 - by0 + 2 * pad:.2f}"
        head = re.search(r"<svg\b[^>]*>", t).group(0)
        new = re.sub(r'\s(viewBox|width|height|x|y|style|enable-background)="[^"]*"', "", head)
        new = new.replace("<svg", f'<svg viewBox="{vb}"', 1)
        t = t.replace(head, new, 1)
        name = os.path.basename(f)
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(t)
        print(f"{name:40s} aspect w/h = {(bx1 - bx0) / (by1 - by0):.2f}  {len(t) // 1024} kB")


if __name__ == "__main__":
    main()
