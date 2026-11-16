"""The installers: they omit repo-only MCP config without deleting it from source, update, report status, and uninstall
only what is this skill (a link alone, never what it points to), its Codex permission rules included. Every run is
confined to a temp folder: -HomeDir, HOME and CLAUDE_CONFIG_DIR point there."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which('powershell') if os.name == 'nt' else None
GIT_BASH = Path('C:/Program Files/Git/bin/bash.exe')
SHELL = str(GIT_BASH) if os.name == 'nt' and GIT_BASH.is_file() else shutil.which('sh')
NODE = shutil.which('node')
SKILL = '---\nname: roblox-dev\ndescription: fixture\n---\nfixture skill\n'
WRAPPER_RULE = 'Bash(bash ~/.claude/skills/roblox-dev/scripts/codex/handoff.sh *)'


class InstallerCases:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='roblox-skill-install-')
        self.base = Path(self.temp.name).resolve()
        assert self.base.parent == Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.temp.cleanup)
        self.source = self.base / 'source repo'
        self.source.mkdir()
        self.git('init', '--initial-branch=main', str(self.source))
        self.git('-C', str(self.source), 'config', 'user.name', 'Installer Test')
        self.git('-C', str(self.source), 'config', 'user.email', 'installer@example.invalid')
        (self.source / 'SKILL.md').write_text(SKILL)
        (self.source / '.mcp.json').write_text('{"mcpServers":{}}\n')
        (self.source / 'scripts').mkdir()
        (self.source / 'scripts' / 'helper.txt').write_text('version 1\n')
        (self.source / 'scripts' / 'codex').mkdir()
        for name in ('install.mjs', 'state.mjs'):  # the uninstaller runs the real permission remover
            shutil.copy(ROOT / 'scripts' / 'codex' / name, self.source / 'scripts' / 'codex' / name)
        self.commit()
        self.project = self.base / 'target project'
        self.project.mkdir()
        self.target = self.project / '.agents' / 'skills' / 'roblox-dev'
        self.claude_link = self.project / '.claude' / 'skills' / 'roblox-dev'

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, capture_output=True, text=True)

    def commit(self):
        self.git('-C', str(self.source), 'add', '.')
        self.git('-C', str(self.source), 'commit', '-m', 'fixture')

    def run_installer(self, *flags, local=False):
        """One installer run, global unless local, confined to the temp project. Flags are named once: 'update' is
        -Update for PowerShell and --update for sh."""
        env = dict(os.environ, ROBLOX_DEV_REPO=str(self.source), CLAUDE_CONFIG_DIR=str(self.project / '.claude'))
        for name in ('ROBLOX_DEV_LEARNING_HOME', 'CODEX_HANDOFF_HOME'):
            env.pop(name, None)
        if self.powershell:
            # HomeDir isolates the global-install path without changing HOME.
            command = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                       '-File', str(ROOT / 'install' / 'install.ps1'), '-HomeDir', str(self.project)]
            if local:
                command += ['-Local', '-Project', str(self.project)]
            command += ['-' + flag.capitalize() for flag in flags]
        else:
            env['HOME'] = str(self.project)
            command = [SHELL, str(ROOT / 'install' / 'install.sh')]
            if local:
                command += ['--local', '--project', str(self.project)]
            command += ['--' + flag for flag in flags]
        return subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)

    def install(self, local=False):
        # The sh default is local: existing git installs retain their history either way.
        result = self.run_installer(local=local or not self.powershell)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def ok(self, *flags, local=False):
        result = self.run_installer(*flags, local=local)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def link(self, path, to):
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.powershell:
            subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-Command',
                            "New-Item -ItemType Junction -Path '{}' -Target '{}' | Out-Null".format(
                                str(path).replace("'", "''"), str(to).replace("'", "''"))],
                           check=True, capture_output=True)
        else:
            path.symlink_to(to, target_is_directory=True)

    def test_fresh_install_excludes_mcp_and_preserves_skill_files(self):
        self.install()
        self.assertTrue((self.target / 'SKILL.md').is_file())
        self.assertEqual((self.target / 'scripts' / 'helper.txt').read_text(), 'version 1\n')
        self.assertFalse((self.target / '.mcp.json').exists())
        self.assertTrue((self.source / '.mcp.json').is_file())
        self.assertEqual((self.target / '.git').exists(), self.powershell)

    def test_update_removes_tracked_mcp_and_keeps_future_updates_excluded(self):
        self.target.parent.mkdir(parents=True)
        self.git('clone', str(self.source), str(self.target))
        self.assertTrue((self.target / '.mcp.json').is_file())
        for version in (2, 3):
            (self.source / 'scripts' / 'helper.txt').write_text(f'version {version}\n')
            (self.source / '.mcp.json').write_text('{"mcpServers":{"new":{}}}\n' + ' ' * version)
            self.commit()
            self.install()
            self.assertEqual((self.target / 'scripts' / 'helper.txt').read_text(), f'version {version}\n')
            self.assertFalse((self.target / '.mcp.json').exists())
            self.assertTrue((self.source / '.mcp.json').is_file())
            self.assertTrue((self.target / '.git').exists())

    def test_developer_link_is_left_untouched(self):
        if os.name == 'nt' and not self.powershell:
            self.skipTest('Use the PowerShell installer for Windows junctions')
        self.link(self.target, self.source)
        self.install()
        self.assertTrue((self.source / '.mcp.json').is_file())
        self.assertTrue((self.target / '.mcp.json').is_file())
        self.assertEqual(self.git('-C', str(self.source), 'status', '--porcelain').stdout, '')

    def test_status_reports_missing_then_installed(self):
        missing = self.run_installer('status')
        self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
        self.assertIn('not installed', missing.stdout)
        self.ok()
        found = self.ok('status')
        self.assertIn('roblox-dev', found)
        self.assertIn('a git checkout at', found)
        self.assertNotIn('not this skill', found)

    def test_update_needs_an_install(self):
        result = self.run_installer('update')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not installed', result.stdout + result.stderr)
        self.assertFalse(os.path.lexists(self.target))

    def test_global_update_pulls_the_latest(self):
        self.ok()
        (self.source / 'scripts' / 'helper.txt').write_text('version 2\n')
        self.commit()
        self.assertIn('Updated', self.ok('update'))
        self.assertEqual((self.target / 'scripts' / 'helper.txt').read_text(), 'version 2\n')
        self.assertIn('Up to date', self.ok('update'))

    def test_update_replaces_a_local_copy(self):
        self.ok(local=True)
        self.assertFalse((self.target / '.git').exists())
        (self.source / 'scripts' / 'helper.txt').write_text('version 2\n')
        self.commit()
        self.ok('update', local=True)
        self.assertEqual((self.target / 'scripts' / 'helper.txt').read_text(), 'version 2\n')
        self.assertFalse((self.target / '.git').exists())
        self.assertFalse((self.target / '.mcp.json').exists())

    def test_uninstall_removes_the_skill_and_claudes_link(self):
        (self.project / '.agents').mkdir()
        (self.project / '.claude').mkdir()  # both: the copy goes to .agents and Claude gets a link to it
        self.ok()
        self.assertTrue((self.target / 'SKILL.md').is_file())
        self.assertTrue(os.path.lexists(self.claude_link))
        out = self.ok('uninstall')
        self.assertIn('Removed', out)
        self.assertFalse(os.path.lexists(self.target))
        self.assertFalse(os.path.lexists(self.claude_link))
        self.assertTrue((self.project / '.claude').is_dir())
        self.assertTrue((self.source / 'SKILL.md').is_file() and (self.source / '.mcp.json').is_file())
        again = self.ok('uninstall')
        self.assertIn('not installed', again)

    def test_uninstall_leaves_another_skill_unless_forced(self):
        self.target.mkdir(parents=True)
        (self.target / 'SKILL.md').write_text('---\nname: another-skill\n---\n')
        out = self.ok('uninstall')
        self.assertIn('left untouched', out)
        self.assertTrue((self.target / 'SKILL.md').is_file())
        self.ok('uninstall', 'force')
        self.assertFalse(os.path.lexists(self.target))

    def test_uninstall_removes_only_a_developer_link(self):
        if os.name == 'nt' and not self.powershell:
            self.skipTest('Use the PowerShell installer for Windows junctions')
        self.link(self.target, self.source)
        out = self.ok('uninstall')
        self.assertIn('was not touched', out)
        self.assertFalse(os.path.lexists(self.target))
        self.assertTrue((self.source / 'SKILL.md').is_file() and (self.source / '.mcp.json').is_file())
        self.assertTrue((self.source / 'scripts' / 'helper.txt').is_file())
        self.assertEqual(self.git('-C', str(self.source), 'status', '--porcelain').stdout, '')

    def test_uninstall_keeps_data_unless_purged(self):
        notes = self.project / '.roblox-dev' / 'learning' / 'notes' / 'a-note'
        notes.mkdir(parents=True)
        (notes / 'note.md').write_text('a note\n')
        runs = self.project / '.claude' / 'codex-handoffs'
        runs.mkdir(parents=True)
        (runs / 'ledger.tsv').write_text('run\n')
        self.ok()
        out = self.ok('uninstall')
        self.assertIn('Kept the learning notes', out)
        self.assertIn('Kept the Codex handoff state', out)
        self.assertTrue((notes / 'note.md').is_file() and (runs / 'ledger.tsv').is_file())
        self.ok('uninstall', 'purge')
        self.assertFalse(os.path.lexists(self.project / '.roblox-dev'))
        self.assertFalse(os.path.lexists(runs))
        self.assertTrue((self.project / '.claude').is_dir())

    def test_purge_goes_with_uninstall(self):
        result = self.run_installer('purge')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(os.path.lexists(self.target))

    @unittest.skipUnless(NODE, 'Node is unavailable')
    def test_uninstall_takes_out_the_codex_permission_rules(self):
        self.ok()
        settings = self.project / '.claude' / 'settings.json'
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps({'theme': 'dark', 'permissions': {'allow': ['Bash(git status)', WRAPPER_RULE]},
                                        'autoMode': {'allow': ['$defaults', 'Running the roblox-dev Codex handoff wrapper (x)', 'Mine']}}))
        self.ok('uninstall')
        kept = json.loads(settings.read_text())
        self.assertEqual(kept['theme'], 'dark')
        self.assertEqual(kept['permissions']['allow'], ['Bash(git status)'])
        self.assertEqual(kept['autoMode']['allow'], ['$defaults', 'Mine'])

    def test_local_uninstall_leaves_global_settings_alone(self):
        settings = self.project / '.claude' / 'settings.json'
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({'permissions': {'allow': [WRAPPER_RULE]}}))
        (self.project / '.agents').mkdir()
        self.ok(local=True)
        self.assertTrue((self.target / 'SKILL.md').is_file())
        self.ok('uninstall', local=True)
        self.assertFalse(os.path.lexists(self.target))
        self.assertFalse(os.path.lexists(self.claude_link))
        self.assertEqual(json.loads(settings.read_text())['permissions']['allow'], [WRAPPER_RULE])


@unittest.skipUnless(POWERSHELL, 'Windows PowerShell is unavailable')
class PowerShellInstallerTests(InstallerCases, unittest.TestCase):
    powershell = True

    def test_local_install_excludes_mcp_and_drops_git(self):
        self.install(local=True)
        self.assertTrue((self.target / 'SKILL.md').is_file())
        self.assertFalse((self.target / '.mcp.json').exists())
        self.assertFalse((self.target / '.git').exists())


@unittest.skipUnless(SHELL, 'POSIX shell is unavailable')
class ShellInstallerTests(InstallerCases, unittest.TestCase):
    powershell = False


if __name__ == '__main__':
    unittest.main()
