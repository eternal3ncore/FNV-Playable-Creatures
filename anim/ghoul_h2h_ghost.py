"""Feral ghoul unarmed attacks for Ghost People, retargeted onto the Ghost's skeleton.
The vanilla feral ghoul's H2H attack files (Fallout - Meshes.bsa, meshes\\creatures\\ghoul\\) keyed straight onto the
Ghost skeleton twist the body out of shape on every swing: the two rigs' bones have different bind orientations (roll),
so the same local rotations point the limbs elsewhere. Here each frame goes through retarget.Retarget (the method the
Ghost's own run was built with from the ghoul's): world-space delta from the ghoul's bind pose applied to the Ghost's
bind pose (W_ghost = W_ghoul_anim * W_ghoul_bind^T * W_ghost_bind), translations the Ghost's own bone lengths, the root
scaled by the leg-length ratio, feet placed by two-bone leg IK where the scaled ghoul feet are.
Files (standing; sneak versions by sneak_fix afterwards):
  h2hattackleft / right [up / down]  _a <- the ghoul's plain file, _b <- _b, _c <- _c
  h2hattackleftpower / rightpower    <- the ghoul's side power attacks
  h2hrecoil                          <- the ghoul's Recoil
The Ghost's own moves stay: forward power (Dead Money lunge) + Custom1, back power (gas spray) + Custom2, the standing
power attack and Attack8 (Dead Money's), aims, blocks, equips.
Keyed bones = the ghoul file's keyed bones (each at its priority there; the leg / root channels too). Text keys: start,
Hit, a:L / a:R and end from the ghoul file; its creature enum keys become the Ghost's sounds - the attack vocal at 0,
the arm swing just before Hit, footstep enums (Left / Right / BackLeft / BackRight) the ghosts' footsteps.
usage: python3 -P ghoul_h2h_ghost.py <out folder>"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
import importlib
from kf import KFEval, KF
from rig import Creature, write_kf
from retarget import Retarget, GHOST_SKEL, LEGS, THUMBS

GHOUL = '/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/ghoul/'
GHOUL_SKEL = '/home/claude/fnv/ghoul_src/meshes/creatures/ghoul/skeleton.nif'
SWING_LEAD = 0.13            # arm swing sound before Hit (as the Ghost's own h2h files: 0.333 / Hit 0.467)
FOOT = {'Left': 'Sound: NPCGhostFootLeft', 'BackLeft': 'Sound: NPCGhostFootLeft',
        'Right': 'Sound: NPCGhostFootRight', 'BackRight': 'Sound: NPCGhostFootRight'}


def jobs():
    out = []
    for side in ('left', 'right'):
        for v in ('', 'up', 'down'):
            for ab, suf in (('a', ''), ('b', '_b'), ('c', '_c')):
                out.append((f'h2hattack{side}{v}_{ab}.kf', f'h2hattack{side}{v}{suf}.kf'))
        out.append((f'h2hattack{side}power.kf', f'h2hattack{side}power.kf'))
    out.append(('h2hrecoil.kf', 'h2hrecoil.kf'))
    return out


def text_keys(k):
    hit = next((t for t, s in k.textkeys if s == 'Hit'), None)
    keys = []
    for t, s in k.textkeys:
        s = s.strip()
        if s.startswith('Enum:'):
            e = s[5:].strip()
            if e in FOOT: keys.append((t, FOOT[e]))
            continue
        if s.startswith('Sound:'): continue
        keys.append((t, s))
    if hit is not None:
        keys += [(0.0, 'Sound: PCGhostAttackVox'), (max(0.0, hit - SWING_LEAD), 'Sound: WPNArmSwing')]
    return sorted(keys, key=lambda x: (x[0], x[1] != 'start', x[1] == 'end'))


class _Rooted:
    """a KF sampler that supplies the accum root where the file doesn't key it (most ghoul attacks): the ghoul's aim keys
    Bip01 on the ground (translation 0), as every in-game root is - so the leg IK measures the feet from the ground"""
    def __init__(s, k, root): s.k = k; s.root = root; s.stop = k.stop; s.blocks = k.blocks
    def sample(s, t):
        smp = dict(s.k.sample(t))
        if 'Bip01' not in smp or smp['Bip01'][0] is None: smp['Bip01'] = s.root
        return smp


def build(out_dir, fps=30):
    cfg = importlib.import_module('creatures.ghost'); cr = Creature(cfg)
    rt = Retarget(GHOUL_SKEL, GHOST_SKEL, LEGS, THUMBS, skip=('Bip01 Head2', 'Bip01 Footsteps'))
    rt.clean_root = True
    inv = {}
    for dst, src in rt.map.items(): inv.setdefault(src, []).append(dst)
    r0 = KFEval(os.path.join(GHOUL, 'h2haim.kf')).sample(0)['Bip01']; root = (r0[0], r0[1])
    os.makedirs(out_dir, exist_ok=True); made = []
    for out, src in jobs():
        p = os.path.join(GHOUL, src)
        if not os.path.exists(p): print('no ghoul file', src); continue
        k = KFEval(p); kk = KF(p); L = k.stop; n = int(round(L * fps)) + 1; cyc = getattr(k, 'cycle', 2)
        k = _Rooted(k, root)
        prio = {}
        for b in k.blocks:
            for d in inv.get(b[0], []): prio[d] = b[2]
            if b[0] in rt.ROOTS: prio[b[0]] = b[2]
        frames = []
        for i in range(n):
            t = L * i / (n - 1); loc, _ = rt.frame(k, t); frames.append((t, loc))
        bones = [(nm, prio[nm]) for nm in rt.hs.order if nm in prio]
        write_kf(cr, os.path.join(out_dir, out), kk.name, L, text_keys(kk), frames, bones=bones, cycle=cyc)
        made.append((out, kk.name, round(L, 3), len(bones)))
    return rt, made


if __name__ == '__main__':
    rt, made = build(sys.argv[1])
    print('leg ratio %.3f' % rt.ratio)
    for m in made: print(m)
