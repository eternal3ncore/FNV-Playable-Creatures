"""own_block.py (block animations for H2H and melee; 1HM / 2HM shared) for the races with no human
arms to transfer onto (robots, Eyebot, Securitron, Trog / Tunneler): the race's own unarmed guard is its block.
  <p>blockidle = (sneak)h2haim with the sequence renamed BlockIdle (its own loop, length, keys);
  <p>blockhit  = the h2haim pose at t=0 held for the human BlockHit length (0.73 s, clamp, 'Blend: 1'), with a recoil
                 on Bip01 NonAccum: pitched back RECOIL deg about the world lateral axis at 0.1 s, eased out by 0.5 s;
  for every prefix in TYPES (h2h, mt + the melee types the race can hold); standing from h2haim, sneak from sneakh2haim
  (the Eyebot's sneak hover is lower). With --keep-1hm the race's existing 1hmblock* (Mister Handy / Gutsy claw sets) are
  the source instead and copied to the other prefixes.
usage: python3 -P own_block.py <folder> <out dir> <types e.g. h2h,mt,1hm,2hm> [--keep-1hm]"""
import os, sys, shutil, struct
sys.path.append(os.path.dirname(os.path.abspath(__file__))); sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from holster_fix import KFFile
from kf import KFEval, Skeleton
from robotlib import set_meta
RECOIL, HIT_LEN = 6.0, 0.7333
HIT_KEYS = [(0.0, 'start'), (0.0333, 'Blend: 1'), (HIT_LEN, 'end')]

def rot_x(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def block_idle(src, dst):
    shutil.copyfile(src, dst); kf = KFFile(dst); set_meta(kf, seq='BlockIdle'); kf.save(dst)

def block_hit(src, dst, skel):
    shutil.copyfile(src, dst); kf = KFFile(dst); k = KFEval(src); s0 = k.sample(k.start)
    sk = Skeleton(skel); par = sk.parent.get('Bip01 NonAccum')
    P = np.eye(3); nd = par                                   # world rotation of NonAccum's parent chain at t=0
    while nd is not None and nd in sk.local:
        R = s0[nd][1] if nd in s0 and s0[nd][1] is not None else sk.local[nd][1]
        P = np.array(R, float) @ P; nd = sk.parent.get(nd)
    ts = [HIT_LEN * j / 22 for j in range(23)]
    for _, nm in kf.cb:
        if nm is None or nm not in s0 or s0[nm][0] is None or s0[nm][1] is None: continue
        t0, R0 = np.array(s0[nm][0], float), np.array(s0[nm][1], float)
        if nm == 'Bip01 NonAccum':
            keys = []
            for t in ts:
                w = t / 0.1 if t < 0.1 else max(0.0, 1 - (t - 0.1) / 0.4)
                w = w * w * (3 - 2 * w)
                keys.append((t, t0, P.T @ rot_x(-RECOIL * w) @ P @ R0))
            kf.set_channel(nm, keys)
        else:
            kf.set_channel(nm, [(0.0, t0, R0)])
    set_meta(kf, seq='BlockHit', length=HIT_LEN, cycle=2, textkeys=HIT_KEYS); kf.save(dst)

if __name__ == '__main__':
    d, out, types = sys.argv[1], sys.argv[2], sys.argv[3].split(','); keep = '--keep-1hm' in sys.argv
    os.makedirs(out, exist_ok=True)
    skel = os.path.join(d, 'Skeleton.nif'); n = 0
    for sn in ('', 'sneak'):
        if keep:
            src_i, src_h = os.path.join(d, sn + '1hmblockidle.kf'), os.path.join(d, sn + '1hmblockhit.kf')
        else:
            aim = os.path.join(d, sn + 'h2haim.kf')
            src_i, src_h = os.path.join(out, sn + '_bi.kf'), os.path.join(out, sn + '_bh.kf')
            block_idle(aim, src_i); block_hit(aim, src_h, skel)
        for T in types:
            if keep and T == '1hm': continue
            shutil.copyfile(src_i, os.path.join(out, sn + T + 'blockidle.kf'))
            shutil.copyfile(src_h, os.path.join(out, sn + T + 'blockhit.kf')); n += 2
        if not keep: os.remove(src_i); os.remove(src_h)
    print(n, 'block files ->', out)
