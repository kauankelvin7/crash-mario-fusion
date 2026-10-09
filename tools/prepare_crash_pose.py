"""Prepare a separate private launcher from tracked public source only; no game launch."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

PIN = '224da7757920a817de2d9242416f657ab95782ea'
ROOT = Path(__file__).resolve().parents[1]


def private_root():
    root = (Path(os.environ['LOCALAPPDATA'])/'CrashMarioFusion'/'M3-crash-pose').resolve()
    if root == ROOT or ROOT in root.parents:
        raise ValueError('Private build must stay outside Git')
    return root


def prepare():
    source = Path(os.environ['LOCALAPPDATA'])/'CrashMarioFusion/M0/CrashBandicoot-Launcher'
    def git(*args):
        return subprocess.check_output(['git', '-C', str(source), *args])
    if git('rev-parse', 'HEAD').decode().strip() != PIN or git('status', '--porcelain').strip():
        raise ValueError('Expected clean pinned public-source checkout')
    root = private_root()
    # Only resume a recognized, unfinished generated build. Never replace user content.
    if root.exists():
        pin = root/'source-pin.txt'
        project = root/'source/CrashBandicoot.Launcher/CrashBandicoot.Launcher.csproj'
        if (not pin.is_file() or pin.read_text(encoding='ascii').strip() != PIN
                or not project.is_file() or (root/'observer-build.json').exists()):
            raise ValueError('Existing private directory is unknown or already sealed; preserve it')
        print(f'Resuming recognized, unfinished private source: {root}')
        return
    root.mkdir(parents=True, exist_ok=False)
    archive = zipfile.ZipFile(io.BytesIO(git('archive', '--format=zip', PIN)))
    destination = root/'source'
    for entry in archive.infolist():
        path = (destination/entry.filename).resolve()
        if destination not in path.parents:
            raise ValueError('Unsafe source archive entry')
    archive.extractall(destination)
    (root/'source-pin.txt').write_text(PIN+'\n', encoding='ascii')
    print(f'Prepared tracked public sources only: {destination}')


def seal():
    root = private_root()
    if (root/'source-pin.txt').read_text().strip() != PIN:
        raise ValueError('Unknown private build')
    app = root/'app'
    mod = app/'mods/cm64-crash-pose'
    mod.mkdir(parents=True, exist_ok=False)
    for name in ('CrashPoseMod.cs', 'mod.json'):
        (mod/name).write_bytes((ROOT/'integration/crash_pose'/name).read_bytes())
    (app/'settings.json').write_text(json.dumps(dict(ModsConfigured=True, ActiveMods=['cm64-crash-pose'])), encoding='utf-8')
    files = ['CrashBandicoot.exe', 'CrashBandicoot.dll', 'RecompOne.Runtime.dll',
             'mods/cm64-crash-pose/CrashPoseMod.cs', 'mods/cm64-crash-pose/mod.json']
    hashes = {name: hashlib.sha256((app/name).read_bytes()).hexdigest() for name in files}
    (root/'observer-build.json').write_text(json.dumps(dict(pin=PIN, hashes=hashes), indent=2)+'\n', encoding='utf-8')
    print('Sealed isolated diagnostic launcher; gameplay NOT_TESTED')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    seal() if parser.parse_args().seal else prepare()
