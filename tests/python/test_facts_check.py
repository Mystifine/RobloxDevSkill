"""tests/facts_check.py's notes mode: every number, backticked name and URL in a lesson must reach the skill, or be listed."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('facts_check', ROOT / 'tests' / 'facts_check.py')
facts_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facts_check)

NOTE = """---
title: hull outlines
agent: test
project: Example
references: [art/modeling.md]
outcome: accepted
rounds: 0
---

## Prompt
> Outline the props.

## Lessons

### Outline cartoon props with an inverted hull
- Kind: technique
- Basis: measured
- Evidence: each piece grown 0.13 studs along its normals, tinted with `SurfaceAppearance.Color`.
- Change: references/art/modeling.md: the recipe.

### Keep labels clear
- Kind: technique
- Basis: measured
- Evidence: lifts of 2.2 and 3.4 studs cleared them.
- Change: none yet.
"""


class Notes(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        folder = Path(self.home.name) / 'archive' / 'n1'
        folder.mkdir(parents=True)
        (folder / 'note.md').write_text(NOTE.replace('\n', '\r\n'), encoding='utf-8')
        patcher = mock.patch.dict(os.environ, {'ROBLOX_DEV_LEARNING_HOME': self.home.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_check(self, now):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = facts_check.check_notes(['n1'], now)
        return code, out.getvalue()

    def test_a_lesson_fact_missing_from_the_skill_is_listed_by_lesson(self):
        code, out = self.run_check('a hull grown 0.13 studs; labels lifted 2.2 and 3.4 studs')
        self.assertEqual(code, 1)
        self.assertIn('n1 | Outline cartoon props with an inverted hull', out)
        self.assertIn("'SurfaceAppearance.Color'", out)
        self.assertNotIn('Keep labels clear', out)
        self.assertIn('1 facts missing', out)

    def test_every_fact_present_passes(self):
        code, out = self.run_check('0.13 studs, `SurfaceAppearance.Color`, 2.2 and 3.4 studs')
        self.assertEqual(code, 0)
        self.assertIn('0 facts missing', out)

    def test_a_pending_note_is_found_before_the_archive(self):
        pending = Path(self.home.name) / 'notes' / 'n1'
        pending.mkdir(parents=True)
        (pending / 'note.md').write_text(NOTE.replace('0.13', '0.21'), encoding='utf-8')
        code, out = self.run_check('0.13 studs, `SurfaceAppearance.Color`, 2.2 and 3.4 studs')
        self.assertEqual(code, 1)
        self.assertIn("'0.21 studs'", out)  # a number keeps its unit, as in the ref check

    def test_an_unknown_note_stops_with_its_name(self):
        with self.assertRaises(SystemExit) as stopped:
            list(facts_check.note_lessons(['missing-note']))
        self.assertIn('missing-note', str(stopped.exception.code))

    def test_notes_without_ids_shows_the_usage(self):
        with self.assertRaises(SystemExit) as stopped:
            facts_check.main(['--notes'])
        self.assertIn('--notes ID', str(stopped.exception.code))


if __name__ == '__main__':
    unittest.main()
