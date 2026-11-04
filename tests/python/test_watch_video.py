"""watch_video.py: the arithmetic on its own, then the whole tool on a video ffmpeg makes with known cuts and sound
(skipped where ffmpeg or Pillow is missing)."""
import array
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import watch_video as wv

try:
    TOOLS = wv.find_ffmpeg()
except wv.Missing:
    TOOLS = None
try:
    from PIL import Image
except ImportError:
    Image = None


class Times(unittest.TestCase):
    def test_times_read_seconds_and_clock_forms(self):
        self.assertEqual(wv.parse_time('12.5'), 12.5)
        self.assertEqual(wv.parse_time('1:02.5'), 62.5)
        self.assertEqual(wv.parse_time('1:01:02'), 3662)
        self.assertIsNone(wv.parse_time(''))
        for bad in ('-1', '1:2:3:4', 'soon'):
            with self.assertRaises(ValueError):
                wv.parse_time(bad)

    def test_stamps_round_trip(self):
        self.assertEqual(wv.stamp(3.25), '0:03.25')
        self.assertEqual(wv.stamp(3725.5), '1:02:05.50')
        self.assertAlmostEqual(wv.parse_time(wv.stamp(83.47)), 83.47)

    def test_even_frames_avoid_both_edges(self):
        times = wv.even_times(0, 10, 4)
        self.assertEqual(times, [1.25, 3.75, 6.25, 8.75])
        self.assertEqual(wv.every_times(2, 3, 0.25), [2, 2.25, 2.5, 2.75])


class Shots(unittest.TestCase):
    def test_showinfo_times_are_read(self):
        stderr = '[Parsed_showinfo_2 @ 0x1] n:   0 pts:  139 pts_time:4.66 duration: 1\n[Parsed_showinfo_2 @ 0x1] n:   1 pts_time:8.61\n'
        self.assertEqual(wv.cut_times(stderr), [4.66, 8.61])

    def test_a_flash_merges_into_one_cut(self):
        self.assertEqual(wv.merge_cuts([1.0, 1.05, 2.0, 2.1, 2.3], 0.2), [1.0, 2.0, 2.3])

    def test_no_cut_hugs_either_end(self):
        self.assertEqual(wv.merge_cuts([0.1, 3.0, 9.9], 0.2, start=0, end=10), [3.0])

    def test_three_short_shots_in_a_row_are_a_rapid_run(self):
        shots = [(0, 2), (2, 2.3), (2.3, 2.6), (2.6, 2.9), (2.9, 5), (5, 5.3), (5.3, 5.6), (5.6, 8)]
        self.assertEqual(wv.rapid_runs(shots), [(1, 3)])
        tiles = wv.shot_tiles(shots)
        self.assertEqual([label for label, _ in tiles], ['#1', '#2-4 rapid', '#5', '#6', '#7', '#8'])
        self.assertEqual(tiles[1][1], (2, 2.9))
        report = '\n'.join(wv.shot_report(shots))
        self.assertIn('rapid run #2-#4: 3 shots', report)


class Sound(unittest.TestCase):
    def test_levels_are_rms_dbfs_per_bin(self):
        loud = array.array('h', [16384, -16384] * 400)  # a square wave at half scale: -6 dBFS
        quiet = array.array('h', [0] * 800)
        db = wv.levels(quiet + loud, 8000, 0.1)
        self.assertEqual(db[0], -100.0)
        self.assertAlmostEqual(db[1], -6.0, places=1)

    def test_onsets_are_rises_above_the_floor(self):
        db = [-60, -60, -20, -20, -21, -20, -60, -58, -18, -50, -49, -40]
        self.assertEqual(wv.onsets(db, 0.05), [0.1, 0.4, 0.55])

    def test_silences_are_long_quiet_spans(self):
        db = [-60] * 12 + [-20] * 4 + [-60] * 3
        self.assertEqual(wv.silences(db, 0.05), [(0.0, 0.6)])


