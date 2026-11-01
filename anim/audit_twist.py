"""Distortion audit for a playable-creature skeleton folder.
For each limb / spine bone and each sampled frame: local rotation relative to the creature's own idle pose (mtidle t=0),
split into TWIST (about the bone's own axis = direction to its main child: what wrings wrists / ankles / elbows) and
SWING (bend of that axis). The creature's OWN vanilla animations give the per-bone envelope (max twist / swing they ever
use); a generated file is flagged where a bone exceeds max(envelope + MARGIN, FLOOR).
usage: python3 audit_twist.py <race tag> <deployed folder> <own anim dir> [<own dir 2> ...]  -> json report on stdout"""
import sys, os, glob, json, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval, Skeleton, m2q
BONES = ['Bip01 L Clavicle', 'Bip01 R Clavicle', 'Bip01 L UpperArm', 'Bip01 R UpperArm', 'Bip01 L Forearm', 'Bip01 R Forearm',
         'Bip01 L Hand', 'Bip01 R Hand', 'Bip01 L Thigh', 'Bip01 R Thigh', 'Bip01 L Calf', 'Bip01 R Calf',
         'Bip01 L Foot', 'Bip01 R Foot', 'Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2', 'Bip01 Neck', 'Bip01 Head']
MARGIN = 20.0
HINGES = ('Bip01 L Forearm', 'Bip01 R Forearm', 'Bip01 L Calf', 'Bip01 R Calf')   # biped hinges: local Z only
OFFHINGE_LIM = 12.0
HINGE_MARGIN = 15.0
FLOOR = dict(twist=40.0, swing=70.0)
CHILD = {'Bip01 L Hand': 'Bip01 L Finger2', 'Bip01 R Hand': 'Bip01 R Finger2', 'Bip01 L Foot': 'Bip01 L Toe0',
         'Bip01 R Foot': 'Bip01 R Toe0', 'Bip01 L Clavicle': 'Bip01 L UpperArm', 'Bip01 R Clavicle': 'Bip01 R UpperArm',
         'Bip01 L UpperArm': 'Bip01 L Forearm', 'Bip01 R UpperArm': 'Bip01 R Forearm', 'Bip01 L Forearm': 'Bip01 L Hand',
         'Bip01 R Forearm': 'Bip01 R Hand', 'Bip01 L Thigh': 'Bip01 L Calf', 'Bip01 R Thigh': 'Bip01 R Calf',
         'Bip01 L Calf': 'Bip01 L Foot', 'Bip01 R Calf': 'Bip01 R Foot', 'Bip01 Spine': 'Bip01 Spine1',
         'Bip01 Spine1': 'Bip01 Spine2', 'Bip01 Spine2': 'Bip01 Neck', 'Bip01 Neck': 'Bip01 Head', 'Bip01 Head': None}

def axes(sk):
    ax = {}
    for b in BONES:
        if b not in sk.local: continue
        c = CHILD.get(b)
        if c not in sk.local:                       # fall back to the child with the longest offset
            kids = [n for n in sk.order if sk.parent.get(n) == b]
            c = max(kids, key=lambda n: np.linalg.norm(sk.local[n][0]), default=None)
        if c is None or np.linalg.norm(sk.local[c][0]) < 1e-3: ax[b] = np.array([1.0, 0, 0]); continue
        v = np.array(sk.local[c][0], float); ax[b] = v / np.linalg.norm(v)
    return ax

def swing_twist(Rrel, a):
    q = m2q(Rrel); w, v = q[0], np.array(q[1:])
    if w < 0: w, v = -w, -v
    p = np.dot(v, a)
    twist = np.degrees(2 * np.arctan2(abs(p), w))
    ang = np.degrees(2 * np.arctan2(np.linalg.norm(v), w))
    tw = np.radians(twist)
    # swing = total rotation with the twist removed
    qt = np.array([np.cos(tw / 2), *(np.sign(p) * np.sin(tw / 2) * a)])
    qs = _qmul(q if q[0] >= 0 else -q, _qconj(qt))
    swing = np.degrees(2 * np.arctan2(np.linalg.norm(qs[1:]), abs(qs[0])))
    return twist, swing

def _qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2])
def _qconj(q): return np.array([q[0], -q[1], -q[2], -q[3]])

