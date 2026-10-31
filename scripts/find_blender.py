"""Prints the path of a Blender to run headless: python find_blender.py. Exit code 1 when none is found.

Looks at $BLENDER, then `blender` on the PATH, then a Blender that is running (installs outside the usual folders turn up here), then
the usual install folders, newest version first. Standard library only."""
import glob
import os
import re
import shutil
import subprocess
import sys


def running():
    """Paths of running Blenders."""
    if os.name == 'nt':
        command = ['powershell', '-NoProfile', '-Command', "Get-Process blender -ErrorAction SilentlyContinue | ForEach-Object Path"]
    else:
        command = ['ps', '-eo', 'args=']
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if os.name == 'nt':
        return lines
    return [line.split()[0] for line in lines if os.path.basename(line.split()[0]) in ('blender', 'Blender')]


def installed():
    """The usual install folders, newest version first."""
    home = os.path.expanduser('~')
    patterns = [os.path.join(os.environ.get(v, ''), 'Blender Foundation', '*', 'blender.exe') for v in ('ProgramFiles', 'ProgramFiles(x86)') if os.environ.get(v)]
    patterns += [os.path.join(os.environ.get('LOCALAPPDATA', home), 'Programs', 'Blender*', '**', 'blender.exe'),
                 '/Applications/Blender*.app/Contents/MacOS/Blender', os.path.join(home, 'Applications', 'Blender*.app', 'Contents', 'MacOS', 'Blender'),
                 '/usr/bin/blender', '/usr/local/bin/blender', '/snap/bin/blender', '/opt/blender*/blender', os.path.join(home, 'blender*', 'blender')]
    found = [path for pattern in patterns for path in glob.glob(pattern, recursive=True)]

    def version(path):
        return [int(n) for n in re.findall(r'\d+', path)] or [0]
    return sorted(found, key=version, reverse=True)


def find():
    for path in [os.environ.get('BLENDER'), shutil.which('blender'), *running(), *installed()]:
        if path and os.path.isfile(path):
            return path
    return None


if __name__ == '__main__':
    found = find()
    if not found:
        sys.exit('Blender not found: install it, start it once, or set BLENDER to its path')
    print(found)
