"""Install only our authored source mod; preserve existing mods/settings with backups."""
import argparse
import hashlib
import json
import pathlib
import shutil
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]

def install(app_root):
    app_root = app_root.resolve()
    if not app_root.is_dir():
        raise ValueError('Build the native Crash launcher first')
    destination = app_root/'mods/cm64-coin-jump'
    state_path = destination/'.cm64-install.json'
    if destination.exists():
        if not state_path.is_file():
            raise ValueError('Preserve existing unrecognized mod directory')
        for name, digest in json.loads(state_path.read_text()).items():
            if hashlib.sha256((destination/name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Preserve edited mod: {name}')
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ['CoinJumpMod.cs', 'mod.json']:
        data = (ROOT/'integration/crash'/name).read_bytes()
        (destination/name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    state_path.write_text(json.dumps(hashes, indent=2)+'\n')
    settings = app_root/'settings.json'
    state = json.loads(settings.read_text(encoding='utf-8-sig')) if settings.exists() else {}
    active = state.get('ActiveMods', []) or []
    if not isinstance(active, list):
        raise ValueError('Unexpected ActiveMods format; preserve settings')
    if 'cm64-coin-jump' not in active or not state.get('ModsConfigured'):
        if settings.exists():
            shutil.copy2(settings, app_root/f'settings.before-cm64-{time.time_ns()}.json')
        # Configured=false means no mod was active: do not enable unrelated saved ids.
        state['ActiveMods'] = list(active) if state.get('ModsConfigured') else []
        if 'cm64-coin-jump' not in state['ActiveMods']:
            state['ActiveMods'].append('cm64-coin-jump')
        state['ModsConfigured'] = True
        temp = app_root/f'.cm64-settings-{time.time_ns()}.json'
        temp.write_text(json.dumps(state, indent=2)+'\n')
        temp.replace(settings)
    print(f'Installed source mod: {destination}; gameplay NOT_TESTED')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', required=True, type=pathlib.Path)
    install(parser.parse_args().app_root)
