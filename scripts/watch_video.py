"""Watch a video as pictures and numbers (references/art/video.md). An agent cannot play a video, so this turns one into a
shot list, labelled contact sheets, a loudness timeline and stills, written to a folder; it prints only paths and a summary.

  python watch_video.py watch VIDEO [-o DIR] [--start T] [--end T]       everything below, once (start here)
  python watch_video.py sheet VIDEO -o OUT.png [--count 24 | --every S] [--start T] [--end T]
  python watch_video.py burst VIDEO --start T [--duration 1] [--fps 36] -o OUT.png   every new frame: motion, timing
  python watch_video.py frames VIDEO --at 1.5,0:03.2 -o DIR [--width W]           full-size stills
  python watch_video.py compare REFERENCE RECORDING --pairs 2.3=1.6,0:07=5.2 -o OUT.png   moments side by side
  python watch_video.py shots VIDEO [--threshold 0.35] [--min-shot 0.2]           cut times only
  python watch_video.py audio VIDEO [--bin 0.05]                                    loudness and onsets only
  python watch_video.py probe VIDEO                                                 streams as JSON
  python watch_video.py record OUT.mp4 --window TITLE [--seconds 10] [--fps 30] [--crop W:H:X:Y]   Windows: record a window
  python watch_video.py find | install                                              the ffmpeg in use / install it

VIDEO is a file or a direct media URL; a page (YouTube, a post) is not a video file. Times are seconds or [h:]m:ss[.ss].
Common options: --ffmpeg PATH, --cols N, --width PX (sheet width, default 1536), --scale PX (shot detection width).

Settings, measured on a 47 s, 640x348, 30 fps anime clip with flashes, quick cuts and a dissolve (docs/checks.md):
- Shots: every frame, 320 px wide (--scale), compared in RGB, scene threshold 0.35. On YUV input the scene score follows
  brightness, so a cut between two colors of equal brightness (red to green, black to blue) went unseen; in RGB all were
  found and the real clip kept every cut. Sampling 15 fps found 14 of its 28 cuts and 10 fps 11, saving 0.3 s: decoding
  dominates. Full size, 320 and 160 px found the same 28. Threshold 0.3 split a flashing effect 4 more times; 0.4 lost a
  real cut. Cuts under --min-shot (0.2 s) apart merge, and 3 or more shots in a row under 0.5 s are one rapid run (a
  flashing effect or stepped zooms, not separate shots). A dissolve or slow fade is not a cut: a long shot can hide one.
  A still border dilutes the score: the clip padded to 45% of the frame (the 3D view's share of a recorded Studio
  window) gave 6 of its 29 shots, and cropped back all 29. So `record --crop` keeps only the 3D view.
- Frames: one decode pass that keeps the frames asked for (1.1 s for 44 frames, against 4.9 s for 44 seeks) when the
  span is 2 minutes or less; seeks beyond that. A pass picks at most 60 frames: ffmpeg's select expression parsed 100 and failed at 110,
  so a 31 s clip of 46 shots could not be watched whole. Hardware decoding was slower on a short clip (start-up cost): not used.
- Sheets: 1536 px wide at most, 4 columns (6 for portrait video and bursts), tiles never larger than the source, each
  frame fitted whole within its tile. An image costs about width x height / 750 tokens to view: a 24-frame sheet
  (1534 x 1476) about 3,000, the timeline about 500.
- Shots sheet: each shot's in, middle and out frame, 0.1 s inside its cuts (a quarter of a shorter shot), two shots' worth a
  row (three for portrait video). The middle alone hid every camera move and the path of the action within a shot. The
  longer half of the shots, those of at least 0.75 s, show six frames instead of three: half as many frames again, spent
  where a shot has the most to hide (one 6.8 s shot held four beats that in, middle and out skipped), at the same tile size.
- Compare: a reference moment and the recording's beside it, two pairs a row, so the picture is checked, not only timing.
- Burst: duplicates dropped (mpdecimate), then at most --fps 36 a second, each tile labelled with its source frame. The
  clip held about 24 new images a second though stored at 30, so 12 fps would skip every other drawing, impact frames
  included; a 30 fps source keeps every new frame and a 60 fps recording is thinned to 36. Gaps in the frame numbers are holds.
- Audio: decoded at 8 kHz mono, 0.05 s bins (under two frames at 30 fps), onsets at a 9 dB rise above -45 dBFS.

ffmpeg comes from --ffmpeg, FFMPEG, the PATH, then the usual install folders (winget, Chocolatey, Scoop, Homebrew, /usr),
so an install made after the shell started is still found. Sheets and the timeline need Pillow.
Exit codes: 0 done, 1 ffmpeg failed, 2 bad arguments or unreadable input, 3 ffmpeg or Pillow missing (the message says how
to install it: ask the user first)."""
import argparse
import array
from concurrent.futures import ThreadPoolExecutor
import glob
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

