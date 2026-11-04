"""Directional power attacks of a one-handed set made from the race's two-handed set (rig.offhand_release) lost the
two-handed file's travel: offhand_release samples through a Rig, which puts the accum root at the origin, so the
release had no root motion, and power_legs.py then took it for an in-place swing and dropped its lower body. The
Ghost's 1HM Forward / Back / Left / Right powers stood in place while its 2HM ones lunge (root 467 / 516).
This grafts the source type's accum root, NonAccum, Pelvis, legs and Spine (keyed at 30 fps from the source file,
its priorities) into the derived file; the derived file's other channels (the free off arm, the weapon sub-nodes)
stay as they are. Sneak from sneak.
usage: python3 power_graft.py <folder> <Skeleton.nif> <dst type> <src type> [--apply]     e.g. Ghost 1hm 2hm"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile

GROUPS = ('attackforwardpower', 'attackbackpower', 'attackleftpower', 'attackrightpower')
LOWER = ['Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis', 'Bip01 Spine'] + \
        [f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot', 'Toe0')]


def keys_of(ev, sk, name, fps=30):
    n = max(2, int(round((ev.stop - ev.start) * fps)) + 1); out = []
    t0, R0, _ = sk.local[name]
    for i in range(n):
        t = ev.start + (ev.stop - ev.start) * i / (n - 1); s = ev.sample(t).get(name, (None, None))
        p = np.array(s[0] if s[0] is not None else t0, float); R = np.array(s[1] if s[1] is not None else R0, float)
        U, _, Vt = np.linalg.svd(R); out.append((t - ev.start, p, U @ Vt))
    return out


def interp_for(f, kk):
    """a linear-keyed NiTransformInterpolator + NiTransformData for [(t, p, R)]"""
    from kf import m2q
    qs = []; prev = None
    for t, p, R in kk:
        q = m2q(R)
        if prev is not None and np.dot(q, prev) < 0: q = -q
        qs.append((t, q)); prev = q
    body = struct.pack('<II', len(qs), 1) + b''.join(struct.pack('<f4f', t, *q) for t, q in qs)
    body += struct.pack('<II', len(kk), 1) + b''.join(struct.pack('<f3f', t, *p) for t, p, _ in kk) + struct.pack('<I', 0)
    data = f.add_block('NiTransformData', body)
    return f.add_block('NiTransformInterpolator', struct.pack('<3f4ffi', *kk[0][1], *qs[0][1], 1.0, data))


def graft(dst, src, sk):
    ev = KFEval(src); prio = {b[0]: b[2] for b in ev.blocks}
    k = KFFile(dst); f = k.f; d = f.blocks[k.seq]
    nm, ncb, sz = struct.unpack_from('<iII', d, 0)
    entries = [bytearray(d[12 + 29 * i: 12 + 29 * (i + 1)]) for i in range(ncb)]; tail = d[12 + 29 * ncb:]
    at = {n: i for i, (o, n) in enumerate(k.cb)}; done = []
    for name in LOWER:
        if name not in prio: continue
        if name in at: e = entries[at[name]]
        else: e = bytearray(entries[0]); struct.pack_into('<i', e, 9, f.str_index(name)); entries.append(e)
        struct.pack_into('<i', e, 0, interp_for(f, keys_of(ev, sk, name))); struct.pack_into('<B', e, 8, prio[name])
        done.append(name)
    f.blocks[k.seq] = struct.pack('<iII', nm, len(entries), sz) + b''.join(bytes(e) for e in entries) + tail
    k.save(dst); return done


def run(folder, skel, T, S, apply=False):
    sk = Skeleton(skel); rep = []
    for sn in ('', 'sneak'):
        for g in GROUPS:
            dst = os.path.join(folder, f'{sn}{T}{g}.kf'); src = os.path.join(folder, f'{sn}{S}{g}.kf')
            if not (os.path.exists(dst) and os.path.exists(src)): rep.append(f'{sn}{T}{g}: missing'); continue
            de = KFEval(dst); se = KFEval(src)
            r = lambda e: (np.linalg.norm(np.array(e.sample(e.stop)['Bip01'][0]) - np.array(e.sample(e.start)['Bip01'][0]))
                           if 'Bip01' in e.chan and e.sample(e.start)['Bip01'][0] is not None else 0.0)
            if abs((de.stop - de.start) - (se.stop - se.start)) > 1e-3: rep.append(f'{sn}{T}{g}: length differs, skipped'); continue
            if r(de) >= 60: rep.append(f'{sn}{T}{g}: already travels {r(de):.0f}'); continue
            if apply: rep.append(f'{sn}{T}{g}: + {graft(dst, src, sk)} (source root {r(se):.0f})')
            else: rep.append(f'{sn}{T}{g}: would graft (source root {r(se):.0f})')
    print('\n'.join(rep))


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if x != '--apply']
    run(a[0], a[1], a[2], a[3], '--apply' in sys.argv)
