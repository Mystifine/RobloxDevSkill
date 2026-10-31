"""Second half of skin_kit.paint: inks a baked paint layer. Python with Pillow, outside Blender:

    python skin_ink.py paint.png strokes.json color.png height.png

strokes.json holds {"ink": [...], "shadow": [...], "light": [...]}, each stroke a flat list x0, y0, r0, x1, y1, r1, ... in
pixels of the paint layer (r the half width). Shadow and light are soft fold tones, blurred before they go down; ink is drawn
at four times the size and filtered down, so a tapered stroke keeps a smooth edge. The paint is eased first, which takes the
bake's noise out of its soft edges. height.png holds the same strokes as relief, for the normal map."""
import json
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SS = 4  # ink supersampling
INK = (20, 16, 18)
FOLD_SHADOW = (118, 106, 130)  # multiplied into the paint under a fold
FOLD_LIGHT = (255, 250, 240)


def draw(target, stroke, scale):
    """Quads between the stroke's points and discs on them, so joints stay round at any width."""
    d = ImageDraw.Draw(target)
    pts = [(stroke[i] * scale, stroke[i + 1] * scale, stroke[i + 2] * scale) for i in range(0, len(stroke), 3)]
    for (x0, y0, r0), (x1, y1, r1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = (dx * dx + dy * dy) ** .5
        if ln < 1e-6:
            continue
        nx, ny = -dy / ln, dx / ln
        d.polygon([(x0 + nx * r0, y0 + ny * r0), (x1 + nx * r1, y1 + ny * r1), (x1 - nx * r1, y1 - ny * r1), (x0 - nx * r0, y0 - ny * r0)], fill=255)
    for x, y, r in pts:
        if r > .4:
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)


def main():
    paint, strokes, out, height = sys.argv[1:5]
    base = Image.open(paint).convert('RGB').filter(ImageFilter.GaussianBlur(1.1))
    data = json.load(open(strokes, encoding='utf-8'))
    size = base.size
    ink = Image.new('L', (size[0] * SS, size[1] * SS), 0)
    shadow, light = Image.new('L', size, 0), Image.new('L', size, 0)
    for s in data.get('shadow', []):
        draw(shadow, s, 1)
    for s in data.get('light', []):
        draw(light, s, 1)
    for s in data.get('ink', []):
        draw(ink, s, SS)
    shadow = shadow.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .9))
    light = light.filter(ImageFilter.GaussianBlur(1.8)).point(lambda v: int(v * .55))
    result = Image.composite(ImageChops.multiply(base, Image.new('RGB', size, FOLD_SHADOW)), base, shadow)
    result = Image.composite(Image.new('RGB', size, FOLD_LIGHT), result, light)
    line = ink.resize(size, Image.Resampling.LANCZOS)
    result = Image.composite(Image.new('RGB', size, INK), result, line)
    result.save(out)
    # Relief: folds sink, their lit sides rise, and each line is a fine groove.
    relief = Image.new('L', size, 128)
    relief = Image.composite(Image.new('L', size, 70), relief, shadow.point(lambda v: int(v * .8)))
    relief = Image.composite(Image.new('L', size, 190), relief, light)
    relief = Image.composite(Image.new('L', size, 30), relief, line.filter(ImageFilter.GaussianBlur(.8)))
    relief.save(height)


if __name__ == '__main__':
    main()