SHEET_WIDTH = 1536
MAX_EDGE = 1536
SCENE = 0.35
MIN_SHOT = 0.2
SCALE = 320
RAPID = 0.5  # shots shorter than this, three or more in a row, are one rapid run
EDGE = 0.1  # seconds inside each cut for a shot's in and out frames
GROUP_GAP = 14  # px between groups of tiles in a row: one shot's three, or one compared pair
ONE_PASS = 120.0  # seconds: decode once for frames up to this span, seek beyond it
PASS_FRAMES = 60  # frames one decode pass picks: ffmpeg's select expression parsed 100 and failed at 110
OVERVIEW = 24  # frames in `watch`'s overview, and in a `sheet` unless told otherwise
LONG_SHOT = 0.75  # seconds: a shot this long, in the longer half of its video, shows LONG_FRAMES instead of 3
LONG_FRAMES = 6  # twice 3, so a long shot takes a whole row of the shots sheet
BURST_FPS = 36
AUDIO_RATE = 8000
AUDIO_BIN = 0.05
ONSET_RISE = 9.0  # dB above the quietest of the last few bins
ONSET_FLOOR = -45.0  # dBFS: quieter rises are noise
SILENCE = -50.0
INSTALL = {
    'Windows': ['winget', 'install', '--id', 'Gyan.FFmpeg', '-e', '--accept-source-agreements', '--accept-package-agreements'],
    'Darwin': ['brew', 'install', 'ffmpeg'],
    'Linux': ['sudo', 'apt-get', 'install', '-y', 'ffmpeg'],
}


class Missing(Exception):
    """ffmpeg, ffprobe or Pillow is not installed."""


class Failed(Exception):
    """ffmpeg ran and failed."""


# ---------------------------------------------------------------------------------------------------------- finding ffmpeg

