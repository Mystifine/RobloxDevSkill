"""Learning notes: what using the skill teaches, kept on this machine for a later quality update (references/learning/learning.md,
references/learning/quality-update.md). Off until turned on, so anyone else who installs the skill writes nothing. Nothing is ever sent anywhere.

  python learn.py on | off
  python learn.py check
  python learn.py record NOTE.md [--attach FILE]...
  python learn.py digest
  python learn.py archive ID...

- on, off: off stops new notes and keeps the ones there.
- check: whether to write a note. Prints what to do, so the agent reads the reference only when notes are on.
- record: refuses a malformed note, fills in id, date, skill_commit, tasks and kinds, and files it with its attachments.
- digest: for a quality update, every pending lesson grouped by the file it would change, then each note in a line.
- archive: moves notes a quality update has dealt with out of the digest. They are kept.

- Where: ROBLOX_DEV_LEARNING_HOME, by default ~/.roblox-dev/learning, holding notes/<id>/note.md and archive/<id>/note.md. Not the system's temp folder,
  which gets cleaned, nor the skill's folder, which installs replace, nor ~/.agents, whose existence decides where the installers put the skill.

Exit codes: 0 ready or done, 2 refused or bad usage, 5 turned off."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent
MAX_NOTE = 16000  # characters: a note describes the work, it does not carry it
FIELDS = ('title', 'agent', 'project', 'references', 'outcome', 'rounds')
SECTIONS = ('Prompt', 'Attachments', 'Wanted', 'Output', 'Response', 'Lessons')
OUTCOMES = ('accepted', 'corrected', 'rejected', 'abandoned', 'unknown')
KINDS = ('preference', 'correction', 'skill-wrong', 'skill-gap', 'routing', 'platform-fact', 'technique')
BASES = ('stated', 'measured', 'inferred')
TURNED_OFF = 'learning notes are off: nothing to do, and no need to mention it'


class Refused(Exception):
    def __init__(self, problems):
        super().__init__('; '.join(problems))
        self.problems = problems


def home():
    return Path(os.environ.get('ROBLOX_DEV_LEARNING_HOME') or Path.home() / '.roblox-dev' / 'learning')


def is_on():
    return (home() / 'enabled').exists()


def pending():
    notes = home() / 'notes'
    return sorted(p for p in notes.iterdir() if p.is_dir()) if notes.is_dir() else []


def parse(text):
    """(front matter as raw strings, body), or raises Refused."""
    found = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    if not found:
        raise Refused(['the note must open with a front matter block between --- lines'])
    fields = {}
    for line in found.group(1).splitlines():
        key, _, value = line.partition(':')
        fields[key.strip()] = value.strip()
    return fields, found.group(2)


def as_text(value):
    if value.startswith('"'):
        try:
            return json.loads(value)
        except ValueError:
            pass
    return value


def as_list(value):
    return [v.strip() for v in value.strip('[] ').split(',') if v.strip()]


def lessons_of(body):
    """[(rule, {label: value})] under the Lessons heading."""
    section = re.split(r'^## Lessons[ \t]*$', body, flags=re.M)[-1]
    parts = re.split(r'^### (.+)$', section, flags=re.M)[1:]
    return [(rule.strip(), dict(re.findall(r'^- (Kind|Basis|Evidence|Change): *(.*)$', text, flags=re.M))) for rule, text in zip(parts[::2], parts[1::2])]


def format_problems(fields, body):
    problems = [f'front matter is missing `{key}`' for key in FIELDS if not fields.get(key)]
    problems += [f'front matter has an unknown field `{key}`' for key in fields if key not in FIELDS]
    if fields.get('outcome') and fields['outcome'] not in OUTCOMES:
        problems.append(f'outcome must be one of {", ".join(OUTCOMES)}')
    if fields.get('rounds') and not fields['rounds'].isdigit():
        problems.append('rounds must be a whole number')
    if len(as_text(fields.get('title', ''))) > 100:
        problems.append('title must be at most 100 characters')
    for reference in as_list(fields.get('references', '')):
        if not (ROOT / 'references' / reference).is_file():
            problems.append(f'references names `{reference}`, which is not under references/')
    parts = re.split(r'^## (' + '|'.join(SECTIONS) + r')[ \t]*$', body, flags=re.M)
    if parts[1::2] != list(SECTIONS):
        problems.append(f'the sections must be {", ".join(SECTIONS)}, in that order, once each (quote a prompt with > so its headings do not count)')
    else:
        problems += [f'the {name} section is empty: write None. if there is nothing' for name, text in zip(parts[1::2], parts[2::2]) if not text.strip()]
    lessons = lessons_of(body)
    if not lessons:
        problems.append('Lessons needs at least one ### rule')
    for rule, labels in lessons:
        for label in ('Kind', 'Basis', 'Evidence', 'Change'):
            if not labels.get(label, '').strip():
                problems.append(f'lesson "{rule[:40]}" is missing `- {label}:`')
        if labels.get('Kind') and labels['Kind'].strip() not in KINDS:
            problems.append(f'lesson "{rule[:40]}": Kind must be one of {", ".join(KINDS)}')
        if labels.get('Basis') and labels['Basis'].strip() not in BASES:
            problems.append(f'lesson "{rule[:40]}": Basis must be one of {", ".join(BASES)}')
    return problems


def attachment_problems(paths, body):
    names = [p.name for p in paths]
    problems = []
    for path in paths:
        if not path.is_file():
            problems.append(f'{path.name}: no such file')
        elif path.name == 'note.md' or names.count(path.name) > 1:
            problems.append(f'{path.name}: give the attachment another name')
        elif path.name not in body:
            problems.append(f'{path.name}: name it in the Attachments section')
    return problems


def skill_commit():
    """Which version of the skill taught this. A local install has no .git, and asking git there would answer for the project around it."""
    if not (ROOT / '.git').exists():
        return 'unknown'
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip() or 'unknown'
    except (OSError, subprocess.TimeoutExpired):
        return 'unknown'


def render(fields, body, note_id, now):
    references = as_list(fields['references'])
    kinds = sorted({labels['Kind'].strip() for _, labels in lessons_of(body)})
    lines = [
        ('id', note_id),
        ('date', now.strftime('%Y-%m-%d')),
        ('skill_commit', skill_commit()),
        ('title', json.dumps(as_text(fields['title']), ensure_ascii=False)),
        ('agent', json.dumps(as_text(fields['agent']), ensure_ascii=False)),
        ('project', json.dumps(as_text(fields['project']), ensure_ascii=False)),
        ('tasks', f'[{", ".join(sorted({r.split("/")[0] for r in references}))}]'),
        ('references', f'[{", ".join(references)}]'),
        ('outcome', fields['outcome']),
        ('rounds', fields['rounds']),
        ('kinds', f'[{", ".join(kinds)}]'),
    ]
    return '---\n' + ''.join(f'{key}: {value}\n' for key, value in lines) + '---\n' + body


def file_note(note, attachments):
    """Checks the note and files it, returning its id, or raises Refused with everything to fix."""
    try:
        text = note.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    except (OSError, UnicodeDecodeError) as e:
        raise Refused([f'cannot read the note as UTF-8 text: {e}']) from e
    fields, body = parse(text)
    problems = format_problems(fields, body) + attachment_problems(attachments, body)
    if len(text) > MAX_NOTE:
        problems.append(f'the note has {len(text)} characters, over {MAX_NOTE}: describe the work instead of including it')
    if problems:
        raise Refused(problems)
    now = datetime.now(timezone.utc)
    slug = re.sub(r'[^a-z0-9]+', '-', as_text(fields['title']).lower()).strip('-')[:50].rstrip('-') or 'note'
    note_id = f'{now:%Y-%m-%d}-{slug}-{uuid.uuid4().hex[:6]}'
    folder = home() / 'notes' / note_id
    folder.mkdir(parents=True)
    (folder / 'note.md').write_bytes(render(fields, body, note_id, now).encode('utf-8'))
    for path in attachments:
        shutil.copy2(path, folder / path.name)
    return note_id


def cmd_on(_):
    (home() / 'notes').mkdir(parents=True, exist_ok=True)
    (home() / 'enabled').touch()
    print(f'learning notes are on: they go to {(home() / "notes").as_posix()}')
    return 0


def cmd_off(_):
    (home() / 'enabled').unlink(missing_ok=True)
    print(f'learning notes are off: kept {len(pending())} pending in {(home() / "notes").as_posix()}')
    return 0


def cmd_check(_):
    if not is_on():
        print(TURNED_OFF)
        return 5
    print(f'ready: read {(ROOT / "references/learning/learning.md").as_posix()}, then write and record the note ({len(pending())} pending so far)')
    return 0


def cmd_record(a):
    if not is_on():
        print(TURNED_OFF)
        return 5
    try:
        note_id = file_note(Path(a.note), [Path(p) for p in a.attach])
    except Refused as e:
        print('refused, nothing was kept:')
        for problem in e.problems:
            print(f'- {problem}')
        return 2
    print(f'kept: {note_id} ({len(pending())} pending)')
    return 0


def cmd_digest(_):
    folders = pending()
    if not folders:
        print('no notes pending')
        return 0
    by_file, notes = {}, []
    for folder in folders:
        try:
            fields, body = parse((folder / 'note.md').read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, Refused):
            notes.append(f'- {folder.name}: unreadable, open it by hand')
            continue
        wanted = re.split(r'^## (?:Wanted|Output)[ \t]*$', body, flags=re.M)
        wanted = ' '.join(wanted[1].split())[:200] if len(wanted) > 1 else ''
        notes.append(f'- {folder.name} | {as_text(fields.get("project", ""))} | {fields.get("outcome")}, {fields.get("rounds")} rounds | wanted: {wanted}')
        for rule, labels in lessons_of(body):
            change = labels.get('Change', '').strip()
            target = re.match(r'[\w./-]+\.\w+', change)
            by_file.setdefault(target.group(0) if target else 'no file named', []).append(
                f'- {rule} [{labels.get("Kind", "").strip()}, {labels.get("Basis", "").strip()}; {as_text(fields.get("project", ""))}; {folder.name}]\n'
                f'  Evidence: {labels.get("Evidence", "").strip()}\n  Change: {change}')
    print(f'{len(folders)} note{"" if len(folders) == 1 else "s"} pending in {(home() / "notes").as_posix()}')
    for target, lessons in sorted(by_file.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f'\n## {target} ({len(lessons)})')
        print('\n'.join(lessons))
    print('\n## Notes')
    print('\n'.join(notes))
    return 0


def cmd_archive(a):
    notes = home() / 'notes'
    missing = [note_id for note_id in a.ids if not note_id or Path(note_id).name != note_id or not (notes / note_id).is_dir()]
    if missing:
        print('refused, nothing was moved. No pending note with the id:')
        for note_id in missing:
            print(f'- {note_id}')
        return 2
    (home() / 'archive').mkdir(parents=True, exist_ok=True)
    for note_id in a.ids:
        shutil.move(str(notes / note_id), str(home() / 'archive' / note_id))
    print(f'archived {len(a.ids)}, {len(pending())} pending')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    commands = ap.add_subparsers(dest='command', required=True)
    commands.add_parser('on', help='keep notes on this machine').set_defaults(run=cmd_on)
    commands.add_parser('off', help='stop new notes; existing ones are kept').set_defaults(run=cmd_off)
    commands.add_parser('check', help='should a note be written?').set_defaults(run=cmd_check)
    record = commands.add_parser('record', help='check a note and keep it')
    record.add_argument('note')
    record.add_argument('--attach', action='append', default=[], metavar='FILE')
    record.set_defaults(run=cmd_record)
    commands.add_parser('digest', help='every pending lesson, for a quality update').set_defaults(run=cmd_digest)
    archive = commands.add_parser('archive', help='move notes out of the digest')
    archive.add_argument('ids', nargs='+', metavar='ID')
    archive.set_defaults(run=cmd_archive)
    a = ap.parse_args(argv)
    return a.run(a)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
