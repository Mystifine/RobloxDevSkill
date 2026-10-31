"""Renders beside their reference, for the clay check (references/modeling.md): python ref_sheet.py OUT.png IMAGE [IMAGE ...] [--height 640].

Each image is cropped to what stands out from its corner's color and scaled to one height, so proportions compare directly. List a
reference, then the render of the same view. An image that fills its frame, a turnaround on a busy background, stays whole. Needs Pillow."""
import argparse

from PIL import Image


def figure(path, height):
    im = Image.open(path).convert('RGB')
    r0, g0, b0 = im.getpixel((2, 2))
    away = Image.eval(im.convert('L'), lambda v: 255 if abs(v - (r0 + g0 + b0) // 3) > 8 else 0)
    box = away.getbbox()
    if box and (box[2] - box[0]) * (box[3] - box[1]) < .95 * im.width * im.height:
        im = im.crop(box)
    return im.resize((round(im.width * height / im.height), height), Image.Resampling.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    ap.add_argument('out')
    ap.add_argument('images', nargs='+')
    ap.add_argument('--height', type=int, default=640)
    a = ap.parse_args()
    parts = [figure(path, a.height) for path in a.images]
    sheet = Image.new('RGB', (sum(p.width for p in parts) + 10 * (len(parts) - 1), a.height), (30, 30, 36))
    x = 0
    for part in parts:
        sheet.paste(part, (x, 0))
        x += part.width + 10
    sheet.save(a.out)
    print(a.out, sheet.size)


if __name__ == '__main__':
    main()