def candidates(system=None, env=None):
    """Where ffmpeg may be, in the order they are tried after --ffmpeg, FFMPEG and the PATH."""
    system = system or platform.system()
    env = env if env is not None else os.environ
    if system == 'Windows':
        local, home = env.get('LOCALAPPDATA', ''), env.get('USERPROFILE', '')
        found = [os.path.join(local, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe')]
        found += sorted(glob.glob(os.path.join(local, 'Microsoft', 'WinGet', 'Packages', '*FFmpeg*', '*', 'bin', 'ffmpeg.exe')), reverse=True)
        found += [os.path.join(env.get('ProgramData', r'C:\ProgramData'), 'chocolatey', 'bin', 'ffmpeg.exe'),
                  os.path.join(home, 'scoop', 'shims', 'ffmpeg.exe'), r'C:\ffmpeg\bin\ffmpeg.exe']
        return found
    if system == 'Darwin':
        return ['/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg']
    return ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/snap/bin/ffmpeg']


def find_ffmpeg(explicit=None):
    """(ffmpeg, ffprobe) paths, or Missing with the install command for this system."""
    for path in [explicit, os.environ.get('FFMPEG'), shutil.which('ffmpeg'), *candidates()]:
        if path and os.path.isfile(path):
            probe = os.path.join(os.path.dirname(path), 'ffprobe' + ('.exe' if path.lower().endswith('.exe') else ''))
            probe = probe if os.path.isfile(probe) else shutil.which('ffprobe')
            if probe:
                return path, probe
    raise Missing('ffmpeg is not installed. Ask the user, then run: python watch_video.py install  (' + ' '.join(INSTALL.get(platform.system(), INSTALL['Linux'])) + ')')


def pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise Missing('Pillow is not installed: pip install Pillow')
    return Image, ImageDraw, ImageFont


def font(ImageFont, size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow before 10.1
        return ImageFont.load_default()


# --------------------------------------------------------------------------------------------------------------- helpers

def parse_time(text):
    """Seconds from `12.5`, `1:02.5` or `1:01:02.5`."""
    if text is None or text == '':
        return None
    parts = str(text).strip().split(':')
    if len(parts) > 3:
        raise ValueError(f'not a time: {text}')
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    if seconds < 0 or seconds != seconds:
        raise ValueError(f'not a time: {text}')
    return seconds


def stamp(seconds):
    """`0:03.25`, or `1:02:03.25` past an hour."""
    seconds = max(0.0, seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours >= 1:
        return f'{int(hours)}:{int(minutes):02d}:{secs:05.2f}'
    return f'{int(minutes)}:{secs:05.2f}'


def run(cmd, binary=False):
    done = subprocess.run(cmd, capture_output=True)
    if done.returncode != 0:
        tail = done.stderr.decode('utf-8', 'replace').strip().splitlines()[-4:]
        raise Failed(' | '.join(tail) or f'{cmd[0]} exited {done.returncode}')
    return done if binary else SimpleText(done)


class SimpleText:
    def __init__(self, done):
        self.stdout = done.stdout.decode('utf-8', 'replace')
        self.stderr = done.stderr.decode('utf-8', 'replace')


def even_times(start, end, count):
    """`count` moments spread over [start, end): the middle of each equal part, so neither black edge frame is picked."""
    step = (end - start) / count
    return [start + (i + 0.5) * step for i in range(count)]


def every_times(start, end, every):
    times, t = [], start
    while t < end - 1e-9:
        times.append(t)
        t += every
    return times


# ------------------------------------------------------------------------------------------------------------------ probe

def probe(tools, video):
    out = run([tools[1], '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', video]).stdout
    data = json.loads(out)
    info = {'file': video, 'duration': float(data.get('format', {}).get('duration') or 0), 'video': None, 'audio': None}
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video' and info['video'] is None and stream.get('disposition', {}).get('attached_pic') != 1:
            num, _, den = (stream.get('avg_frame_rate') or '0/1').partition('/')
            fps = float(num) / float(den or 1) if float(den or 1) else 0.0
            width, height = int(stream.get('width') or 0), int(stream.get('height') or 0)
            rotation = 0
            for side in stream.get('side_data_list', []):
                rotation = int(side.get('rotation', rotation) or 0)
            rotation = int(stream.get('tags', {}).get('rotate', rotation) or 0)
            if abs(rotation) % 180 == 90:  # ffmpeg turns the picture upright when decoding
                width, height = height, width
            info['video'] = {'codec': stream.get('codec_name'), 'width': width, 'height': height, 'fps': round(fps, 3),
                             'frames': int(stream['nb_frames']) if str(stream.get('nb_frames', '')).isdigit() else None}
            if not info['duration']:
                info['duration'] = float(stream.get('duration') or 0)
        elif stream.get('codec_type') == 'audio' and info['audio'] is None:
            info['audio'] = {'codec': stream.get('codec_name'), 'rate': int(stream.get('sample_rate') or 0), 'channels': stream.get('channels')}
    if not info['video'] and not info['audio']:
        raise ValueError(f'{video}: no video or audio stream')
    return info


def window(info, start, end):
    start = start or 0.0
    end = min(end, info['duration']) if end is not None else info['duration']
    if not end > start:
        raise ValueError(f'nothing between {stamp(start)} and {stamp(end)} (the video is {stamp(info["duration"])})')
    return start, end


# ----------------------------------------------------------------------------------------------------------------- frames

def grab(tools, video, t, out, width=None, info=None):
    """One frame at `t` seconds as a PNG; a moment past the last frame steps back until one decodes."""
    last = info['duration'] - 0.05 if info else t
    for back in (0.0, 0.25, 0.75):
        moment = max(0.0, min(t, last) - back)
        cmd = [tools[0], '-v', 'error', '-ss', f'{moment:.3f}', '-i', video, '-frames:v', '1']
        if width:
            cmd += ['-vf', f'scale={width}:-2']
        run(cmd + ['-y', out])
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
    raise Failed(f'no frame at {stamp(t)}')


def grab_pass(tools, video, times, folder, info, width=None, prefix='pass'):
    """Every frame in `times` from one decode of the span they cover, or None when the frames written do not match."""
    fps = (info.get('video') or {}).get('fps') or 0
    if not fps or not times:
        return None
    start, end = max(0.0, min(times) - 0.5), max(times) + 0.5
    wanted = {t: max(0, round((t - start) * fps)) for t in times}
    numbers = sorted(set(wanted.values()))
    chain = "select='" + '+'.join(f'eq(n\\,{n})' for n in numbers) + "'" + (f',scale={width}:-2' if width else '')
    pattern = os.path.join(folder, f'{prefix}_%04d.png')
    try:
        run([tools[0], '-v', 'error', '-ss', f'{start:.3f}', '-to', f'{end:.3f}', '-i', video, '-an', '-sn', '-vf', chain,
             '-fps_mode', 'passthrough', '-y', pattern])
    except Failed:  # (the seeks may still work)
        numbers = None
    written = sorted(glob.glob(os.path.join(folder, f'{prefix}_*.png')))
    if numbers is None or len(written) != len(numbers):  # past the last frame, or a variable frame rate
        for path in written:
            os.remove(path)
        return None
    by_number = dict(zip(numbers, written))
    return [by_number[wanted[t]] for t in times]


def grab_many(tools, video, times, folder, width=None, info=None, prefix='frame'):
    """A PNG per time, in order: decode passes of at most PASS_FRAMES frames when the times span ONE_PASS seconds or less, else
    a seek per frame, as when a pass fails."""
    os.makedirs(folder, exist_ok=True)
    if info and times and max(times) - min(times) <= ONE_PASS:
        ordered = sorted(set(times))
        found = {}
        for i in range(0, len(ordered), PASS_FRAMES):
            chunk = ordered[i:i + PASS_FRAMES]
            paths = grab_pass(tools, video, chunk, folder, info, width, f'{prefix}_pass{i}')
            if not paths:
                for path in set(found.values()):
                    os.remove(path)
                break
            found.update(zip(chunk, paths))
        else:
            return [found[t] for t in times]
    paths = [os.path.join(folder, f'{prefix}_{i + 1:03d}.png') for i in range(len(times))]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda job: grab(tools, video, job[0], job[1], width, info), zip(times, paths)))
    return paths


def burst_frames(tools, video, start, duration, cap, folder, width=None, unique=True, source_fps=None):
    """([path], [time]) of each new frame from `start` for `duration`: a source faster than `cap` resampled to it first
    (a gap rule would keep every other frame of 30 fps: 15, not 24), then repeats of the frame before dropped."""
    os.makedirs(folder, exist_ok=True)
    steps = [f'fps={cap:g}'] if not source_fps or source_fps > cap + 0.5 else []
    steps += ['mpdecimate'] if unique else []
    steps += [f'scale={width}:-2'] if width else []
    chain = ','.join(steps + ['showinfo'])
    done = run([tools[0], '-hide_banner', '-nostats', '-ss', f'{start:.3f}', '-t', f'{duration:.3f}', '-i', video, '-an', '-sn',
                '-vf', chain, '-fps_mode', 'passthrough', '-y', os.path.join(folder, 'burst_%03d.png')])
    paths = sorted(glob.glob(os.path.join(folder, 'burst_*.png')))
    times = [start + t for t in cut_times(done.stderr)]
    return paths, (times if len(times) == len(paths) else [start + i / cap for i in range(len(paths))])


# ------------------------------------------------------------------------------------------------------------------ shots

def cut_times(stderr):
    return [float(m) for m in re.findall(r'pts_time:\s*([0-9.]+)', stderr)]


def merge_cuts(cuts, min_shot, start=0.0, end=None):
    """Cuts at least `min_shot` from the last kept cut and from both ends: a flash cuts in and out a few frames apart."""
    kept = []
    for cut in sorted(cuts):
        if cut - (kept[-1] if kept else start) < min_shot or (end is not None and end - cut < min_shot):
            continue
        kept.append(cut)
    return kept


def shots(tools, video, info, start, end, threshold=SCENE, min_shot=MIN_SHOT, scale=SCALE):
    """[(start, end)] of each shot between `start` and `end`."""
    if not info['video']:
        return [(start, end)]
    # RGB: on YUV the score follows brightness and misses a cut between two colors of equal brightness.
    chain = (f'scale={scale}:-2,' if scale else '') + f"format=rgb24,select='gt(scene,{threshold})',showinfo"
    done = run([tools[0], '-hide_banner', '-nostats', '-ss', f'{start:.3f}', '-to', f'{end:.3f}', '-i', video, '-an', '-sn',
                '-vf', chain, '-f', 'null', '-'])
    cuts = merge_cuts([start + t for t in cut_times(done.stderr)], min_shot, start, end)
    edges = [start, *cuts, end]
    return list(zip(edges, edges[1:]))


# ------------------------------------------------------------------------------------------------------------------ audio

def levels(samples, rate, size):
    """dBFS (RMS) per bin of `size` seconds, from 16-bit samples."""
    step = max(1, int(round(rate * size)))
    out = []
    for i in range(0, len(samples), step):
        chunk = samples[i:i + step]
        if not chunk:
            break
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk)) / 32768.0
        out.append(round(20 * math.log10(rms), 1) if rms > 1e-5 else -100.0)
    return out


