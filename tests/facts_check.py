"""What a change to the docs lost: every number, backticked name and URL missing from the current docs and scripts.

  python tests/facts_check.py <git-ref>        against a commit: what a rewrite dropped from the old docs
  python tests/facts_check.py --notes ID...    against learning notes, pending or archived: what a quality update left
                                               out of each lesson's rule, evidence and change

A reword is fine; a value, API or link that vanished is a lost fact until shown to be a true duplicate, or, for a note,
one project's own name or value, which the quality update's record lists with the reason it stayed out.
Prints what is missing with where it came from. Exit code 1 when anything is."""
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


def check_ref(ref, now):
    missing = 0
    for name, text in sorted(old_docs(ref).items()):
        lost = {v: where for v, where in facts(text).items() if v not in now}
        for value, (number, line) in sorted(lost.items(), key=lambda kv: kv[1][0]):
            print(f'{name}:{number}: {value!r}\n    {line[:150]}')
            missing += 1
    print(f'{missing} facts missing')
    return 1 if missing else 0


def note_lessons(note_ids):
    """(note id, rule, text) for each lesson of the notes named, looked up in the learning home's notes, then its archive."""
    sys.path.insert(0, str(ROOT / 'scripts'))
    import learn
    for note_id in note_ids:
        path = next((p for p in (learn.home() / 'notes' / note_id / 'note.md', learn.home() / 'archive' / note_id / 'note.md') if p.exists()), None)
        if path is None:
            sys.exit(f'no note {note_id} under {learn.home()}')
        _, body = learn.parse(path.read_text(encoding='utf-8').replace('\r\n', '\n'))
        for rule, labels in learn.lessons_of(body):
            yield note_id, rule, '\n'.join([rule, labels.get('Evidence', ''), labels.get('Change', '')])


def check_notes(note_ids, now):
    missing = 0
    for note_id, rule, text in note_lessons(note_ids):
        lost = [value for value in facts(text) if value not in now]
        if lost:
            print(f'{note_id} | {rule}\n    ' + ', '.join(repr(value) for value in lost))
            missing += len(lost)
    print(f'{missing} facts missing')
    return 1 if missing else 0


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1 and args[0] == '--notes':
        return check_notes(args[1:], new_text())
    if len(args) != 1 or args[0].startswith('-'):
        sys.exit(__doc__)
    return check_ref(args[0], new_text())


if __name__ == '__main__':
    sys.exit(main())
