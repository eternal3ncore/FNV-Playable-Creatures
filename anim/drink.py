"""ActWaterSource.kf for the creatures with hands (drinking from a water source): a slight forward bend over the
trunk-to-head chain (BEND deg, eased in to the human file's StartLoop, out after EndLoop) on the creature's own idle,
and the left hand on the human drinking file's path relative to the mouth (hand_xfer: it scoops water up to the mouth
twice, on the human file's two 'Sound: NPCHumanDrinkingHand' keys). The human file's name, length, cycle and keys.
Ghost: the human file itself (its skeleton is the human one). Robots keep act_idles.py's bend.
usage: python3 drink.py <folder name> <race folder with mtidle.kf + Skeleton.nif> <out IdleAnims dir>"""
import os, shutil, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KF, KFEval
import rig
from act_idles import Shim, wrot, rotx, chain_of, REF, ease
from hand_xfer import HandXfer, MOUTH, HUMAN_SKEL, HUMAN_STAND, local_pose

HUMAN_DRINK = os.path.join(REF, 'actwatersource.kf')
BEND = {'Trog': 8.0, 'Tunneler': 8.0, 'Deathclaw': 10.0, 'Mirelurk': 8.0, 'Lakelurk': 10.0}     # default 12
PRIO = 45


def build(name, folder, out_dir):
    os.makedirs(out_dir, exist_ok=True); out = os.path.join(out_dir, 'ActWaterSource.kf')
    if name == 'Ghost': shutil.copyfile(HUMAN_DRINK, out); return 'human copy'
    if name not in MOUTH: return 'kept (no hands)'
    skel = os.path.join(folder, 'Skeleton.nif')
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    idle = KFEval(os.path.join(folder, 'mtidle.kf'))
    h = KF(HUMAN_DRINK); ev = KFEval(HUMAN_DRINK); L = h.stop; n = int(round(L * 30)) + 1
    keys = {v.split(':')[0].strip().lower(): t for t, v in h.textkeys}
    a, b = keys.get('startloop', 0.37), keys.get('endloop', 1.37)
    hx = HandXfer(HUMAN_SKEL, MOUTH['human'], skel, name, local_pose(sk, idle.sample(0.0)), HUMAN_DRINK, sides=('L',), src_ref=HUMAN_STAND)
    ch = chain_of(sk); deg = np.radians(BEND.get(name, 12.0))
    frames = []
    for i in range(n):
        t = L * i / (n - 1); loc = local_pose(sk, idle.sample(t % idle.stop))
        bend = ease(t / a) * (1 - ease((t - (L - 0.9)) / 0.8))
        for nm in ch:
            pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
            loc[nm] = (loc[nm][0], pR.T @ rotx(-deg * bend / len(ch)) @ R)
        w = ease(t / 0.3) * (1 - ease((t - (L - 0.5)) / 0.45))
        hx.apply(loc, ev, t, w)
        frames.append((t, loc))
    keyed = [bb[0] for bb in idle.blocks if bb[0] != 'Bip01' and bb[0] in sk.local] + ch + list(hx.arm['L']) + hx.fingers['L']
    rig.write_kf(cr, out, h.name, L, list(h.textkeys), frames, bones=[(x, PRIO) for x in dict.fromkeys(keyed) if x in sk.local], cycle=h.cycle)
    return 'bend + scooping hand'


if __name__ == '__main__':
    print(sys.argv[1], build(*sys.argv[1:4]))
