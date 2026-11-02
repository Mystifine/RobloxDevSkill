"""Learning notes, in a temporary folder. Nothing leaves the machine, and nothing but the note's own folder changes."""
import contextlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest import mock
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import learn

NOTE = """---
title: "Topbar: read the row height from the device"
agent: test-model
project: test-game
references: [ui/ui.md, ui/topbar.md]
outcome: corrected
rounds: 2
---

## Prompt
> make the coins readout sit in the topbar

## Attachments
None.

## Wanted
A readout level with Roblox's own buttons on every device.

## Output
Changed the HUD layout. Checked in Play on two sizes; phones not checked.

## Response
> it's too low on my phone

## Lessons

### Read the topbar row from the device
- Kind: correction
- Basis: stated
- Evidence: A fixed offset sat low on a phone.
- Change: references/ui/topbar.md: say so.

### Check the topbar on a phone first
- Kind: preference
- Basis: stated
- Evidence: The user tests on a phone.
- Change: none yet
"""


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.state = self.tmp / 'state'
        patch = mock.patch.dict(os.environ, {'ROBLOX_DEV_LEARNING_HOME': str(self.state)})
        patch.start()
        self.addCleanup(patch.stop)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = learn.main(list(args))
        return code, out.getvalue()

    def write_note(self, text=NOTE, name='draft.md'):
        path = self.tmp / name
        path.write_text(text, encoding='utf-8', newline='\n')
        return str(path)

    def on(self):
        self.assertEqual(self.run_cli('on')[0], 0)

    def notes(self):
        return [p.name for p in learn.pending()]

    def kept(self, note_id):
        return (self.state / 'notes' / note_id / 'note.md').read_text(encoding='utf-8')


class Switch(Base):
    def test_it_is_off_until_turned_on_and_writes_nothing(self):
        code, out = self.run_cli('check')
        self.assertEqual(code, 5)
        self.assertIn('nothing to do', out)
        self.assertNotIn('learning.md', out)
        self.assertEqual(self.run_cli('record', self.write_note())[0], 5)
        self.assertFalse(self.state.exists())

    def test_on_sends_the_agent_to_the_reference(self):
        self.on()
        code, out = self.run_cli('check')
        self.assertEqual(code, 0)
        self.assertIn('references/learning/learning.md', out)
        self.assertIn('0 pending', out)

    def test_off_stops_new_notes_and_keeps_the_old(self):
        self.on()
        self.run_cli('record', self.write_note())
        code, out = self.run_cli('off')
        self.assertEqual(code, 0)
        self.assertIn('1 pending', out)
        self.assertEqual(len(self.notes()), 1)
        self.assertEqual(self.run_cli('check')[0], 5)
        self.assertEqual(self.run_cli('record', self.write_note())[0], 5)
        self.assertEqual(len(self.notes()), 1)
        self.assertEqual(self.run_cli('off')[0], 0, 'turning off twice is fine')