def hinge_split(Rrel):
    """signed angle about local Z, and the residual (off-hinge) rotation angle"""
    phi = np.arctan2(Rrel[1, 0], Rrel[0, 0])
    c, s_ = np.cos(phi), np.sin(phi)
    Rz = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
    res = Rz.T @ Rrel
    off = np.degrees(np.arccos(np.clip((np.trace(res) - 1) / 2, -1, 1)))
    return np.degrees(phi), off

def measure(path, sk, R0, ax, nsamp=12):
    k = KFEval(path); L = k.stop
    keyed = {nm for nm, _, _ in k.blocks}
    out = {}
    for i in range(nsamp):
        t = L * i / max(1, nsamp - 1); s = k.sample(t)
        for b in BONES:
            if b not in keyed or b not in R0 or b not in s or s[b][1] is None: continue
            tw, sw = swing_twist(R0[b].T @ np.asarray(s[b][1], float), ax[b])
            if b in HINGES:
                phi, off = hinge_split(R0[b].T @ np.asarray(s[b][1], float))
                h = out.setdefault(b + '#h', [1e9, -1e9, 0, 0])
                h[0] = min(h[0], phi); h[1] = max(h[1], phi)
                if off > h[2]: h[2], h[3] = off, t
            o = out.setdefault(b, [0, 0, 0, 0]); 
            if tw > o[0]: o[0], o[1] = tw, t
            if sw > o[2]: o[2], o[3] = sw, t
    return out, L

def run(tag, folder, own_dirs):
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif')); ax = axes(sk)
    idle = KFEval(os.path.join(folder, 'mtidle.kf')).sample(0)
    R0 = {b: np.asarray(idle[b][1] if b in idle and idle[b][1] is not None else sk.local[b][1], float) for b in BONES if b in sk.local}
    env = {b: [0.0, 0.0] for b in R0}
    hen = {b: [1e9, -1e9] for b in HINGES if b in R0}
    own = [f for d in own_dirs for f in glob.glob(os.path.join(d, '**', '*.kf'), recursive=True)]
    for f in own:
        try: m, _ = measure(f, sk, R0, ax)
        except Exception: continue
        for b, v in m.items():
            if b.endswith('#h'): bb = b[:-2]; hen[bb][0] = min(hen[bb][0], v[0]); hen[bb][1] = max(hen[bb][1], v[1]); continue
            env[b][0] = max(env[b][0], v[0]); env[b][1] = max(env[b][1], v[2])
    lim = {b: (max(env[b][0] + MARGIN, FLOOR['twist']), max(env[b][1] + MARGIN, FLOOR['swing'])) for b in env}
    flags = []
    for f in sorted(glob.glob(os.path.join(folder, '**', '*.kf'), recursive=True)):
        rel = os.path.relpath(f, folder)
        try: m, L = measure(f, sk, R0, ax)
        except Exception as e: flags.append(dict(file=rel, error=str(e)[:80])); continue
        for b, v in m.items():
            if b.endswith('#h'):
                bb = b[:-2]; lo, hi = hen[bb]
                if v[2] > OFFHINGE_LIM: flags.append(dict(file=rel, bone=bb, kind='offhinge', deg=round(v[2]), lim=OFFHINGE_LIM, t=round(v[3], 2)))
                if v[0] < lo - HINGE_MARGIN or v[1] > hi + HINGE_MARGIN:
                    flags.append(dict(file=rel, bone=bb, kind='hingerange', deg=[round(v[0]), round(v[1])], lim=[round(lo), round(hi)]))
                continue
            tw, tt, sw, st = v
            if tw > lim[b][0]: flags.append(dict(file=rel, bone=b, kind='twist', deg=round(tw), lim=round(lim[b][0]), t=round(tt, 2)))
            if sw > lim[b][1]: flags.append(dict(file=rel, bone=b, kind='swing', deg=round(sw), lim=round(lim[b][1]), t=round(st, 2)))
    return dict(tag=tag, own_files=len(own), envelope={b: [round(x) for x in v] for b, v in env.items()},
                hinge_range={b: [round(x) for x in v] for b, v in hen.items()}, flags=flags)

if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1], sys.argv[2], sys.argv[3:])))
