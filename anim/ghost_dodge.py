"""Ghost People back dodge: the Ghost is swallowed by a thick cloud of its gas, shrinks out of sight, is carried back
unseen and re-forms. A special idle (IDLE PCGhostDodgeBack, played by Core on back + jump with a weapon out, as the hops):
  * root motion: Bip01 translation keyed straight back (actor -Y) DIST over SLIP_ON..SLIP_OFF, as Dead Money's own hops key
    their sideways move (combatidle_hopleft.kf: Bip01 x 0 -> -159, rotation identity) - the hops move the player this
    way; the idle is played as they are (their IDLE settings, no movement hold). The player is moved no faster than its
    own movement speed (the hops: ~4 ft running, less walking), so the dodge's spell raises SpeedMult for 1 s (LENGTH)
  * the body: Bip01 NonAccum - the parent of every bone, so the skinned body, the head gear and the weapon in the hand -
    scaled 1 -> SMALL over SHRINK and back to 1 over GROW (scale keys on its NiTransformData; Bip01 and the camera,
    which hang above it, are not touched)
  * the cloud: the skeleton's PCGhostDodgeCloud (build_skel_ghost.py, on Scene Root, particles in the actor's space, off at rest)
    switched on CLOUD_ON..CLOUD_OFF at BIRTH / s - from the first frame, the body shrinking only once the fog has
    gathered round it ("lost in the fog"); its particles are in the actor's space, so the cloud travels with the Ghost,
    and short-lived, so it thins away as the body re-forms (controlled blocks NiPSysEmitterCtlr EmitterActive / BirthRate, as the
    mask spray); its puffs stay where they were let out, so the cloud hangs along the path and thins after the Ghost is back
  * the pose: the Ghost's standing frame of Dead Money's hop (its first frame), every bone at the hop's priority 58
  * text keys: start, the gas hiss (SOUND_AT, just after the start), the ghosts' hop sound (as the hop keys it), end
usage: python3 -P ghost_dodge.py <hop kf (Dead Money combatidle_hopleft.kf)> <out PCGhostDodgeBack.kf>"""
import os, sys, struct, importlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval
from rig import Creature, write_kf, smooth
from nifedit import NifFile
from ghost_spray import add_emitter

LENGTH = 1.00                            # = the dodge spell's speed boost (1 s, its shortest)
DIST = 360.0                             # units straight back (~16 ft)
SLIP_ON, SLIP_OFF = 0.10, 0.85           # root motion, while the body is (nearly) gone
SHRINK = (0.075, 0.19)                   # body 1 -> SMALL, once the fog has gathered
GROW = (0.85, 0.94)                      # body SMALL -> 1
SMALL = 0.001
CLOUD_ON, CLOUD_OFF = 0.0, 0.88          # emitter on from the first frame, off as the body re-forms
BIRTH = 980.0                            # puffs / s while on (user: 40% more fog than 700)
PRIO = 58                                # Dead Money's hop
SEQ = 'SpecialIdle_PCDodgeBack'
NODE = 'PCGhostDodgeCloud'
SOUND = 'PCGhostGasSprayHiss'
SOUND_AT = 0.03
HOP_SOUND, HOP_SOUND_AT = 'NPCGhostJumpSfx', 0.067   # Dead Money's hop sound, at the hop's own time

cfg = importlib.import_module('creatures.ghost'); cr = Creature(cfg); sk = cr.sk


def scale_at(t):
    return 1.0 - (1.0 - SMALL) * (smooth((t - SHRINK[0]) / (SHRINK[1] - SHRINK[0])) - smooth((t - GROW[0]) / (GROW[1] - GROW[0])))


def set_scale_keys(path, node, keys):
    """linear scale keys on node's NiTransformData (its NiTransformInterpolator gets one if it has none)"""
    f = NifFile(path); si = f.str_index
    seq = next(i for i, b in enumerate(f.btype) if f.types[b] == 'NiControllerSequence')
    sb = f.blocks[seq]; ncb = struct.unpack_from('<I', sb, 4)[0]
    for j in range(ncb):
        ii, _, _, nm = struct.unpack_from('<iiBi', sb, 12 + 29 * j)
        if f.strings[nm] != node: continue
        ib = bytearray(f.blocks[ii]); data = struct.unpack_from('<i', ib, 32)[0]
        sc = struct.pack('<II', len(keys), 1) + b''.join(struct.pack('<ff', t, v) for t, v in keys)
        if data < 0:
            data = f.add_block('NiTransformData', struct.pack('<II', 0, 0) + sc)
            struct.pack_into('<i', ib, 32, data); f.blocks[ii] = bytes(ib)
        else:                                       # rotation / translation groups as written, then the scale group
            d = f.blocks[data]; o = 0
            nr = struct.unpack_from('<I', d, o)[0]; o += 4
            if nr: rt = struct.unpack_from('<I', d, o)[0]; o += 4 + nr * (20 if rt != 4 else 0)
            nt = struct.unpack_from('<I', d, o)[0]; o += 4
            if nt: o += 4 + nt * 16
            assert d[o:] == struct.pack('<I', 0), 'unexpected scale group'
            f.blocks[data] = d[:o] + sc
        struct.pack_into('<f', ib, 28, keys[0][1]); f.blocks[ii] = bytes(ib)
        open(path, 'wb').write(f.to_bytes()); return
    raise KeyError(node)


def build(hop, out):
    h = KFEval(hop)
    s0 = h.sample(0.0)
    base = {}
    for nm in sk.order:
        t, R, _ = sk.local[nm]
        if nm in s0:
            if s0[nm][0] is not None: t = s0[nm][0]
            if s0[nm][1] is not None: R = s0[nm][1]
        base[nm] = (np.array(t, float), np.array(R, float))
    n = int(round(LENGTH * 30)) + 1; frames = []
    for i in range(n):
        t = LENGTH * i / (n - 1); loc = dict(base)
        loc['Bip01'] = (np.array([0.0, -DIST * smooth((t - SLIP_ON) / (SLIP_OFF - SLIP_ON)), 0.0]), np.eye(3))
        frames.append((t, loc))
    bones = [(b[0], PRIO) for b in h.blocks if b[0] in sk.local]
    if not any(nm == 'Bip01 NonAccum' for nm, _ in bones): bones.insert(1, ('Bip01 NonAccum', PRIO))
    # the hiss just after the start: a Sound key at 0.0 (on the start key) played nothing in game
    keys = [(0.0, 'start'), (SOUND_AT, f'Sound: {SOUND}'), (HOP_SOUND_AT, f'Sound: {HOP_SOUND}'), (LENGTH, 'end')]
    write_kf(cr, out, SEQ, LENGTH, keys, frames, bones=bones, cycle=2)
    ts = sorted({0.0, LENGTH} | {round(x, 4) for x in np.arange(SHRINK[0], SHRINK[1] + 1e-6, 1 / 30)} |
                {round(x, 4) for x in np.arange(GROW[0], GROW[1] + 1e-6, 1 / 30)} | {SHRINK[1], GROW[0], GROW[1]})
    set_scale_keys(out, 'Bip01 NonAccum', [(t, scale_at(t)) for t in ts])
    add_emitter(out, NODE, [(CLOUD_ON, 1), (CLOUD_OFF, 0), (LENGTH, 0)], BIRTH, PRIO, headtrack=False)
    return len(frames), len(bones)


if __name__ == '__main__':
    print(build(sys.argv[1], sys.argv[2]))
