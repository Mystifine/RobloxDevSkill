"""A clip's rendered PNG frames as one verified, looping GIF (references/animation/blender.md, Preview). Python 3 with Pillow 10-12.

    python gif_preview.py FRAMES_DIR OUT.gif [--glob 'walk_*.png'] [--fps 30] [--expected-frames N] [--exclude-last]

One adaptive palette (median cut, 254 colours) built from every frame, so colours do not flicker between frames; Floyd-Steinberg
dithering; loop forever, disposal 2, no optimisation. Frame times are whole centiseconds, spread so the total matches the rate:
24 frames at 30 fps are [30, 30, 40] * 8 ms, 800 ms in all. Two spare palette entries share the top-left pixel's colour and
alternate, so Pillow cannot merge an intended hold into one frame. The file is reopened and checked (frames, size, loop,
total time, disposal); exit 1 when a check fails. --exclude-last drops a rendered loop-closing frame (a loop's last key
repeats its first and must not play twice).

Adapted from animate-roblox-characters' build_animation_preview.py (MIT; THIRD_PARTY_NOTICES.md)."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sys


def _pillow():
    try:
        from PIL import Image, ImageSequence
    except ImportError as exc:
        raise RuntimeError('Pillow is required: pip install "Pillow>=10,<13"') from exc
    return Image, ImageSequence


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', Path(path).name)]


def durations(count, fps):
    """Milliseconds per frame, whole centiseconds, matching `fps` over the whole GIF."""
    if count < 1:
        raise ValueError('no frames')
    if not math.isfinite(fps) or fps <= 0 or fps > 100:
        raise ValueError('GIF fps must be above 0 and at most 100')
    per = Fraction(100, 1) / Fraction(str(fps))
    base, remainder = divmod(per.numerator, per.denominator)
    if base < 1:
        raise ValueError('a GIF frame cannot be shorter than 10 ms')
    out, error = [], 0
    for _ in range(count):
        cs = base
        error += remainder
        if error >= per.denominator:
            cs += 1
            error -= per.denominator
        out.append(cs * 10)
    return out


def _palette(images, colors=254, max_pixels=4_194_304):
    Image, _ = _pillow()
    edge = max(32, min(128, int(math.sqrt(max_pixels / len(images)))))
    columns = min(8, max(1, math.ceil(math.sqrt(len(images)))))
    sheet = Image.new('RGB', (columns * edge, math.ceil(len(images) / columns) * edge))
    for i, image in enumerate(images):
        sheet.paste(image.resize((edge, edge), Image.Resampling.LANCZOS), ((i % columns) * edge, (i // columns) * edge))
    return sheet.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)


def _keep_holds(frames):
    for i, frame in enumerate(frames):
        palette = list(frame.getpalette() or [])
        palette += [0] * (768 - len(palette))
        marker = int(frame.getpixel((0, 0)))
        rgb = palette[marker * 3:marker * 3 + 3]
        palette[254 * 3:256 * 3] = rgb + rgb
        frame.putpalette(palette)
        frame.putpixel((0, 0), 254 + i % 2)


def verify(path, frames, size, total_ms):
    Image, ImageSequence = _pillow()
    path = Path(path)
    with Image.open(path) as gif:
        times, disposals = [], []
        for frame in ImageSequence.Iterator(gif):
            times.append(int(frame.info.get('duration', 0)))
            disposals.append(int(getattr(gif, 'disposal_method', 0)))
        errors = []
        if gif.n_frames != frames:
            errors.append(f'{gif.n_frames} frames, expected {frames}')
        if gif.size != tuple(size):
            errors.append(f'size {gif.size}, expected {tuple(size)}')
        if gif.info.get('loop') != 0:
            errors.append('does not loop forever')
        if sum(times) != total_ms:
            errors.append(f'{sum(times)} ms in all, expected {total_ms}')
        if any(d != 2 for d in disposals):
            errors.append(f'disposal not 2: {sorted(set(disposals))}')
        return {'ok': not errors, 'path': str(path), 'frames': gif.n_frames, 'size': list(gif.size), 'ms': sum(times),
                'fps': round(gif.n_frames * 1000 / sum(times), 3) if sum(times) else None, 'bytes': path.stat().st_size, 'errors': errors}


def build(paths, out, fps=30.0, expected=None):
    Image, _ = _pillow()
    paths = sorted((Path(p) for p in paths), key=natural_key)
    images = []
    for p in paths:
        with Image.open(p) as source:
            images.append(source.convert('RGB'))
    if not images:
        raise ValueError('no frames found')
    if any(i.size != images[0].size for i in images):
        raise ValueError('frames differ in size')
    if expected is not None and len(images) != expected:
        raise ValueError(f'{len(images)} frames, expected {expected}')
    palette = _palette(images)
    frames = [i.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for i in images]
    _keep_holds(frames)
    times = durations(len(frames), fps)
    out = Path(out).with_suffix('.gif')
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=times, loop=0, disposal=2, optimize=False)
    return verify(out, len(frames), images[0].size, sum(times))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('frames', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--glob', default='*.png')
    ap.add_argument('--fps', type=float, default=30.0)
    ap.add_argument('--expected-frames', type=int)
    ap.add_argument('--exclude-last', action='store_true')
    a = ap.parse_args(argv)
    paths = sorted(a.frames.glob(a.glob), key=natural_key)
    if a.exclude_last:
        paths = paths[:-1]
    try:
        result = build(paths, a.out, a.fps, a.expected_frames)
    except Exception as exc:  # report every failure as JSON, like the checks
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
