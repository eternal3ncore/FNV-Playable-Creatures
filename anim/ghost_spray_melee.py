"""Ghost People gas spray on the melee power attacks: the one- and two-handed forward power attack and the AttackCustom1-5Power
that melee weapons play in its place (+ sneak) keep their lunge and get the spray from the mask - the skeleton's
PCGhostMaskSpray emitter switched on round the Hit (ON .. OFF, as ghost_spray.add_emitter) and the spray's hiss
(Sound: PCGhostGasSprayHiss) just before it. PlayableCreatures.dll (UnarmedEffectWeapons=1) casts the race's unarmed
effect on those hits too.
usage: python3 -P ghost_spray_melee.py <in folder> <out folder>     (files already carrying the emitter are skipped)"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from nifedit import NifFile
from ghost_spray import add_emitter, SPRAY_NODE, SPRAY_SOUND, BIRTH

LEAD, HOLD = 0.05, 0.32          # emitter on from Hit - LEAD to Hit + HOLD
FILES = re.compile(r'^(sneak)?(1hm|2hm)attack(forwardpower|custom[1-5]power)\.kf$')


def text_keys(f):
    ty = [f.types[b] for b in f.btype]; i = ty.index('NiTextKeyExtraData'); b = f.blocks[i]
    nm, n = struct.unpack_from('<iI', b, 0)
    return i, nm, [(struct.unpack_from('<f', b, 8 + 8 * k)[0], struct.unpack_from('<i', b, 12 + 8 * k)[0]) for k in range(n)]


def run(src, dst):
    os.makedirs(dst, exist_ok=True)
    for fn in sorted(os.listdir(src)):
        if not FILES.match(fn.lower()): continue
        f = NifFile(os.path.join(src, fn))
        if SPRAY_NODE in f.strings: print(fn, 'already sprays'); continue
        i, nm, keys = text_keys(f)
        hit = next(t for t, s in keys if f.strings[s] == 'Hit'); stop = max(t for t, _ in keys)
        keys.append((max(0.0, hit - 0.03), f.str_index(f'Sound: {SPRAY_SOUND}'))); keys.sort(key=lambda k: k[0])
        f.blocks[i] = struct.pack('<iI', nm, len(keys)) + b''.join(struct.pack('<fi', t, s) for t, s in keys)
        prio = max(struct.unpack_from('<B', f.blocks[[f.types[b] for b in f.btype].index('NiControllerSequence')], 12 + 29 * k + 8)[0]
                   for k in range(struct.unpack_from('<I', f.blocks[[f.types[b] for b in f.btype].index('NiControllerSequence')], 4)[0]))
        out = os.path.join(dst, fn); open(out, 'wb').write(f.to_bytes())
        add_emitter(out, SPRAY_NODE, [(0.0, 0), (max(0.0, hit - LEAD), 1), (hit + HOLD, 0), (stop, 0)], BIRTH, prio, headtrack=False)
        print(fn, f'Hit {hit:.2f}: spray {hit - LEAD:.2f}-{hit + HOLD:.2f}, priority {prio}')


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
