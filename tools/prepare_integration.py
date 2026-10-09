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

def _pose_hooks(output):
    """Pinned game-thread read seam; lifecycle hooks touch observer state only."""
    path = output/'src/game/level_update.c'
    text = path.read_text(encoding='utf-8')
    anchor = '#include "thread6.h"'
    if text.count(anchor) != 1:
        raise ValueError('Unrecognized pose include anchor')
    text = text.replace(anchor, anchor+'\n#include "../pc/cm64_pose.h"')
    anchor = 's32 update_level(void) {\n    s32 changeLevel;'
    if text.count(anchor) != 1:
        raise ValueError('Unrecognized update_level anchor')
    text = text.replace(anchor, anchor+'\n    s16 cm64_entry_mode = sCurrPlayMode;')
    begin, end = text.index('s32 update_level(void)'), text.index('s32 init_level(void)')
    block = text[begin:end]
    anchor = '    return changeLevel;'
    if block.count(anchor) != 1:
        raise ValueError('Unrecognized post-update anchor')
    hook = '''    /* Read only after native object/camera/warp update; never during pause/load. */
    if (cm64_entry_mode == PLAY_MODE_NORMAL && sCurrPlayMode == PLAY_MODE_NORMAL
        && !changeLevel && gCurrentArea != NULL && gMarioState != NULL
        && gMarioState->marioObj != NULL && gMarioState->area == gCurrentArea
        && gCurrDemoInput == NULL && gCurrCreditsEntry == NULL
        && !gWarpTransition.isActive && sDelayedWarpOp == WARP_OP_NONE
        && gTimeStopState == 0 && gMarioState->action != ACT_UNINITIALIZED) {
        cm64_pose(gGlobalTimer, gCurrLevelNum, gCurrentArea->index,
                  gMarioState->pos, gMarioState->faceAngle,
                  gMarioState->action, gMarioState->flags);
    } else {
        cm64_pose_invalidate();
    }
'''
    text = text[:begin]+block.replace(anchor,hook+anchor)+text[end:]
    text = text.replace('s32 init_level(void) {',
                        's32 init_level(void) {\n    cm64_pose_invalidate();')
    path.write_text(text, encoding='utf-8')
    path = output/'src/game/area.c'
    text = '#include "../pc/cm64_pose.h"\n'+path.read_text(encoding='utf-8')
    for name in ('clear_areas(void)', 'clear_area_graph_nodes(void)',
                 'load_area(s32 index)', 'unload_area(void)',
                 'load_mario_area(void)', 'unload_mario_area(void)', 'change_area(s32 index)'):
        anchor = 'void '+name+' {'
        if text.count(anchor) != 1:
            raise ValueError('Unrecognized area lifecycle anchor: '+name)
        text = text.replace(anchor, anchor+'\n    cm64_pose_invalidate();')
    path.write_text(text, encoding='utf-8')

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
        text = interaction.read_text(encoding='utf-8')
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
        interaction.write_text(text, encoding='utf-8')
        makefile = output / 'Makefile'
        text = makefile.read_text(encoding='utf-8')
        anchor = 'BACKEND_LDFLAGS :='
        if text.count(anchor) != 1:
            raise ValueError('Unrecognized linker anchor')
        text = text.replace(anchor, anchor + '\nifeq ($(WINDOWS_BUILD),1)\nBACKEND_LDFLAGS += -lws2_32\nendif')
        makefile.write_text(text, encoding='utf-8')
        state = {'pin': PIN, 'hashes': {}}
    else:
        if not marker.is_file():
            raise ValueError('Refusing to overwrite an unrecognized existing directory')
        state = json.loads(marker.read_text(encoding='utf-8'))
        if state['pin'] != PIN:
            raise ValueError('Generated directory revision mismatch')
        for name, digest in state['hashes'].items():
            if hashlib.sha256((output/name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'Preserve local edits before refreshing: {name}')
    if state.get('pose_hooks') != 1:
        if not created:
            for name in ('src/game/level_update.c', 'src/game/area.c'):
                original = subprocess.check_output(['git', '-C', str(source), 'show', f'HEAD:{name}'])
                if (output/name).read_text(encoding='utf-8') != original.decode().replace('\r\n', '\n'):
                    raise ValueError(f'Preserve local edits before adding pose hook: {name}')
        _pose_hooks(output)
        state['pose_hooks'] = 1
    for name in ['cm64_coin.c', 'cm64_coin.h', 'cm64_pose.c', 'cm64_pose.h']:
        (output/'src/pc'/name).write_bytes((ROOT/'integration/sm64'/name).read_bytes())
    names = ['src/game/interaction.c', 'Makefile', 'src/pc/cm64_coin.c', 'src/pc/cm64_coin.h',
             'src/game/level_update.c', 'src/game/area.c', 'src/pc/cm64_pose.c', 'src/pc/cm64_pose.h']
    state['hashes'] = {name: hashlib.sha256((output/name).read_bytes()).hexdigest() for name in names}
    marker.write_text(json.dumps(state, indent=2)+'\n', encoding='utf-8')
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
