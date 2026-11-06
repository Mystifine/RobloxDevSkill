"""r15_motion/pipeline.py, the parts that need no Studio: how a joint's keys are packed, which clips a run picks, and what upload demands."""
import base64
import contextlib
import importlib.util
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('r15_pipeline', ROOT / 'scripts' / 'r15_motion' / 'pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class Pack(unittest.TestCase):
    def test_a_joints_keys_come_back_from_their_bytes(self):
        packed = pipeline.pack({'F': [0, 30], 'Q': [1, 0, 0, 0, 0.5, 0.5, 0.5, 0.5], 'P': [0, 1, -2, 0.25, 0, 0]})
        self.assertEqual(packed['N'], 2)
        self.assertTrue(packed['O'])
        raw = base64.b64decode(packed['D'])
        frame, *quaternion = struct.unpack_from('<H4h', raw, 0)
        offset = struct.unpack_from('<3h', raw, 10)
        self.assertEqual(frame, 0)
        self.assertEqual(quaternion, [32767, 0, 0, 0])
        self.assertEqual(offset, (0, 4096, -8192))

    def test_a_joint_with_no_offset_says_so(self):
        self.assertFalse(pipeline.pack({'F': [0], 'Q': [1, 0, 0, 0], 'P': None})['O'])


class Choosing(unittest.TestCase):
    def test_names_pick_clips_and_none_picks_them_all(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('Wave', 'Flip'):
                (Path(folder) / f'{name}.json').write_text('{}', encoding='utf-8')
            self.assertEqual([p.stem for p in pipeline.wanted('Wave', Path(folder), '.json')], ['Wave'])
            self.assertEqual([p.stem for p in pipeline.wanted(None, Path(folder), '.json')], ['Flip', 'Wave'])

    def test_upload_asks_who_owns_the_clips(self):
        argv = ['pipeline.py', 'upload']
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            pipeline.main()
        self.assertEqual(stopped.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
