"""Outline style of an icon set: which icons end in a white sticker border, and how thick it is.

Image viewers show transparency as white, which hides a white border; this measures it instead. It walks inward
from the transparent background one pixel ring at a time and reports how white each ring is. Prints the set's
styles and the icons that differ from the most common one; named icons also get their ring values.
Usage: uv run --with numpy --with pillow python icon_outlines.py <folder> [name ...]
"""
import os
import sys

import numpy as np
from PIL import Image


def rings(path, depth=6):
    rgba = np.asarray(Image.open(path).convert("RGBA")).astype(np.int16)
    inside = rgba[..., 3] > 200
    reached = rgba[..., 3] < 40
    light = rgba[..., :3].mean(axis=2) > 215
    whites = []
    for _ in range(depth):
        pad = np.pad(reached, 1, constant_values=True)
        near = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
        ring = inside & near & ~reached
        if not ring.any():
            break
        whites.append(float(light[ring].mean()))
        reached |= near
    return whites


def border(whites):
    """Thickest run of mostly white rings; a thin dark fringe may sit outside the white."""
    best = run = 0
    for value in whites:
        run = run + 1 if value >= 0.5 else 0
        best = max(best, run)
    return best


def style(width):
    return "white border" if width >= 2 else "no white border"


folder, named = sys.argv[1], sys.argv[2:]
widths, details = {}, {}
for name in sorted(os.listdir(folder)):
    stem, ext = os.path.splitext(name)
    if ext.lower() == ".png":
        whites = rings(os.path.join(folder, name))
        widths[stem], details[stem] = border(whites), whites

counts = {}
for width in widths.values():
    counts[style(width)] = counts.get(style(width), 0) + 1
common = max(counts, key=counts.get) if counts else "none"
print(f"{len(widths)} icons: " + ", ".join(f"{key} {value}" for key, value in sorted(counts.items())))
odd = sorted(stem for stem, width in widths.items() if style(width) != common)
if odd:
    print(f"differ from the set ({common}): " + ", ".join(f"{stem} ({widths[stem]} px)" for stem in odd))
for stem in named:
    if stem in widths:
        print(f"{stem}: {style(widths[stem])} ({widths[stem]} px); ring whiteness " + " ".join(f"{v:.2f}" for v in details[stem]))
    else:
        print(f"{stem}: not found in {folder}")
