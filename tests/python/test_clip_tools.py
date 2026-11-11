"""The Blender-clip helpers that run without Blender or Studio: gif_preview.py's timing and file, clip_import.py's .rbxanim
reading, blender_anim.py's pose checks and turn findings, and r6_rig.py's pinned downloads. No network: downloads are faked."""
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gif = load('gif_preview')
ci = load('clip_import')
ba = load('blender_anim')
r6 = load('r6_rig')


class GifTiming(unittest.TestCase):
    def test_24_frames_at_30_fps_are_800_ms_in_whole_centiseconds(self):
        self.assertEqual(gif.durations(24, 30), [30, 30, 40] * 8)

    def test_the_total_tracks_the_rate(self):
        for count, fps in ((16, 30), (60, 60), (7, 24)):
            total = sum(gif.durations(count, fps))
            self.assertLessEqual(abs(total - count * 1000 / fps), 10, (count, fps))
            self.assertTrue(all(d % 10 == 0 for d in gif.durations(count, fps)))

    def test_rates_a_gif_cannot_hold_are_refused(self):
        for fps in (0, -1, 101, float('nan')):
            with self.assertRaises(ValueError):
                gif.durations(10, fps)


@unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow is not installed')
class GifFile(unittest.TestCase):
    def test_a_built_gif_loops_with_one_palette_and_keeps_holds(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            colors = [(200, 40, 40), (200, 40, 40), (40, 200, 40), (40, 40, 200)]  # frames 1 and 2 are the same: a hold
            for i, c in enumerate(colors):
                Image.new('RGB', (64, 48), c).save(folder / f'clip_{i + 1:04d}.png')
            result = gif.build(sorted(folder.glob('clip_*.png')), folder / 'out.gif', fps=30)
            self.assertTrue(result['ok'], result['errors'])
            self.assertEqual((result['frames'], result['size']), (4, [64, 48]))
            self.assertEqual(result['ms'], sum(gif.durations(4, 30)))

    def test_frames_of_different_sizes_are_refused(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            Image.new('RGB', (64, 48)).save(folder / 'a_1.png')
            Image.new('RGB', (32, 48)).save(folder / 'a_2.png')
            self.assertFalse(gif.main([str(folder), str(folder / 'x.gif'), '--glob', 'a_*.png']) == 0)


class Rbxanim(unittest.TestCase):
    def write(self, folder, frames, sidecar=None):
        path = Path(folder) / 'HeroSlash.rbxanim'
        path.write_bytes(zlib.compress(json.dumps({'t': frames[-1]['t'], 'kfs': frames, 'export_info': {'fps': 60}}).encode()))
        if sidecar is not None:
            path.with_suffix('.json').write_text(json.dumps(sidecar))
        return path

    def test_linear_keys_become_bare_numbers_and_other_easing_is_kept(self):
        cf = [0.1234567, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
        frames = [{'t': 0.0, 'kf': {'Torso': [cf, 'Linear', 'Out'], 'Head': [cf, 'Constant', 'Out']}},
                  {'t': 1 / 60, 'kf': {'Torso': [cf, 'Linear', 'Out'], 'Head': [cf, 'Linear', 'Out']}}]
        with tempfile.TemporaryDirectory() as folder:
            data = ci.rbxanim_data(self.write(folder, frames))
        self.assertEqual(data['kfs'][0]['kf']['Torso'][0], 0.123457)
        self.assertEqual(len(data['kfs'][0]['kf']['Torso']), 12)
        self.assertEqual(data['kfs'][0]['kf']['Head'][1:], ['Constant', 'Out'])
        self.assertEqual(data['kfs'][1]['t'], round(1 / 60, 6))

    def test_the_sidecar_gives_markers_loop_and_feet(self):
        frames = [{'t': 0.0, 'kf': {}}]
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, frames, {'Markers': {'Hit': 0.2}, 'Loop': False, 'Feet': {}, 'Rest': {}})
            self.assertEqual(ci.sidecar(path)['Markers'], {'Hit': 0.2})
            self.assertEqual(ci.sidecar(Path(folder) / 'Other.rbxanim'), {})

    def test_a_long_string_never_closes_early(self):
        for text in ('plain', 'has ]] inside', 'has ]=] and ]==] too'):
            s = ci.long_string(text)
            eq = s[1:s.index('[', 1)]
            self.assertTrue(s.startswith(f'[{eq}[') and s.endswith(f']{eq}]'))
            self.assertNotIn(f']{eq}]', text)


class PoseChecks(unittest.TestCase):
    BONES = ['Head', 'LowerTorso-FK']

    def test_a_good_batch_is_normalised(self):
        frame, bones, interp = ba.check_pose(12.0, {'Head': {'rotation_quaternion': [2, 0, 0, 0]},
                                                     'LowerTorso-FK': {'location': [0, -0.2, 0]}}, self.BONES, 'bezier')
        self.assertEqual((frame, interp), (12, 'BEZIER'))
        self.assertEqual(bones['Head']['rotation_quaternion'], [1.0, 0.0, 0.0, 0.0])

    def test_bad_batches_change_nothing(self):
        bad = [
            (1.5, {'Head': {'location': [0, 0, 0]}}),
            (1, {'Neck': {'location': [0, 0, 0]}}),
            (1, {'Head': {'location': [0, math.nan, 0]}}),
            (1, {'Head': {'location': [0, 0]}}),
            (1, {'Head': {'rotation_degrees': [0, 0, 0], 'rotation_quaternion': [1, 0, 0, 0]}}),
            (1, {'Head': {'rotation_quaternion': [0, 0, 0, 0]}}),
            (1, {'Head': {'colour': 1}}),
            (1, {'Head': {'location': [0, 0, 0], 'rotation_mode': 'XYZ'}}),
            (True, {'Head': {'location': [0, 0, 0]}}),
            (1, {}),
        ]
        for frame, bones in bad:
            with self.assertRaises(ValueError, msg=(frame, bones)):
                ba.check_pose(frame, bones, self.BONES)


class TurnFindings(unittest.TestCase):
    def test_a_turn_over_the_limit_is_found_with_its_frame(self):
        errors, worst = ba.turn_findings({'Right Arm': [10, 20, 44, 20, 10]}, 60, 43)
        self.assertEqual(len(errors), 1)
        self.assertIn('frame 3', errors[0])
        self.assertEqual(worst, (44, 'Right Arm', 3))

    def test_a_lone_spike_is_a_pop_and_a_fast_even_sweep_is_not(self):
        pop, _ = ba.turn_findings({'Head': [1, 1, 20, 1, 1]}, 60, 43)
        sweep, _ = ba.turn_findings({'Head': [30, 32, 35, 32, 30]}, 60, 43)
        self.assertTrue(pop and 'pops' in pop[0])
        self.assertEqual(sweep, [])

    def test_turns_are_judged_per_60th_of_a_second(self):
        at_30, _ = ba.turn_findings({'Arm': [60, 60, 60]}, 30, 43)  # 30 degrees a 60 fps frame
        at_120, _ = ba.turn_findings({'Arm': [30, 30, 30]}, 120, 43)  # 60 a 60 fps frame
        self.assertEqual(at_30, [])
        self.assertEqual(len(at_120), 3)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class PinnedFiles(unittest.TestCase):
    def setUp(self):
        self.blob = b'rig bytes'
        digest = r6.hashlib.sha256(self.blob).hexdigest()
        self.files = {'blend': {'name': 'rig.blend', 'size': len(self.blob), 'sha256': digest,
                                'url': 'https://devforum.roblox.com/uploads/rig.blend'}}

    def test_only_https_on_the_allowed_hosts(self):
        r6._allowed('https://github.com/Cautioned/Blender-Animations-Plugin/releases/download/v2.6.3/x.zip')
        for url in ('http://devforum.roblox.com/x', 'https://example.com/x', 'https://devforum.roblox.com.evil.io/x'):
            with self.assertRaises(ValueError):
                r6._allowed(url)

    def test_the_pins_are_whole(self):
        for key, spec in r6.FILES.items():
            self.assertEqual(len(spec['sha256']), 64, key)
            self.assertGreater(spec['size'], 0)
            r6._allowed(spec['url'])
        self.assertEqual(len(r6.SCRIPTS), 5)

    def test_a_matching_copy_on_disk_is_taken_by_hash(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as home, mock.patch.object(r6, 'FILES', self.files):
            (Path(src) / 'renamed.bin').write_bytes(self.blob)
            out = r6.fetch(source=src, home=home)
            self.assertEqual(out['blend'].read_bytes(), self.blob)

    def test_a_download_that_misses_its_pin_is_thrown_away(self):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse(b'tampered!')
        with tempfile.TemporaryDirectory() as home, mock.patch.object(r6, 'FILES', self.files), \
                mock.patch.object(r6.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(ValueError):
                r6.fetch(home=home)
            self.assertEqual(list(Path(home).iterdir()), [])

    def test_a_good_download_is_kept(self):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse(self.blob)
        with tempfile.TemporaryDirectory() as home, mock.patch.object(r6, 'FILES', self.files), \
                mock.patch.object(r6.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(r6.fetch(home=home)['blend'].read_bytes(), self.blob)

    def test_a_working_copy_never_overwrites(self):
        with tempfile.TemporaryDirectory() as home, mock.patch.object(r6, 'FILES', {**r6.FILES, 'blend': self.files['blend']}):
            (Path(home) / 'rig.blend').write_bytes(self.blob)
            out = Path(home) / 'work.blend'
            r6.copy(out, home=home)
            with self.assertRaises(ValueError):
                r6.copy(out, home=home)


if __name__ == '__main__':
    unittest.main()
