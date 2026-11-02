"""What a rewrite of the docs lost, against a commit: every number, backticked name and URL in the old docs must still exist somewhere in the
new docs or the scripts. A reword is fine; a value, API or link that vanished is a lost fact until shown to be a true duplicate.

  python tests/facts_check.py <git-ref>

Prints what is missing with the line it came from. Exit code 1 when anything is."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FACTS = (re.compile(r'`([^`\n]{2,})`'), re.compile(r'https?://[^\s)>\]]+'), re.compile(r'(?<![\w.])\d[\d,]*(?:\.\d+)?(?:%| ?(?:studs?|px|tokens|triangles|degrees|fps|s\b))?'))


def facts(text):
    found = {}
    for number, line in enumerate(text.splitlines(), 1):
        for pattern in FACTS:
            for m in pattern.finditer(line):
                value = (m.group(1) if m.groups() else m.group(0)).strip().rstrip('.,;:')
                if len(value) > 1:
                    found.setdefault(value, (number, line.strip()))
    return found


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout


def old_docs(ref):
    return {f: git('show', f'{ref}:{f}') for f in git('ls-tree', '-r', '--name-only', ref).splitlines() if f.endswith('.md')}


def new_text():
    parts = [p.read_text(encoding='utf-8', errors='replace') for p in ROOT.rglob('*.md') if '.git' not in p.parts]
    parts += [p.read_text(encoding='utf-8', errors='replace') for p in (ROOT / 'scripts').rglob('*') if p.is_file() and p.suffix in {'.py', '.luau', '.mjs', '.sh'}]
    return '\n'.join(parts)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    now = new_text()
    missing = 0
    for name, text in sorted(old_docs(sys.argv[1]).items()):
        lost = {v: where for v, where in facts(text).items() if v not in now}
        for value, (number, line) in sorted(lost.items(), key=lambda kv: kv[1][0]):
            print(f'{name}:{number}: {value!r}\n    {line[:150]}')
            missing += 1
    print(f'{missing} facts missing')
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
