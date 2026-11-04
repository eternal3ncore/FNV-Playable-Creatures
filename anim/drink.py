"""ActWaterSource.kf for the creatures with hands (drinking from a water source): a slight forward bend over the
trunk-to-head chain (BEND deg, eased in to the human file's StartLoop, out after EndLoop) on the creature's own idle,
and the left hand on the human drinking file's path relative to the mouth (hand_xfer: it scoops water up to the mouth
twice, on the human file's two 'Sound: NPCHumanDrinkingHand' keys). The human file's name, length, cycle and keys.
Ghost: the human file itself (its skeleton is the human one). Robots keep act_idles.py's bend.
usage: python3 drink.py <folder name> <race folder with mtidle.kf + Skeleton.nif> <out IdleAnims dir>"""
import os, shutil, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KF, KFEval, Skeleton
import rig
from act_idles import Shim, wrot, rotx, chain_of, REF, ease
from hand_xfer import HandXfer, MOUTH, HUMAN_SKEL, HUMAN_STAND, local_pose, fk

HUMAN_DRINK = os.path.join(REF, 'actwatersource.kf')
# the head goes to the cupped hand on each sip (deg over neck + head; yaw + = left, pitch + = down), for arms that cannot
# reach their own mouth: the Zetan's (25) is 31 from its face, so its palm stops under its chin with the long fingers
# curled up across to the right cheek; it turns right 15 and tilts back 10 onto them (scanned against its head mesh:
# no finger inside the head on any frame; straight ahead 3 frames, turned left to the hand 13)
HEAD_TO_HAND = {'Zetan': (-15.0, -10.0)}
BEND = {'Trog': 8.0, 'Tunneler': 8.0, 'Deathclaw': 10.0, 'Mirelurk': 8.0, 'Lakelurk': 10.0}     # default 12
PRIO = 45


def rotz(a):
    c, s_ = np.cos(a), np.sin(a); return np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])


def sip_weight(ev, n, L):
    """0..1 per frame: the human's palm within 6 (sipping) .. 18 (away) of its mouth, smoothed over +-3 frames"""
    gs = Skeleton(HUMAN_SKEL); B = fk(gs, local_pose(gs, KFEval(HUMAN_STAND[0]).sample(HUMAN_STAND[1])))
    mg = B['Bip01 Head'][1].T @ np.array(MOUTH['human'], float); pg = 0.6 * np.array(gs.local['Bip01 L Finger2'][0], float)
    w = []
    for i in range(n):
        W = fk(gs, local_pose(gs, ev.sample(L * i / (n - 1))))
        d = np.linalg.norm(W['Bip01 L Hand'][0] + W['Bip01 L Hand'][1] @ pg - W['Bip01 Head'][0] - W['Bip01 Head'][1] @ mg)
        w.append(1 - ease((d - 6) / 12))
    k = np.exp(-0.5 * (np.arange(-3, 4) / 1.5) ** 2); k /= k.sum()
    return np.convolve(np.pad(w, 3, mode='edge'), k, mode='valid')


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
    yaw, pitch = (np.radians(x) for x in HEAD_TO_HAND.get(name, (0.0, 0.0)))
    neck = [x for x in ('Bip01 Neck', 'Bip01 Neck1', 'Bip01 Head') if x in sk.local]
    sip = sip_weight(ev, n, L) if yaw or pitch else np.zeros(n)
    frames = []
    for i in range(n):
        t = L * i / (n - 1); loc = local_pose(sk, idle.sample(t % idle.stop))
        bend = ease(t / a) * (1 - ease((t - (L - 0.9)) / 0.8))
        for nm in ch:
            pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
            loc[nm] = (loc[nm][0], pR.T @ rotx(-deg * bend / len(ch)) @ R)
        if sip[i] > 0:
            for nm in neck:
                pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
                loc[nm] = (loc[nm][0], pR.T @ rotz(yaw * sip[i] / len(neck)) @ rotx(-pitch * sip[i] / len(neck)) @ R)
        w = ease(t / 0.3) * (1 - ease((t - (L - 0.5)) / 0.45))
        hx.apply(loc, ev, t, w)
        frames.append((t, loc))
    keyed = [bb[0] for bb in idle.blocks if bb[0] != 'Bip01' and bb[0] in sk.local] + ch + (neck if yaw or pitch else []) + list(hx.arm['L']) + hx.fingers['L']
    rig.write_kf(cr, out, h.name, L, list(h.textkeys), frames, bones=[(x, PRIO) for x in dict.fromkeys(keyed) if x in sk.local], cycle=h.cycle)
    return 'bend + scooping hand'


if __name__ == '__main__':
    print(sys.argv[1], build(*sys.argv[1:4]))
