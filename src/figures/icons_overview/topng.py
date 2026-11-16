import re, sys, io, os, cairosvg
from PIL import Image, ImageDraw, ImageFont
def clean(s):
    ents = dict(re.findall(r'<!ENTITY\s+(\w+)\s+"([^"]*)"', s))
    s = re.sub(r'<!DOCTYPE[^\[]*\[.*?\]>', '', s, flags=re.S)
    s = re.sub(r'<!DOCTYPE[^>]*>', '', s)
    for k, v in ents.items(): s = s.replace(f'&{k};', v)
    return s
def png(path, px=600):
    s = clean(open(path, encoding='utf-8', errors='ignore').read())
    b = cairosvg.svg2png(bytestring=s.encode(), output_width=px)
    im = Image.open(io.BytesIO(b)).convert('RGBA'); bb = im.getbbox()
    im = im.crop(bb) if bb else im
    pad = int(0.03 * max(im.size)); out = Image.new('RGBA', (im.width + 2*pad, im.height + 2*pad), (0,0,0,0)); out.paste(im, (pad, pad)); return out
if __name__ == '__main__':
    os.makedirs('png', exist_ok=True); tiles = []
    for f in sorted(os.listdir('raw')):
        try: im = png('raw/'+f); im.save('png/'+f[:-4]+'.png'); tiles.append((f, im))
        except Exception as e: print('FAIL', f, e)
    W = 6; S = 220; H = (len(tiles)+W-1)//W
    sheet = Image.new('RGB', (W*S, H*(S+30)), 'white'); d = ImageDraw.Draw(sheet)
    for i, (f, im) in enumerate(tiles):
        t = im.copy(); t.thumbnail((S-20, S-20)); x, y = (i%W)*S, (i//W)*(S+30)
        sheet.paste(t, (x+10, y+10), t); d.text((x+5, y+S+5), f[:34], fill='black')
    sheet.save('sheet.png'); print(len(tiles))