class Record(Base):
    def test_a_note_is_filed_and_filled_in(self):
        self.on()
        code, out = self.run_cli('record', self.write_note())
        self.assertEqual(code, 0, out)
        note_id = self.notes()[0]
        self.assertRegex(note_id, r'^\d{4}-\d\d-\d\d-topbar-read-the-row-height-from-the-device-[0-9a-f]{6}$')
        self.assertIn(note_id, out)
        fields, body = learn.parse(self.kept(note_id))
        self.assertEqual(fields['id'], note_id)
        self.assertEqual(learn.as_text(fields['title']), 'Topbar: read the row height from the device')
        self.assertEqual(learn.as_text(fields['project']), 'test-game')
        self.assertEqual(fields['tasks'], '[ui]')
        self.assertEqual(fields['kinds'], '[correction, preference]')
        self.assertRegex(fields['skill_commit'], r'^([0-9a-f]{4,}|unknown)$')
        self.assertRegex(fields['date'], r'^\d{4}-\d\d-\d\d$')
        self.assertIn("## Response\n> it's too low on my phone", body)

    def test_it_changes_nothing_but_its_own_folder_and_only_reads_the_version(self):
        before = git('status', '--porcelain'), git('rev-parse', 'HEAD')
        real = subprocess.run
        calls = []

        def watching(args, **options):
            calls.append(args)
            return real(args, **options)
        self.on()
        with mock.patch.object(learn.subprocess, 'run', watching):
            self.assertEqual(self.run_cli('record', self.write_note())[0], 0)
        self.assertEqual((git('status', '--porcelain'), git('rev-parse', 'HEAD')), before)
        self.assertEqual(calls, [['git', 'rev-parse', '--short', 'HEAD']])

    def test_without_git_the_note_is_still_kept(self):
        self.on()
        with mock.patch.object(learn.subprocess, 'run', side_effect=FileNotFoundError('git')):
            self.assertEqual(self.run_cli('record', self.write_note())[0], 0)
        self.assertIn('skill_commit: unknown', self.kept(self.notes()[0]))

    def test_a_local_install_does_not_report_the_project_around_it(self):
        self.on()
        with mock.patch.object(learn, 'ROOT', self.tmp), mock.patch.object(learn.subprocess, 'run', side_effect=AssertionError('asked git')):
            self.assertEqual(learn.skill_commit(), 'unknown')

    def test_two_notes_with_one_title_stay_apart(self):
        self.on()
        self.run_cli('record', self.write_note())
        self.run_cli('record', self.write_note())
        self.assertEqual(len(self.notes()), 2)

    def test_windows_line_endings_and_no_references_are_fine(self):
        self.on()
        text = NOTE.replace('references: [ui/ui.md, ui/topbar.md]', 'references: []').replace('\n', '\r\n')
        path = self.tmp / 'crlf.md'
        path.write_bytes(text.encode('utf-8'))
        self.assertEqual(self.run_cli('record', str(path))[0], 0)
        note = self.kept(self.notes()[0])
        self.assertIn('tasks: []', note)
        self.assertNotIn('\r', note)

    def test_utf16_from_a_powershell_redirect_is_refused_not_mangled(self):
        self.on()
        path = self.tmp / 'wide.md'
        path.write_bytes(NOTE.encode('utf-16'))
        code, out = self.run_cli('record', str(path))
        self.assertEqual(code, 2)
        self.assertIn('UTF-8', out)
        self.assertEqual(self.notes(), [])


class Attachments(Base):
    def attach(self, name, note=None):
        path = self.tmp / name
        path.write_bytes(b'bytes')
        text = note if note is not None else NOTE.replace('## Attachments\nNone.', f'## Attachments\nThe concept sheet, {name}.')
        return self.run_cli('record', self.write_note(text), '--attach', str(path))

    def test_a_file_goes_beside_its_note(self):
        self.on()
        code, out = self.attach('concept.png')
        self.assertEqual(code, 0, out)
        self.assertEqual((self.state / 'notes' / self.notes()[0] / 'concept.png').read_bytes(), b'bytes')

    def test_what_is_refused(self):
        self.on()
        self.assertIn('another name', self.attach('note.md')[1])
        self.assertIn('name it in the Attachments section', self.attach('concept.png', note=NOTE)[1])
        self.assertIn('no such file', self.run_cli('record', self.write_note(), '--attach', str(self.tmp / 'gone.png'))[1])
        self.assertEqual(self.notes(), [])


class Format(Base):
    def refused(self, text):
        self.on()
        code, out = self.run_cli('record', self.write_note(text))
        self.assertEqual(code, 2, out)
        self.assertEqual(self.notes(), [])
        return out

    def test_everything_wrong_is_listed_at_once(self):
        out = self.refused(NOTE.replace('outcome: corrected', 'outcome: fine').replace('rounds: 2', 'rounds: two').replace('references: [ui/ui.md, ui/topbar.md]', 'references: [ui/nope.md]').replace('- Kind: correction', '- Kind: oops').replace('- Basis: stated\n- Evidence: A fixed', '- Evidence: A fixed').replace('agent: test-model\n', 'surprise: yes\n'))
        for piece in ('outcome must be', 'rounds must be', 'ui/nope.md', 'Kind must be', 'missing `- Basis:`', 'missing `agent`', 'unknown field `surprise`'):
            self.assertIn(piece, out)

    def test_structure(self):
        self.assertIn('front matter', self.refused('no front matter'))
        self.assertIn('missing `project`', self.refused(NOTE.replace('project: test-game\n', '')))
        self.assertIn('the sections must be', self.refused(NOTE.replace('## Wanted\n', '')))
        self.assertIn('the sections must be', self.refused(NOTE.replace('> make the coins', '## Output\nmake the coins')))
        self.assertIn('the Response section is empty', self.refused(NOTE.replace("> it's too low on my phone\n", '')))
        self.assertIn('at least one ### rule', self.refused(NOTE[:NOTE.index('### Read')]))
        self.assertIn('over 16000', self.refused(NOTE.replace('None.', 'x ' * 9000)))
        self.assertIn('at most 100', self.refused(NOTE.replace('Topbar:', 'x' * 100)))

    def test_a_prompt_quoting_headings_is_fine(self):
        self.on()
        self.assertEqual(self.run_cli('record', self.write_note(NOTE.replace('> make the coins', '> ## Output\n> make the coins')))[0], 0)


