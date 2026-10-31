"""The upload batch and the Blender finder."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import find_blender
import upload_asset


class UploadBatchTests(unittest.TestCase):
    def run_batch(self, files, manifest, sent, results):
        def fake(a, path):
            sent.append(os.path.basename(path))
            code = results.get(os.path.basename(path), 0)
            return code, {'assetId': '1', 'moderation': 'Approved' if code == 0 else 'Rejected'}
        argv = ['upload_asset.py', *files, '--group', '1', '--manifest', str(manifest)]
        with patch.object(sys, 'argv', argv), patch.object(upload_asset, 'upload', fake), contextlib.redirect_stdout(io.StringIO()):
            return upload_asset.main()

    def test_batch_stops_at_a_rejection_and_reuses_what_is_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, c = (Path(tmp) / f'{n}.png' for n in 'abc')
            for path in (a, b, c):
                path.write_text(path.name)
            manifest, sent = Path(tmp) / 'assets.json', []
            self.assertEqual(self.run_batch([str(a), str(b), str(c)], manifest, sent, {'b.png': 2}), 2)
            self.assertEqual(sent, ['a.png', 'b.png'])
            self.assertEqual(list(json.loads(manifest.read_text())), ['a'])
            sent.clear()
            self.assertEqual(self.run_batch([str(a), str(b), str(c)], manifest, sent, {}), 0)
            self.assertEqual(sent, ['b.png', 'c.png'])
            a.write_text('changed')
            sent.clear()
            self.assertEqual(self.run_batch([str(a), str(b), str(c)], manifest, sent, {}), 0)
            self.assertEqual(sent, ['a.png'])
            self.assertEqual(json.loads(manifest.read_text())['a']['sha256'], hashlib.sha256(b'changed').hexdigest())

    def test_a_dry_run_records_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            art, manifest = Path(tmp) / 'a.png', Path(tmp) / 'assets.json'
            art.write_text('x')
            argv = ['upload_asset.py', str(art), '--group', '1', '--manifest', str(manifest), '--dry-run']
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(upload_asset.main(), 0)
            self.assertFalse(manifest.exists())


class FindBlenderTests(unittest.TestCase):
    def test_the_order_is_override_path_running_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'one', Path(tmp) / 'two'
            first.write_text('')
            second.write_text('')
            with patch.dict(os.environ, {'BLENDER': str(first)}), patch.object(find_blender.shutil, 'which', return_value=str(second)):
                self.assertEqual(find_blender.find(), str(first))
            with patch.dict(os.environ, {'BLENDER': ''}), patch.object(find_blender.shutil, 'which', return_value=None), \
                    patch.object(find_blender, 'running', return_value=[str(second)]), patch.object(find_blender, 'installed', return_value=[str(first)]):
                self.assertEqual(find_blender.find(), str(second))
            with patch.dict(os.environ, {'BLENDER': ''}), patch.object(find_blender.shutil, 'which', return_value=None), \
                    patch.object(find_blender, 'running', return_value=[]), patch.object(find_blender, 'installed', return_value=[]):
                self.assertIsNone(find_blender.find())

    def test_newest_install_comes_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            for version in ('4.2', '5.1'):
                path = Path(tmp) / 'Blender Foundation' / f'Blender {version}'
                path.mkdir(parents=True)
                (path / 'blender.exe').write_text('')
            with patch.dict(os.environ, {'ProgramFiles': tmp, 'ProgramFiles(x86)': ''}):
                self.assertIn('5.1', find_blender.installed()[0])


if __name__ == '__main__':
    unittest.main()