def onsets(db, size, rise=ONSET_RISE, floor=ONSET_FLOOR, look=3, gap=0.15):
    """Bin start times where loudness jumps `rise` dB over the quietest of the last `look` bins, above `floor`."""
    found = []
    for i in range(1, len(db)):
        before = min(db[max(0, i - look):i])
        if db[i] >= floor and db[i] - before >= rise and (not found or i * size - found[-1] >= gap):
            found.append(round(i * size, 3))
    return found


def silences(db, size, below=SILENCE, shortest=0.5):
    spans, begin = [], None
    for i, level in enumerate(db + [0.0]):
        if level < below and begin is None:
            begin = i
        elif level >= below and begin is not None:
            if (i - begin) * size >= shortest:
                spans.append((round(begin * size, 2), round(i * size, 2)))
            begin = None
    return spans


def audio(tools, video, info, start, end, size=AUDIO_BIN):
    """Loudness per bin, onsets, silences and the peak, with times in the video's own seconds."""
    if not info['audio']:
        return None
    raw = run([tools[0], '-v', 'error', '-ss', f'{start:.3f}', '-to', f'{end:.3f}', '-i', video, '-vn', '-ac', '1',
               '-ar', str(AUDIO_RATE), '-f', 's16le', '-'], binary=True).stdout
    samples = array.array('h')
    samples.frombytes(raw[:len(raw) // 2 * 2])
    if sys.byteorder == 'big':
        samples.byteswap()
    db = levels(samples, AUDIO_RATE, size)
    if not db:
        return None
    peak = max(range(len(db)), key=db.__getitem__)
    loudest = sorted(range(len(db)), key=lambda i: -db[i])
    picked = []
    for i in loudest:  # the five loudest moments, at least half a second apart
        if all(abs(i - j) * size >= 0.5 for j in picked):
            picked.append(i)
        if len(picked) == 5:
            break
    return {'bin': size, 'start': start, 'db': db, 'peak': db[peak], 'peak_at': start + peak * size,
            'loudest': [round(start + i * size, 2) for i in picked],
            'onsets': [round(start + t, 2) for t in onsets(db, size)],
            'silences': [(round(start + a, 2), round(start + b, 2)) for a, b in silences(db, size)]}


# ----------------------------------------------------------------------------------------------------------------- sheets

def group_gap(col, group):
    """Extra px left of column `col`: GROUP_GAP for each group boundary before it."""
    return col // group * GROUP_GAP if group > 1 else 0


def layout(width, height, count, cols=None, sheet_width=SHEET_WIDTH, max_edge=MAX_EDGE, label=22, gap=6, header=30, group=1):
    """(cols, tile width, tile height, tiles per page) for a sheet whose long edge stays within `max_edge`; a row holds
    whole groups of `group` tiles, GROUP_GAP apart."""
    cols = cols or (6 if height > width else 4)
    cols = max(group, min(cols, count) // group * group)
    tile_w = min(width, (sheet_width - gap * (cols + 1) - group_gap(cols - 1, group)) // cols)
    tile_h = max(1, round(tile_w * height / width))
    rows = max(1, (max_edge - header - gap) // (tile_h + label + gap))
    return cols, tile_w, tile_h, cols * rows


def make_sheet(paths, labels, out, title, cols=None, sheet_width=SHEET_WIDTH, group=1):
    """Contact sheets of `paths` with a label over each tile, each frame fitted whole (tiles take the first frame's
    shape); more pages (`-2`, `-3`) when one would pass MAX_EDGE."""
    Image, ImageDraw, ImageFont = pillow()
    first = Image.open(paths[0])
    cols, tile_w, tile_h, per_page = layout(first.width, first.height, len(paths), cols, sheet_width, group=group)
    small, big = font(ImageFont, 15), font(ImageFont, 17)
    label, gap, header = 22, 6, 30
    outs = []
    pages = math.ceil(len(paths) / per_page)
    for page in range(pages):
        chunk = list(zip(paths, labels))[page * per_page:(page + 1) * per_page]
        rows = math.ceil(len(chunk) / cols)
        width = gap + cols * (tile_w + gap) + group_gap(cols - 1, group)
        sheet = Image.new('RGB', (width, header + rows * (tile_h + label + gap) + gap), (18, 18, 22))
        draw = ImageDraw.Draw(sheet)
        draw.text((gap, 7), title + (f'  (page {page + 1} of {pages})' if pages > 1 else ''), fill=(235, 235, 235), font=big)
        for i, (path, text) in enumerate(chunk):
            x = gap + (i % cols) * (tile_w + gap) + group_gap(i % cols, group)
            y = header + (i // cols) * (tile_h + label + gap)
            draw.text((x + 2, y + 3), text, fill=(255, 214, 102), font=small)
            with Image.open(path) as frame:
                scale = min(tile_w / frame.width, tile_h / frame.height)
                size = (max(1, round(frame.width * scale)), max(1, round(frame.height * scale)))
                sheet.paste(frame.convert('RGB').resize(size, Image.LANCZOS),
                            (x + (tile_w - size[0]) // 2, y + label + (tile_h - size[1]) // 2))
        target = out if page == 0 else re.sub(r'(\.\w+)$', f'-{page + 1}\\1', out)
        sheet.save(target)
        outs.append(target)
    return outs


def tick_step(span, most=12):
    for step in (0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800):
        if span / step <= most:
            return step
    return 3600


def make_timeline(out, start, end, shot_list, sound, width=SHEET_WIDTH, height=240):
    """Loudness over time (dBFS, -60 at the bottom), cuts as orange lines with shot numbers, onsets as blue marks."""
    Image, ImageDraw, ImageFont = pillow()
    small = font(ImageFont, 14)
    left, right, top, bottom = 52, 12, 24, 30
    image = Image.new('RGB', (width, height), (18, 18, 22))
    draw = ImageDraw.Draw(image)
    plot_w, plot_h = width - left - right, height - top - bottom
    x_of = lambda t: left + (t - start) / (end - start) * plot_w  # noqa: E731
    y_of = lambda db: top + (min(0.0, max(-60.0, db)) / -60.0) * plot_h  # noqa: E731
    for db in (0, -20, -40, -60):
        draw.line([(left, y_of(db)), (width - right, y_of(db))], fill=(48, 48, 56))
        draw.text((4, y_of(db) - 8), f'{db} dB', fill=(150, 150, 160), font=small)
    step = tick_step(end - start)
    t = math.ceil(start / step) * step
    while t <= end + 1e-9:
        draw.line([(x_of(t), top + plot_h), (x_of(t), top + plot_h + 4)], fill=(150, 150, 160))
        draw.text((x_of(t) - 18, top + plot_h + 8), stamp(t)[:-3] if step >= 1 else stamp(t), fill=(150, 150, 160), font=small)
        t += step
    labelled = -100.0
    for number, (a, _) in enumerate(shot_list, 1):
        if number > 1:  # 2 px, so the line survives a viewer's downscale
            draw.line([(x_of(a), top), (x_of(a), top + plot_h)], fill=(255, 150, 40), width=2)
        if x_of(a) - labelled >= 8 * len(str(number)) + 6:
            draw.text((x_of(a) + 2, 4), str(number), fill=(255, 150, 40), font=small)
            labelled = x_of(a)
    if sound:
        points = [(x_of(sound['start'] + i * sound['bin']), y_of(db)) for i, db in enumerate(sound['db'])]
        if len(points) > 1:
            draw.line(points, fill=(235, 235, 235), width=1)
        for onset in sound['onsets']:
            x = x_of(onset)
            draw.polygon([(x, top + plot_h - 8), (x - 4, top + plot_h), (x + 4, top + plot_h)], fill=(90, 170, 255))
    image.save(out)
    return out


# ---------------------------------------------------------------------------------------------------------------- reports

def describe(info):
    v, a = info['video'], info['audio']
    text = f'{os.path.basename(info["file"])}: {info["duration"]:.2f} s'
    if v:
        text += f', {v["width"]}x{v["height"]}, {v["fps"]:g} fps, {v["codec"]}'
    text += f', audio {a["codec"]} {a["rate"]} Hz {a["channels"]} ch' if a else ', no audio'
    return text


def rapid_runs(shot_list, short=RAPID, least=3):
    """[(first, last)] indexes of 3 or more shots in a row, each shorter than `short`: a flashing effect or quick cuts."""
    runs, i = [], 0
    while i < len(shot_list):
        j = i
        while j < len(shot_list) and shot_list[j][1] - shot_list[j][0] < short:
            j += 1
        if j - i >= least:
            runs.append((i, j - 1))
        i = max(j, i + 1)
    return runs


def shot_tiles(shot_list):
    """[(label, (start, end))] for the shots sheet: one per shot, a rapid run as a single tile."""
    runs = {first: last for first, last in rapid_runs(shot_list)}
    tiles, i = [], 0
    while i < len(shot_list):
        if i in runs:
            last = runs[i]
            tiles.append((f'#{i + 1}-{last + 1} rapid', (shot_list[i][0], shot_list[last][1])))
            i = last + 1
        else:
            tiles.append((f'#{i + 1}', shot_list[i]))
            i += 1
    return tiles


def shot_moments(tiles):
    """[(label, time)]: each tile's in, middle and out frame, EDGE inside its cuts (a quarter of a shorter shot). The longer
    half of the tiles, if at least LONG_SHOT, show LONG_FRAMES, evenly from in to out: half as many frames again."""
    lengths = [b - a for _, (a, b) in tiles]
    by_length = sorted(range(len(tiles)), key=lambda i: -lengths[i])
    longer = {i for i in by_length[:(len(tiles) + 1) // 2] if lengths[i] >= LONG_SHOT}
    moments = []
    for i, (label, (a, b)) in enumerate(tiles):
        inset = min(EDGE, (b - a) / 4)
        if i in longer:
            times = [a + inset + (b - a - 2 * inset) * k / (LONG_FRAMES - 1) for k in range(LONG_FRAMES)]
            moments += [(f'{label} {stamp(times[0])}', times[0])]
            moments += [(f'{k + 1}/{LONG_FRAMES} {stamp(times[k])}', times[k]) for k in range(1, LONG_FRAMES - 1)]
            moments += [(f'out {stamp(times[-1])}', times[-1])]
        else:
            moments += [(f'{label} {stamp(a + inset)}', a + inset), (f'mid {stamp((a + b) / 2)}', (a + b) / 2),
                        (f'out {stamp(b - inset)}', b - inset)]
    return moments


def parse_pairs(text):
    """[(reference time, recording time)] from `2.3=1.6,0:07=5.2`."""
    pairs = []
    for item in (p for p in text.split(',') if p.strip()):
        ref, sep, rec = item.partition('=')
        ref, rec = parse_time(ref), parse_time(rec)
        if not sep or ref is None or rec is None:
            raise ValueError(f'not a pair of times (REFERENCE=RECORDING): {item}')
        pairs.append((ref, rec))
    if not pairs:
        raise ValueError('--pairs is empty')
    return pairs


def shot_report(shot_list, limit=40):
    lengths = [b - a for a, b in shot_list]
    if len(shot_list) == 1:
        return ['shots: 1 (no cut found)']
    shortest, longest = min(range(len(lengths)), key=lengths.__getitem__), max(range(len(lengths)), key=lengths.__getitem__)
    lines = [f'shots: {len(shot_list)}, mean {sum(lengths) / len(lengths):.2f} s, shortest {lengths[shortest]:.2f} s (#{shortest + 1}), '
             f'longest {lengths[longest]:.2f} s (#{longest + 1})']
    for first, last in rapid_runs(shot_list):
        run_lengths = lengths[first:last + 1]
        lines.append(f'  rapid run #{first + 1}-#{last + 1}: {last - first + 1} shots of {min(run_lengths):.2f}-{max(run_lengths):.2f} s, '
                     f'{stamp(shot_list[first][0])}-{stamp(shot_list[last][1])} (a flashing effect or quick cuts: burst it)')
    for number, (a, b) in enumerate(shot_list[:limit], 1):
        lines.append(f'  #{number} {stamp(a)}-{stamp(b)}  {b - a:.2f} s')
    if len(shot_list) > limit:
        lines.append(f'  ... {len(shot_list) - limit} more in summary.md')
    return lines


def audio_report(sound, shot_list=None):
    if not sound:
        return ['audio: none']
    lines = [f'audio: peak {sound["peak"]:.1f} dBFS at {stamp(sound["peak_at"])}; loudest at ' + ', '.join(stamp(t) for t in sound['loudest'])]
    cuts = [a for a, _ in (shot_list or [])[1:]]
    on_cut = sum(1 for t in sound['onsets'] if any(abs(t - c) <= 0.1 for c in cuts))
    lines.append(f'onsets ({len(sound["onsets"])}' + (f', {on_cut} within 0.1 s of a cut' if cuts else '') + '): '
                 + ' '.join(stamp(t) for t in sound['onsets'][:60]) + (' ...' if len(sound['onsets']) > 60 else ''))
    if sound['silences']:
        lines.append('silences: ' + ', '.join(f'{stamp(a)}-{stamp(b)}' for a, b in sound['silences']))
    return lines


# --------------------------------------------------------------------------------------------------------------- commands

def cmd_watch(tools, a):
    info = probe(tools, a.video)
    start, end = window(info, a.start, a.end)
    out = a.out or tempfile.mkdtemp(prefix='watch_')
    os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp(prefix='frames_', dir=out)
    name = os.path.basename(a.video)
    files = []
    try:
        shot_list = shots(tools, a.video, info, start, end, a.threshold, a.min_shot, a.scale)
        sound = audio(tools, a.video, info, start, end, a.bin)
        if info['video']:
            times = even_times(start, end, a.count)
            moments = shot_moments(shot_tiles(shot_list)) if len(shot_list) > 1 else []
            paths = grab_many(tools, a.video, times + [t for _, t in moments], work, info=info)  # one decode for both sheets
            files += make_sheet(paths[:len(times)], [f'#{i + 1}  {stamp(t)}' for i, t in enumerate(times)], os.path.join(out, 'overview.png'),
                                f'{name}  {stamp(start)}-{stamp(end)}  {a.count} frames, evenly spaced', a.cols, a.width)
            if moments:
                portrait = info['video']['height'] > info['video']['width']
                files += make_sheet(paths[len(times):], [label for label, _ in moments], os.path.join(out, 'shots.png'),
                                    f'{name}  {len(shot_list)} shots: in to out of each, more of the longer half (a rapid run as one: burst it)',
                                    9 if portrait else 6, a.width, group=3)
        files.append(make_timeline(os.path.join(out, 'timeline.png'), start, end, shot_list, sound, a.width))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    head = [describe(info)] + ([f'window: {stamp(start)}-{stamp(end)}'] if a.start or a.end is not None else [])
    lines = [*head, *shot_report(shot_list), *audio_report(sound, shot_list), 'files: ' + ', '.join(os.path.basename(f) for f in files) + f'  in {out}']
    full = [*head, *shot_report(shot_list, limit=10 ** 6), *audio_report(sound, shot_list)]
    Path(out, 'summary.md').write_text('\n'.join(full) + '\n', encoding='utf-8')
    print('\n'.join(lines))


def cmd_sheet(tools, a):
    info = probe(tools, a.video)
    start, end = window(info, a.start, a.end)
    times = every_times(start, end, a.every) if a.every else even_times(start, end, a.count)
    work = tempfile.mkdtemp(prefix='frames_')
    try:
        paths = grab_many(tools, a.video, times, work, info=info)
        outs = make_sheet(paths, [f'#{i + 1}  {stamp(t)}' for i, t in enumerate(times)], a.out,
                          f'{os.path.basename(a.video)}  {stamp(start)}-{stamp(end)}  {len(times)} frames', a.cols, a.width)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print('\n'.join(outs))


def cmd_burst(tools, a):
    info = probe(tools, a.video)
    start, end = window(info, a.start, a.start + a.duration)
    work = tempfile.mkdtemp(prefix='burst_')
    try:
        source = info['video']['fps'] if info['video'] else 0
        paths, times = burst_frames(tools, a.video, start, end - start, a.fps, work, unique=not a.all, source_fps=source)
        if not paths:
            raise Failed('no frames decoded')
        labels = [stamp(t) + (f'  f{round(t * source)}' if source else '') for t in times]
        kind = 'every frame' if a.all else 'each new frame'
        outs = make_sheet(paths, labels, a.out, f'{os.path.basename(a.video)}  {kind}, at most {a.fps:g} a second, '
                          f'{stamp(start)}-{stamp(end)} ({len(paths)}; f = frame at {source:g} fps)', a.cols or 6, a.width)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print('\n'.join(outs))


def cmd_frames(tools, a):
    info = probe(tools, a.video)
    times = [parse_time(t) for t in a.at.split(',') if t.strip()]
    paths = grab_many(tools, a.video, times, a.out, a.frame_width, info)
    for t, path in zip(times, paths):
        print(f'{stamp(t)}  {path}')


def cmd_compare(tools, a):
    pairs = parse_pairs(a.pairs)
    if a.cols and a.cols % 2:
        raise ValueError('--cols must be even: each moment is two tiles')
    sides = [(a.reference, probe(tools, a.reference), 'ref'), (a.recording, probe(tools, a.recording), 'yours')]
    for (video, info, _), times in zip(sides, zip(*pairs)):
        late = [t for t in times if t > info['duration']]
        if late:
            raise ValueError(f'{os.path.basename(video)} is {stamp(info["duration"])} long: nothing at {stamp(late[0])}')
    work = tempfile.mkdtemp(prefix='compare_')
    try:
        grabbed = [grab_many(tools, video, list(times), os.path.join(work, side), info=info, prefix=side)
                   for (video, info, side), times in zip(sides, zip(*pairs))]
        paths = [path for pair in zip(*grabbed) for path in pair]
        labels = [text for i, (ref, rec) in enumerate(pairs, 1) for text in (f'#{i} ref {stamp(ref)}', f'#{i} yours {stamp(rec)}')]
        outs = make_sheet(paths, labels, a.out, f'{os.path.basename(a.reference)} (ref) beside {os.path.basename(a.recording)} (yours), '
                          f'{len(pairs)} moments', a.cols, a.width, group=2)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print('\n'.join(outs))


def cmd_shots(tools, a):
    info = probe(tools, a.video)
    start, end = window(info, a.start, a.end)
    print('\n'.join([describe(info), *shot_report(shots(tools, a.video, info, start, end, a.threshold, a.min_shot, a.scale), limit=10 ** 6)]))


def cmd_audio(tools, a):
    info = probe(tools, a.video)
    start, end = window(info, a.start, a.end)
    print('\n'.join([describe(info), *audio_report(audio(tools, a.video, info, start, end, a.bin))]))


def cmd_probe(tools, a):
    print(json.dumps(probe(tools, a.video), indent=2))


def find_window(part):
    """(title, left, top, width, height) of the first visible top-level window whose title contains `part`, in screen pixels."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # physical pixels, as the screen grabber uses
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if part.lower() in buffer.value.lower():
                rect = wintypes.RECT()
                # The visible frame: GetWindowRect adds invisible borders, off screen on a maximized window.
                if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append((buffer.value, rect.left, rect.top, rect.right, rect.bottom))
        return True

    user32.EnumWindows(each, 0)
    if not found:
        raise ValueError(f'no visible window has "{part}" in its title')
    title, left, top, right, bottom = found[0]
    x0, y0 = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)  # the virtual screen, every monitor
    x1, y1 = x0 + user32.GetSystemMetrics(78), y0 + user32.GetSystemMetrics(79)
    left, top, right, bottom = max(left, x0), max(top, y0), min(right, x1), min(bottom, y1)
    return title, left, top, right - left, bottom - top


def cmd_record(tools, a):
    if a.crop and not re.fullmatch(r'\d+:\d+:\d+:\d+', a.crop):
        raise ValueError(f'--crop is W:H:X:Y in pixels of the full recording, not {a.crop}')
    if platform.system() != 'Windows':
        raise ValueError('record captures with gdigrab, so it runs on Windows only')
    title, left, top, width, height = find_window(a.window)
    width, height = width // 2 * 2, height // 2 * 2  # H.264 needs even sizes
    if a.mode == 'window':  # the window's own surface: works behind other windows, if the app draws there
        source = ['-i', f'title={title}']
    else:  # the screen area the window covers: whatever is on top is what is recorded
        source = ['-offset_x', str(left), '-offset_y', str(top), '-video_size', f'{width}x{height}', '-i', 'desktop']
    chain = ([f'crop={a.crop}'] if a.crop else []) + ['pad=ceil(iw/2)*2:ceil(ih/2)*2']
    run([tools[0], '-v', 'error', '-f', 'gdigrab', '-framerate', str(a.fps), '-draw_mouse', '0', '-t', str(a.seconds), *source,
         '-vf', ','.join(chain), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', '-y', a.out])
    print(f'{a.out}  {a.seconds:g} s of "{title}" ({a.mode}' + (f', cropped to {a.crop}' if a.crop else '') + f'), {a.fps:g} fps')


def cmd_find(tools, a):
    version = run([tools[0], '-hide_banner', '-version']).stdout.splitlines()[0]
    print(f'{tools[0]}\n{tools[1]}\n{version}')


def cmd_install(a):
    command = INSTALL.get(platform.system(), INSTALL['Linux'])
    print('running: ' + ' '.join(command), flush=True)
    code = subprocess.call(command)
    if code == 0:
        try:
            print('installed: ' + find_ffmpeg()[0])
        except Missing:
            print('installed, but not found yet: open a new shell, or pass --ffmpeg PATH')
    return code


def parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    sub = ap.add_subparsers(dest='command', required=True)

    def add(name, video=True, out=False, window_opts=False):
        p = sub.add_parser(name)
        if video:
            p.add_argument('video')
        if out:
            p.add_argument('-o', '--out', required=name not in ('watch',))
        if window_opts:
            p.add_argument('--start', type=parse_time)
            p.add_argument('--end', type=parse_time)
        p.add_argument('--ffmpeg')
        return p

    p = add('watch', out=True, window_opts=True)
    p.add_argument('--count', type=int, default=OVERVIEW)
    for q in (p, add('shots', window_opts=True)):
        q.add_argument('--threshold', type=float, default=SCENE)
        q.add_argument('--min-shot', type=float, default=MIN_SHOT)
        q.add_argument('--scale', type=int, default=SCALE)
    p.add_argument('--bin', type=float, default=AUDIO_BIN)
    p.add_argument('--cols', type=int)
    p.add_argument('--width', type=int, default=SHEET_WIDTH)
    q = add('sheet', out=True, window_opts=True)
    q.add_argument('--count', type=int, default=OVERVIEW)
    q.add_argument('--every', type=float)
    q.add_argument('--cols', type=int)
    q.add_argument('--width', type=int, default=SHEET_WIDTH)
    q = add('burst', out=True)
    q.add_argument('--start', type=parse_time, required=True)
    q.add_argument('--duration', type=float, default=1.0)
    q.add_argument('--fps', type=float, default=BURST_FPS)
    q.add_argument('--all', action='store_true', help='keep duplicate frames (a held drawing shows each time)')
    q.add_argument('--cols', type=int)
    q.add_argument('--width', type=int, default=SHEET_WIDTH)
    q = add('frames', out=True)
    q.add_argument('--at', required=True)
    q.add_argument('--width', dest='frame_width', type=int)
    q = sub.add_parser('compare')
    q.add_argument('reference')
    q.add_argument('recording')
    q.add_argument('--pairs', required=True, help='REF=REC times, comma separated: a reference moment and the one built for it')
    q.add_argument('-o', '--out', required=True)
    q.add_argument('--cols', type=int, help='an even number: each moment is two tiles')
    q.add_argument('--width', type=int, default=SHEET_WIDTH)
    q.add_argument('--ffmpeg')
    add('audio', window_opts=True).add_argument('--bin', type=float, default=AUDIO_BIN)
    add('probe')
    q = sub.add_parser('record')
    q.add_argument('out')
    q.add_argument('--window', required=True)
    q.add_argument('--seconds', type=float, default=10)
    q.add_argument('--fps', type=float, default=30)
    q.add_argument('--mode', choices=['window', 'screen'], default='window')
    q.add_argument('--crop', help='W:H:X:Y: keep only this part, such as the 3D view, measured on a full-size still')
    q.add_argument('--ffmpeg')
    add('find', video=False)
    sub.add_parser('install')
    return ap


def main(argv=None):
    a = parser().parse_args(argv)
    if a.command == 'install':
        return cmd_install(a)
    try:
        tools = find_ffmpeg(getattr(a, 'ffmpeg', None))
        for video in (getattr(a, name, None) for name in ('video', 'reference', 'recording')):
            if video and not re.match(r'^[a-z]+://', video) and not os.path.isfile(video):
                raise ValueError(f'no such file: {video}')
        {'watch': cmd_watch, 'sheet': cmd_sheet, 'burst': cmd_burst, 'frames': cmd_frames, 'compare': cmd_compare, 'shots': cmd_shots,
         'audio': cmd_audio, 'probe': cmd_probe, 'record': cmd_record, 'find': cmd_find}[a.command](tools, a)
    except Missing as e:
        print(e, file=sys.stderr)
        return 3
    except Failed as e:
        print(f'ffmpeg failed: {e}', file=sys.stderr)
        return 1
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
