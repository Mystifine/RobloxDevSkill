"""Installers must omit repo-only MCP config without deleting it from source."""
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
        (self.source / 'SKILL.md').write_text('fixture skill\n')
        (self.source / '.mcp.json').write_text('{"mcpServers":{}}\n')
        (self.source / 'scripts').mkdir()
        (self.source / 'scripts' / 'helper.txt').write_text('version 1\n')
        self.commit()
        self.project = self.base / 'target project'
        self.project.mkdir()
        self.target = self.project / '.agents' / 'skills' / 'roblox-dev'

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, capture_output=True, text=True)

    def commit(self):
        self.git('-C', str(self.source), 'add', '.')
        self.git('-C', str(self.source), 'commit', '-m', 'fixture')

    def install(self, local=False):
        env = dict(os.environ, ROBLOX_DEV_REPO=str(self.source))
        if self.powershell:
            # HomeDir isolates the global-install path without changing HOME.
            command = [POWERSHELL, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                       '-File', str(ROOT / 'install' / 'install.ps1'), '-HomeDir', str(self.project)]
            if local:
                command += ['-Local', '-Project', str(self.project)]
        else:
            # The local base exercises the same clone/update branches without
            # changing HOME. Existing git installs retain their history.
            command = [SHELL, str(ROOT / 'install' / 'install.sh'), '--local', '--project', str(self.project)]
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

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
        self.target.parent.mkdir(parents=True)
        if self.powershell:
            source = str(self.source).replace("'", "''")
            target = str(self.target).replace("'", "''")
            subprocess.run([POWERSHELL, '-NoProfile', '-NonInteractive', '-Command',
                            f"New-Item -ItemType Junction -Path '{target}' -Target '{source}' | Out-Null"],
                           check=True, capture_output=True)
        else:
            self.target.symlink_to(self.source, target_is_directory=True)
        self.install()
        self.assertTrue((self.source / '.mcp.json').is_file())
        self.assertTrue((self.target / '.mcp.json').is_file())
        self.assertEqual(self.git('-C', str(self.source), 'status', '--porcelain').stdout, '')


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