class QualityUpdate(Base):
    def seed(self):
        self.on()
        self.run_cli('record', self.write_note())
        other = NOTE.replace('project: test-game', 'project: other-game').replace('Topbar: read', 'Second: read').replace('Check the topbar on a phone first', 'Name the safe area').replace('- Change: none yet', '- Change: references/ui/topbar.md: name it.').replace('- Kind: preference', '- Kind: skill-gap')
        self.run_cli('record', self.write_note(other))
        return self.notes()

    def test_nothing_pending(self):
        self.assertEqual(self.run_cli('digest'), (0, 'no notes pending\n'))

    def test_the_digest_works_with_notes_turned_off(self):
        self.seed()
        self.run_cli('off')
        self.assertIn('2 notes pending', self.run_cli('digest')[1])

    def test_lessons_are_grouped_by_the_file_they_would_change_commonest_first(self):
        ids = self.seed()
        code, out = self.run_cli('digest')
        self.assertEqual(code, 0)
        self.assertIn('2 notes pending', out)
        self.assertLess(out.index('## references/ui/topbar.md (3)'), out.index('## no file named (1)'))
        self.assertIn('- Name the safe area [skill-gap, stated; other-game;', out)
        self.assertIn('Evidence: A fixed offset sat low on a phone.', out)
        self.assertIn('Change: references/ui/topbar.md: say so.', out)
        for note_id in ids:
            self.assertIn(note_id, out)
        self.assertIn("corrected, 2 rounds | wanted: A readout level with Roblox's own buttons on every device.", out)

    def test_a_damaged_note_does_not_stop_the_digest(self):
        ids = self.seed()
        (self.state / 'notes' / ids[0] / 'note.md').write_text('damaged', encoding='utf-8')
        code, out = self.run_cli('digest')
        self.assertEqual(code, 0)
        self.assertIn(f'{ids[0]}: unreadable', out)
        self.assertIn(ids[1], out)

    def test_archive_takes_notes_out_of_the_digest_and_keeps_them(self):
        ids = self.seed()
        self.assertEqual(self.run_cli('archive', ids[0])[0], 0)
        self.assertEqual(self.notes(), [ids[1]])
        self.assertTrue((self.state / 'archive' / ids[0] / 'note.md').is_file())
        self.assertNotIn(ids[0], self.run_cli('digest')[1])

    def test_a_wrong_id_moves_nothing(self):
        ids = self.seed()
        for wrong in ('nope', '../notes', ''):
            code, out = self.run_cli('archive', ids[0], wrong)
            self.assertEqual(code, 2, wrong)
            self.assertIn('nothing was moved', out)
        self.assertEqual(self.notes(), ids)


class Docs(unittest.TestCase):
    def reference(self):
        return (ROOT / 'references/learning/learning.md').read_text(encoding='utf-8')

    def test_the_template_in_the_reference_is_accepted(self):
        fields, body = learn.parse(re.search(r'```markdown\n(.*?)```', self.reference(), re.S).group(1))
        self.assertEqual(learn.format_problems(fields, body), [])

    def test_the_reference_lists_every_kind_outcome_and_basis(self):
        for value in (*learn.KINDS, *learn.OUTCOMES, *learn.BASES):
            self.assertIn(f'`{value}`', self.reference())

    def test_the_rule_runs_the_check_the_script_answers(self):
        self.assertIn('python scripts/learn.py check', (ROOT / 'SKILL.md').read_text(encoding='utf-8'))

    def test_notes_are_kept_where_nothing_cleans_or_moves_them(self):
        with mock.patch.dict(os.environ):
            os.environ.pop('ROBLOX_DEV_LEARNING_HOME', None)
            home = learn.home().resolve()
        self.assertFalse(home.is_relative_to(ROOT), 'installs replace the skill folder')
        self.assertFalse(home.is_relative_to(Path(tempfile.gettempdir()).resolve()), 'the system cleans its temp folder')
        for folder in ('.agents', '.claude'):
            self.assertNotIn(folder, home.parts, 'the installers read these')


if __name__ == '__main__':
    unittest.main()
