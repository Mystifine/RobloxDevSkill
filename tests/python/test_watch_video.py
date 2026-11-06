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

    def test_each_shot_shows_in_middle_and_out_inside_its_cuts(self):
        moments = wv.shot_moments([('#1', (0, 0.6)), ('#2-4 rapid', (0.6, 1.1)), ('#5', (1.1, 1.3))])
        self.assertEqual(len(moments), 9, 'none is long enough for more')
        times = [round(t, 3) for _, t in moments]
        self.assertEqual(times[:3], [0.1, 0.3, 0.5], 'EDGE inside each cut')
        self.assertEqual(times[6:], [1.15, 1.2, 1.25], 'a quarter of a shot shorter than 4 x EDGE')
        self.assertEqual([label.split()[0] for label, _ in moments[:6]], ['#1', 'mid', 'out', '#2-4', 'mid', 'out'])

    def test_the_longer_half_of_the_shots_shows_twice_the_frames(self):
        moments = wv.shot_moments([('#1', (0, 4)), ('#2', (4, 4.6)), ('#3', (4.6, 6.6)), ('#4', (6.6, 7.2))])
        self.assertEqual(len(moments), 18, 'half as many frames again as 3 for each of 4 shots')
        labels = [label.split()[0] for label, _ in moments]
        self.assertEqual(labels[:6], ['#1', '2/6', '3/6', '4/6', '5/6', 'out'])
        self.assertEqual(labels[6:9], ['#2', 'mid', 'out'], 'the shorter half keeps three')
        self.assertEqual([round(t, 2) for _, t in moments[:6]], [0.1, 0.86, 1.62, 2.38, 3.14, 3.9], 'evenly from in to out')
        self.assertEqual(moments, sorted(moments, key=lambda m: m[1]), 'in the order they happen')

    def test_a_short_shot_stays_at_three_even_in_the_longer_half(self):
        self.assertEqual(len(wv.shot_moments([(f'#{i}', (i * 0.5, i * 0.5 + 0.5)) for i in range(4)])), 12)

    def test_speech_runs_where_it_can_and_says_how_when_it_cannot(self):
        self.assertEqual(wv.speech_command(has_package=True)[:2], [sys.executable, '-I'])
        self.assertEqual(wv.speech_command(has_package=False, uv='uv')[:4], ['uv', 'run', '--no-project', '--with'])
        with mock.patch.object(wv.shutil, 'which', return_value=None), self.assertRaises(wv.Missing) as caught:
            wv.speech_command(has_package=False)
        self.assertIn('Ask the user', str(caught.exception))

    def test_spoken_words_keep_the_videos_own_times(self):
        out = 'a log line\n{"start": 1.0, "end": 2.0, "text": "I win.", "words": [{"word": "I", "start": 1.1, "end": 1.3}, {"word": "win.", "start": 1.5, "end": 1.9}]}\n'
        segment = wv.parse_segments(out, offset=10.0)[0]
        self.assertEqual((segment['start'], segment['end']), (11.0, 12.0))
        self.assertEqual([w['start'] for w in segment['words']], [11.1, 11.5])

    def test_pairs_read_reference_then_recording(self):
        self.assertEqual(wv.parse_pairs('2.3=1.6, 0:07=5.2'), [(2.3, 1.6), (7.0, 5.2)])
        for bad in ('2.3', '=1.6', '2.3=', ' , '):
            with self.assertRaises(ValueError):
                wv.parse_pairs(bad)


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

    def test_a_row_holds_whole_groups_within_the_width(self):
        for width, height, count, cols, group in ((640, 348, 66, 6, 3), (1080, 1920, 27, 9, 3), (1920, 1080, 10, 4, 2), (640, 348, 3, 6, 3)):
            got, tile_w, _, per_page = wv.layout(width, height, count, cols, group=group)
            self.assertEqual(got % group, 0, (width, count))
            self.assertEqual(per_page % group, 0, 'no group splits across pages')
            self.assertLessEqual(6 + got * (tile_w + 6) + wv.group_gap(got - 1, group), wv.SHEET_WIDTH)
        self.assertEqual(wv.layout(640, 348, 3, 6, group=3)[0], 3)
        self.assertEqual(wv.group_gap(5, 1), 0, 'single tiles get no group gap')


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

    def test_more_frames_than_one_expression_holds_come_out_in_order(self):
        times = [(i + 0.25) / 30 for i in range(130)]  # (ffmpeg's select expression parsed 100 and failed at 110)
        with tempfile.TemporaryDirectory() as folder:
            paths = wv.grab_many(TOOLS, self.video, times, folder, info=self.info)
            self.assertEqual(len(set(paths)), 130)
            self.assertTrue(all('_pass' in os.path.basename(path) for path in paths), 'decoded in passes, not a seek each')
            for i, (r, g, bl) in ((0, (255, 0, 0)), (27, (255, 0, 0)), (33, (0, 128, 0)), (71, (0, 128, 0)), (79, (255, 255, 255))):  # (within a frame, as seeks are)
                pixel = Image.open(paths[i]).convert('RGB').getpixel((160, 90))
                self.assertLess(abs(pixel[0] - r) + abs(pixel[1] - g) + abs(pixel[2] - bl), 60, (i, pixel))

    def test_a_failed_pass_falls_back_to_seeks(self):
        real = wv.run

        def no_select(cmd, binary=False):
            if any('select=' in str(part) for part in cmd):
                raise wv.Failed('Error while parsing expression')
            return real(cmd, binary)

        times = [0.5, 1.5, 4.2]
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(wv, 'run', no_select):
            self.assertIsNone(wv.grab_pass(TOOLS, self.video, times, folder, self.info))
            paths = wv.grab_many(TOOLS, self.video, times, folder, info=self.info)
            for path, (r, g, bl) in zip(paths, ((255, 0, 0), (0, 128, 0), (0, 0, 255))):
                pixel = Image.open(path).convert('RGB').getpixel((160, 90))
                self.assertLess(abs(pixel[0] - r) + abs(pixel[1] - g) + abs(pixel[2] - bl), 60, (path, pixel))

    def test_a_variable_frame_rate_is_sought_by_timestamp(self):
        # Red for 10 frames over 1 s, then green at 30 fps: frame numbers from the average rate land on the wrong moments.
        video = os.path.join(self.folder, 'vfr.mp4')
        chain = "[0:v]setpts=N/10/TB[a];[1:v]setpts=N/30/TB[b];[a][b]concat=n=2:v=1:a=0[v]"
        subprocess.run([TOOLS[0], '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=320x180:r=10:d=1', '-f', 'lavfi', '-i', 'color=c=lime:s=320x180:r=30:d=1',
                        '-filter_complex', chain, '-map', '[v]', '-fps_mode', 'vfr', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', video], check=True)
        info = wv.probe(TOOLS, video)
        self.assertTrue(info['video']['vfr'], info['video'])
        self.assertIn('variable', wv.describe(info))
        self.assertFalse(self.info['video']['vfr'], 'a constant rate is not called variable')
        with tempfile.TemporaryDirectory() as folder:
            paths = wv.grab_many(TOOLS, video, [0.5, 1.5], folder, info=info)
            self.assertFalse(any('_pass' in os.path.basename(path) for path in paths), 'sought, not counted')
            red, lime = (Image.open(path).convert('RGB').getpixel((160, 90)) for path in paths)
            self.assertGreater(red[0], 200, red)
            self.assertGreater(lime[1], 200, lime)

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
        with tempfile.TemporaryDirectory() as folder:
            every, _ = wv.burst_frames(TOOLS, self.video, 1.1, 1.0, wv.BURST_FPS, folder, unique=False, source_fps=30)
            self.assertEqual(len(every), 30, 'by default a 30 fps source keeps all its frames')

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

    def test_compare_puts_each_reference_moment_beside_the_recordings(self):
        # The recording: the same colors 0.5 s later, 4:3 instead of 16:9, so its tiles are fitted, not stretched.
        recording = os.path.join(self.folder, 'later.mp4')
        subprocess.run([TOOLS[0], '-v', 'error', '-i', self.video, '-vf', 'scale=240:180,tpad=start_duration=0.5',
                        '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', recording], check=True)
        out = os.path.join(self.folder, 'compare.png')
        with contextlib.redirect_stdout(io.StringIO()):
            code = wv.main(['compare', self.video, recording, '--pairs', '0.5=1.0,1.5=2.0,4.2=4.7', '-o', out])
        self.assertEqual(code, 0)
        sheet = Image.open(out).convert('RGB')
        cols, tile_w, tile_h, _ = wv.layout(320, 180, 6, group=2)
        self.assertEqual(cols, 4)
        for i, want in enumerate([(255, 0, 0)] * 2 + [(0, 128, 0)] * 2 + [(0, 0, 255)] * 2):
            x = 6 + (i % cols) * (tile_w + 6) + wv.group_gap(i % cols, 2) + tile_w // 2
            y = 30 + (i // cols) * (tile_h + 28) + 22 + tile_h // 2
            pixel = sheet.getpixel((x, y))
            self.assertLess(sum(abs(p - w) for p, w in zip(pixel, want)), 60, (i, pixel))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(wv.main(['compare', self.video, recording, '--pairs', '1=9', '-o', out]), 2, 'past the end')
            self.assertEqual(wv.main(['compare', self.video, recording, '--pairs', '1=1', '--cols', '3', '-o', out]), 2)

    def test_a_crop_must_be_four_numbers(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(wv.main(['record', os.path.join(self.folder, 'r.mp4'), '--window', 'none', '--crop', '1280x720']), 2)
        self.assertIn('--crop', errors.getvalue())

    def test_a_missing_file_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(wv.main(['probe', os.path.join(self.folder, 'nothing.mp4')]), 2)
            self.assertEqual(wv.main(['compare', self.video, os.path.join(self.folder, 'nothing.mp4'), '--pairs', '1=1', '-o', 'x.png']), 2)


if __name__ == '__main__':
    unittest.main()
