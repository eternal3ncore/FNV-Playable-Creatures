"""Ghost People: the feral ghoul H2H attacks (ghoul_h2h_ghost.py) keep the head level, looking where the Ghost's own aim
looks. Retargeted from the hunched ghoul, whose head is raised against its spine to look ahead, the Ghost's head came
out raised or dipped through the swings (user, 11-05: "make the ghost look up, they should continue to look straight").
For every rotation key of Bip01 Head (linear, one per frame) only the
head's up / down tilt is corrected: C = the smallest rotation (about a level axis) that takes the face direction to the
same heading at the pitch of the matching Ghost aim (h2haim / h2haimup / h2haimdown, sneak: sneakh2haim*; about -1 deg).
The heading still follows the body's turn through the swing, the roll is kept. C goes on Bip01 Head alone: the Ghost's
clavicles (so both arms) hang from Bip01 Neck, so the neck keys are left as they are and the punches don't move.
Bip01 Neck1 (not keyed by these files) is taken from that aim, as it plays underneath in game. Keys are rewritten in
place (same count / times); every other channel is untouched.
usage: python3 -P ghost_head_level.py <folder with the files + the six aims> <out folder> [files...]"""
import os, sys, re, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
import importlib
from rig import Creature
from kf import KFEval, q2m, m2q
from nifedit import NifFile

cr = Creature(importlib.import_module('creatures.ghost')); sk = cr.sk
PAT = re.compile(r'^(sneak)?h2h(attack(left|right)(up|down)?(_[abc]|power)|recoil)\.kf$')


def fk(smp, extra=None):
    W = {}
    for nm in sk.order:
        tt, Rm, _ = sk.local[nm]
        src = smp.get(nm) or (extra or {}).get(nm)
        if src:
            if src[0] is not None: tt = src[0]
            if src[1] is not None: Rm = src[1]
        tt = np.array(tt, float); Rm = np.array(Rm, float); p = sk.parent[nm]
        W[nm] = (tt, Rm) if p is None else (W[p][0] + W[p][1] @ tt, W[p][1] @ Rm)
    return W


def rot_half(C):
    """the rotation halfway along C (axis-angle / 2)"""
    a = np.arccos(np.clip((np.trace(C) - 1) / 2, -1, 1))
    if a < 1e-6: return np.eye(3)
    ax = np.array([C[2, 1] - C[1, 2], C[0, 2] - C[2, 0], C[1, 0] - C[0, 1]]) / (2 * np.sin(a))
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]]); h = a / 2
    return np.eye(3) + np.sin(h) * K + (1 - np.cos(h)) * K @ K


def pitch(R):
    v = -R[:, 2]; return np.degrees(np.arcsin(v[2] / np.linalg.norm(v)))


def key_blocks(f):
    seq = next(i for i, b in enumerate(f.btype) if f.types[b] == 'NiControllerSequence')
    sb = f.blocks[seq]; out = {}
    for j in range(struct.unpack_from('<I', sb, 4)[0]):
        ii, _, _, nm = struct.unpack_from('<iiBi', sb, 12 + 29 * j)
        out[f.strings[nm]] = struct.unpack_from('<i', f.blocks[ii], 32)[0]
    return out


def level(folder, fn, out):
    m = PAT.match(fn); sneak, v = m.group(1) or '', m.group(4) or ''
    aim = KFEval(os.path.join(folder, f'{sneak}h2haim{v}.kf')); A = fk(aim.sample(aim.stop / 2))
    Aloc = aim.sample(aim.stop / 2); neck1 = {'Bip01 Neck1': Aloc['Bip01 Neck1']} if 'Bip01 Neck1' in Aloc else {}
    rel = A['Bip01'][1].T @ A['Bip01 Head'][1]
    k = KFEval(os.path.join(folder, fn)); f = NifFile(os.path.join(folder, fn)); kb = key_blocks(f)
    dn, dh = kb['Bip01 Neck'], kb['Bip01 Head']
    def keys(d):
        b = f.blocks[d]; n, typ = struct.unpack_from('<II', b, 0); assert typ == 1
        return [struct.unpack_from('<f4f', b, 8 + 20 * i) for i in range(n)]
    kn, kh = keys(dn), keys(dh); assert [x[0] for x in kn] == [x[0] for x in kh]
    newn, newh, before, after, corr = [], [], [], [], []
    for (t, *_q) in kn:
        smp = k.sample(t); W = fk(smp, neck1)
        Rh = W['Bip01 Head'][1]; fwd = -Rh[:, 2]; fwd = fwd / np.linalg.norm(fwd)
        h = np.hypot(fwd[0], fwd[1]); pt = np.radians(pitch(W['Bip01'][1] @ rel))
        want = np.array([fwd[0] / h * np.cos(pt), fwd[1] / h * np.cos(pt), np.sin(pt)])
        ax = np.cross(fwd, want); sa = np.linalg.norm(ax); ca = float(np.dot(fwd, want))
        if sa < 1e-9: C = np.eye(3)
        else:
            ax /= sa; K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
            C = np.eye(3) + sa * K + (1 - ca) * K @ K
        Rt = C @ Rh
        Hl = W[sk.parent['Bip01 Head']][1].T @ Rt
        newh.append((t, m2q(Hl)))
        before.append(pitch(Rh)); after.append(pitch(Rt)); corr.append(np.degrees(np.arccos(np.clip((np.trace(C) - 1) / 2, -1, 1))))
    for d, ks in ((dh, newh),):
        b = bytearray(f.blocks[d]); prev = None
        for i, (t, q) in enumerate(ks):
            q = np.array(q, float)
            if prev is not None and np.dot(q, prev) < 0: q = -q
            prev = q; struct.pack_into('<f4f', b, 8 + 20 * i, t, *q)
        f.blocks[d] = bytes(b)
    os.makedirs(out, exist_ok=True); open(os.path.join(out, fn), 'wb').write(f.to_bytes())
    return (min(before), max(before)), (min(after), max(after)), max(corr)


if __name__ == '__main__':
    folder, out = sys.argv[1:3]
    files = sys.argv[3:] or sorted(x for x in os.listdir(folder) if PAT.match(x))
    for fn in files:
        b, a, c = level(folder, fn, out)
        print('%-28s head pitch %6.1f..%5.1f -> %6.1f..%5.1f  largest correction %5.1f deg' % (fn, b[0], b[1], a[0], a[1], c))