class Sheets(unittest.TestCase):
    def test_a_sheet_stays_within_the_long_edge(self):
        for width, height, count in ((1920, 1080, 16), (640, 348, 40), (1080, 1920, 16), (320, 180, 3)):
            cols, tile_w, tile_h, per_page = wv.layout(width, height, count)
            pages = -(-count // per_page)
            rows = -(-min(count, per_page) // cols)
            self.assertLessEqual(30 + rows * (tile_h + 28) + 6, wv.MAX_EDGE, (width, height))
            self.assertLessEqual(tile_w, width, 'a tile is never larger than the source')
            self.assertGreaterEqual(pages, 1)
        self.assertEqual(wv.layout(1080, 1920, 16)[0], 6, 'portrait video gets 6 columns')


class Finding(unittest.TestCase):
    def test_winget_packages_are_searched_after_its_links(self):
        with tempfile.TemporaryDirectory() as local:
            binary = Path(local, 'Microsoft', 'WinGet', 'Packages', 'Gyan.FFmpeg_x', 'ffmpeg-9-full', 'bin', 'ffmpeg.exe')
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'')
            found = wv.candidates('Windows', {'LOCALAPPDATA': local, 'USERPROFILE': local})
            self.assertTrue(found[0].endswith(os.path.join('WinGet', 'Links', 'ffmpeg.exe')))
            self.assertEqual(found[1], str(binary))

    def test_missing_ffmpeg_names_the_install_command(self):
        with mock.patch.object(wv.shutil, 'which', return_value=None), mock.patch.object(wv, 'candidates', return_value=[]), \
                mock.patch.dict(os.environ, {'FFMPEG': ''}):
            with self.assertRaises(wv.Missing) as caught:
                wv.find_ffmpeg()
        self.assertIn('Ask the user', str(caught.exception))
        self.assertIn('install', str(caught.exception))

    def test_an_explicit_path_needs_ffprobe_beside_it_or_on_the_path(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'ffmpeg').write_bytes(b'')
            Path(folder, 'ffprobe').write_bytes(b'')
            self.assertEqual(wv.find_ffmpeg(str(Path(folder, 'ffmpeg'))), (str(Path(folder, 'ffmpeg')), str(Path(folder, 'ffprobe'))))


@unittest.skipUnless(TOOLS and Image, 'needs ffmpeg and Pillow')
class OnARealVideo(unittest.TestCase):
    """4.7 s at 30 fps: red 1 s, green 1.5 s, four 0.3 s flashes (white, black, white, black), blue 1 s; silent, then a
    440 Hz tone from 2.0 s."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp(prefix='watch_test_')
        cls.video = os.path.join(cls.folder, 'cuts.mp4')
        parts = [('red', 1.0), ('green', 1.5), ('white', 0.3), ('black', 0.3), ('white', 0.3), ('black', 0.3), ('blue', 1.0)]
        cmd = [TOOLS[0], '-v', 'error']
        for color, length in parts:
            cmd += ['-f', 'lavfi', '-i', f'color=c={color}:s=320x180:r=30:d={length}']
        cmd += ['-f', 'lavfi', '-i', "aevalsrc='if(gte(t,2),0.5*sin(2*PI*440*t),0)':s=44100:d=4.7"]
        concat = ''.join(f'[{i}:v]' for i in range(len(parts))) + f'concat=n={len(parts)}:v=1:a=0[v]'
        cmd += ['-filter_complex', concat, '-map', '[v]', '-map', f'{len(parts)}:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-shortest', '-y', cls.video]
        subprocess.run(cmd, check=True)
        cls.info = wv.probe(TOOLS, cls.video)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    def test_probe_reads_the_streams(self):
        self.assertAlmostEqual(self.info['duration'], 4.7, delta=0.1)
        self.assertEqual((self.info['video']['width'], self.info['video']['height']), (320, 180))
        self.assertAlmostEqual(self.info['video']['fps'], 30, delta=0.01)
        self.assertIsNotNone(self.info['audio'])

    def test_every_cut_is_found_within_a_frame(self):
        shots = wv.shots(TOOLS, self.video, self.info, 0, self.info['duration'])
        cuts = [a for a, _ in shots[1:]]
        expected = [1.0, 2.5, 2.8, 3.1, 3.4, 3.7]
        self.assertEqual(len(cuts), len(expected), cuts)
        for got, want in zip(cuts, expected):
            self.assertAlmostEqual(got, want, delta=1 / 30 + 1e-6)
        self.assertEqual(wv.rapid_runs(shots), [(2, 5)])

    def test_a_window_keeps_the_videos_own_times(self):
        shots = wv.shots(TOOLS, self.video, self.info, 2.0, 4.7)
        self.assertAlmostEqual(shots[1][0], 2.5, delta=1 / 30 + 1e-6)

    def test_the_tone_is_an_onset_after_a_silence(self):
        sound = wv.audio(TOOLS, self.video, self.info, 0, self.info['duration'])
        self.assertAlmostEqual(sound['onsets'][0], 2.0, delta=0.06)
        self.assertEqual(len(sound['onsets']), 1)
        self.assertAlmostEqual(sound['silences'][0][1], 2.0, delta=0.06)

    def test_one_pass_and_seeks_grab_the_same_frames(self):
        times = [0.5, 1.5, 4.2]
        with tempfile.TemporaryDirectory() as folder:
            passed = wv.grab_pass(TOOLS, self.video, times, folder, self.info)
            sought = [wv.grab(TOOLS, self.video, t, os.path.join(folder, f'seek{i}.png'), info=self.info) for i, t in enumerate(times)]
            self.assertIsNotNone(passed)
            for a, b, (r, g, bl) in zip(passed, sought, ((255, 0, 0), (0, 128, 0), (0, 0, 255))):
                for path in (a, b):
                    pixel = Image.open(path).convert('RGB').getpixel((160, 90))
                    self.assertLess(abs(pixel[0] - r) + abs(pixel[1] - g) + abs(pixel[2] - bl), 60, (path, pixel))

    def test_a_burst_keeps_only_new_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            still, _ = wv.burst_frames(TOOLS, self.video, 1.1, 1.0, 24, folder, source_fps=30)
            self.assertEqual(len(still), 1, 'a second of one color is one new frame')
        with tempfile.TemporaryDirectory() as folder:
            every, times = wv.burst_frames(TOOLS, self.video, 1.1, 1.0, 24, folder, unique=False, source_fps=30)
            self.assertEqual(len(every), 24, '24 a second from 30, not the 15 a gap rule keeps')
            self.assertTrue(all(abs((b - a) - 1 / 24) < 0.003 for a, b in zip(times, times[1:])))
            self.assertAlmostEqual(times[0], 1.1, delta=0.05)
        with tempfile.TemporaryDirectory() as folder:
            flashes, _ = wv.burst_frames(TOOLS, self.video, 2.5, 1.2, 24, folder, source_fps=30)
            self.assertEqual(len(flashes), 4, 'each of the four flashes once')

    def test_watch_writes_its_sheets_and_summary(self):
        out = os.path.join(self.folder, 'watched')
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = wv.main(['watch', self.video, '-o', out, '--ffmpeg', TOOLS[0]])
        self.assertEqual(code, 0)
        for name in ('overview.png', 'shots.png', 'timeline.png', 'summary.md'):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        for name in ('overview.png', 'shots.png', 'timeline.png'):
            self.assertLessEqual(max(Image.open(os.path.join(out, name)).size), wv.MAX_EDGE)
        text = printed.getvalue()
        self.assertIn('shots: 7', text)
        self.assertIn('rapid run #3-#6', text)
        self.assertIn('onsets (1', text)

    def test_a_missing_file_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(wv.main(['probe', os.path.join(self.folder, 'nothing.mp4')]), 2)


if __name__ == '__main__':
    unittest.main()
