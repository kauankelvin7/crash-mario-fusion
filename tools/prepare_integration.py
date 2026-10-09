"""Prepare an instrumented private sm64ex build without modifying the M0 checkout."""
import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import tarfile
import tempfile

PIN = 'd7ca2c04364a6dd0dac58b47151e04e26887e6f0'
ROOT = pathlib.Path(__file__).resolve().parents[1]

def _prepare(source, output):
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Use separate, nonoverlapping source/output directories')
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != PIN:
        raise ValueError('sm64ex revision differs from M0 pin')
    if subprocess.check_output(['git', '-C', str(source), 'diff', 'HEAD', '--', 'src', 'Makefile']):
        raise ValueError('Source changes must be preserved; use the clean pinned checkout')
    marker = output / '.cm64-generated.json'
    created = not output.exists()
    if created:
        output.mkdir(parents=True)
        archive = subprocess.check_output(['git', '-C', str(source), 'archive', 'HEAD'])
        # Git archive contains source only, never ignored ROMs or generated data.
        with tarfile.open(fileobj=io.BytesIO(archive)) as files:
            files.extractall(output, filter='data')
        interaction = output / 'src/game/interaction.c'
        text = interaction.read_text()
        anchor = '#include "thread6.h"'
        if text.count(anchor) != 1:
            raise ValueError('Unrecognized include anchor')
        text = text.replace(anchor, anchor + '\n#include "../pc/cm64_coin.h"')
        begin = text.index('u32 interact_coin(struct MarioState *m,')
        end = text.index('u32 interact_water_ring(struct MarioState *m,', begin)
        block = text[begin:end]
        if block.count('    return FALSE;') != 1:
            raise ValueError('Unrecognized native coin hook')
        hook = ('    if (o->oDamageOrCoinValue == 1 && gCurrDemoInput == NULL)\n'
                '        cm64_coin(gGlobalTimer, m->numCoins, m->pos[0], m->pos[1], m->pos[2]);\n')
        text = text[:begin] + block.replace('    return FALSE;', hook + '    return FALSE;') + text[end:]
        interaction.write_text(text)
        makefile = output / 'Makefile'
        text = makefile.read_text()
        anchor = 'BACKEND_LDFLAGS :='
        if text.count(anchor) != 1:
            raise ValueError('Unrecognized linker anchor')
        text = text.replace(anchor, anchor + '\nifeq ($(WINDOWS_BUILD),1)\nBACKEND_LDFLAGS += -lws2_32\nendif')
        makefile.write_text(text)
        state = {'pin': PIN, 'hashes': {}}
    else:
        if not marker.is_file():
            raise ValueError('Refusing to overwrite an unrecognized existing directory')
        state = json.loads(marker.read_text())
        if state['pin'] != PIN:
            raise ValueError('Generated directory revision mismatch')
        for name, digest in state['hashes'].items():
            if hashlib.sha256((output/name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Preserve local edits before refreshing: {name}')
    for name in ['cm64_coin.c', 'cm64_coin.h']:
        (output/'src/pc'/name).write_bytes((ROOT/'integration/sm64'/name).read_bytes())
    names = ['src/game/interaction.c', 'Makefile', 'src/pc/cm64_coin.c', 'src/pc/cm64_coin.h']
    state['hashes'] = {name: hashlib.sha256((output/name).read_bytes()).hexdigest() for name in names}
    marker.write_text(json.dumps(state, indent=2)+'\n')
def prepare(source, output):
    source, output = source.resolve(), output.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('Use separate, nonoverlapping source/output directories')
    if output.exists():
        _prepare(source, output)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.cm64-prepare-', dir=output.parent) as scratch:
            staged = pathlib.Path(scratch)/'sm64ex'
            _prepare(source, staged)
            if output.exists():
                raise ValueError('Destination appeared during preparation; preserving it')
            staged.rename(output)
    print(f'Prepared native coin observer: {output}; real runtime NOT_TESTED')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=pathlib.Path)
    parser.add_argument('--output', required=True, type=pathlib.Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
