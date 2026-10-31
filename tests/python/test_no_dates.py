"""The skill's notes state facts, with no dates on them. Protocol versions and fixtures that need a date's shape are listed here."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DATE = re.compile(r'\b20\d\d-\d\d-\d\d\b')
ALLOWED = {('scripts/studio_mcp.py', 'protocolVersion'), ('tests/codex/handoff.test.mjs', 'rollout-')}
SUFFIXES = {'.md', '.py', '.luau', '.mjs', '.sh', '.ps1', '.toml', '.yml'}


class NoDatesTests(unittest.TestCase):
    def test_no_note_carries_a_date(self):
        found = []
        for path in ROOT.rglob('*'):
            if path.suffix not in SUFFIXES or not path.is_file() or {'.git', '__pycache__', 'Packages'} & set(path.parts) or path.name == 'test_no_dates.py':
                continue
            name = path.relative_to(ROOT).as_posix()
            for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                if DATE.search(line) and not any(name == f and mark in line for f, mark in ALLOWED):
                    found.append(f'{name}:{number}: {line.strip()[:100]}')
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
