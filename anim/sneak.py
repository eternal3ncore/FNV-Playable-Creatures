"""Sneak (crouched) versions of a creature's own idle/locomotion: the same motion (root movement included)
with the knees bent, the root lowered so the feet keep their height, and the torso leaning forward."""
import numpy as np
from kf import KFEval
from rig import rotm

LAT = np.array([1.0, 0, 0])
CROUCH = dict(thigh=32, calf=-55, foot=22, lean=14, head=-8)

def _fk(sk, loc):
    W = {}
    for nm in sk.order:
        t, R = loc[nm]; p = sk.parent[nm]
        if p is None: W[nm] = (t.copy(), R.copy())
        else: pp, pR = W[p]; W[nm] = (pp + pR @ t, pR @ R)
    return W

def crouch_frames(cr, src_kf, timescale=1.0, fps=30, c=None):
    """returns frames, bones (with priorities), length, text keys (retimed), cycle"""
    c = dict(CROUCH, **(c or {}))
    sk = cr.sk; b = cr.cfg.BONES
    k = KFEval(cr.path(src_kf))
    L = k.stop / timescale; n = max(2, int(round(L * fps)) + 1)
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        smp = k.sample(t * timescale)
        loc = {}
        for nm in sk.order:
            tt, R, _ = sk.local[nm]
            if nm in smp:
                if smp[nm][0] is not None: tt = smp[nm][0]
                if smp[nm][1] is not None: R = smp[nm][1]
            loc[nm] = (np.array(tt, float), np.array(R, float))
        W0 = _fk(sk, loc)
        def wrot(nm, Rw):
            W = _fk(sk, loc); p = sk.parent[nm]
            loc[nm] = (loc[nm][0], W[p][1].T @ Rw @ W[nm][1])
        for side in ('L', 'R'):
            th, ca, ft = b['leg_' + side][:3]
            wrot(th, rotm(LAT, c['thigh'])); wrot(ca, rotm(LAT, c['calf'])); wrot(ft, rotm(LAT, c['foot']))
        sp = cr.spine[1:]
        for nm in sp: wrot(nm, rotm(LAT, -c['lean'] / max(1, len(sp))))
        wrot(cr.head, rotm(LAT, -c['head']))
        W1 = _fk(sk, loc)
        f0 = min(W0[b['leg_L'][2]][0][2], W0[b['leg_R'][2]][0][2])
        f1 = min(W1[b['leg_L'][2]][0][2], W1[b['leg_R'][2]][0][2])
        rt, rR = loc[b['root']]
        # the drop is along world z; express it in the root's parent frame
        pR = W1[sk.parent[b['root']]][1]
        loc[b['root']] = (rt - pR.T @ np.array([0, 0, f1 - f0]), rR)
        frames.append((t, loc))
    bones = [(nm, pr) for nm, _, pr in k.blocks]
    have = {nm for nm, _ in bones}
    base_pr = max([p for _, p in bones] or [30])
    for nm in [b['root'], b['pelvis']] + b['leg_L'] + b['leg_R'] + list(cr.spine) + [cr.head]:
        if nm not in have: bones.append((nm, base_pr))
    keys = [(min(t / timescale, L), s) for t, s in k.textkeys]
    return frames, bones, L, keys, k.cycle, k.name
