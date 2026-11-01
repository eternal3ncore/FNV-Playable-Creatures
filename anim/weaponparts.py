"""Weapon-part tracks: copies the controlled blocks that drive the *weapon mesh's own* sub-nodes ('##Name':
visibility switches, barrels, bolts, belts, display textures) from the vanilla file of the same animation group
into a creature KF, time-warped onto the creature file's text keys.  No body bones are copied.

Why: several weapon meshes are drawn only while the character animation switches their parts on
(e.g. the Titans of the New West minigun keeps '##MinigunGun' hidden unless the playing animation sets it
visible), and animated parts (spinning barrels, bolts) are keyed in the character animation."""
import struct, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/claude/fnv')
from nif import Nif
from nifedit import NifFile

LOOSE = re.compile(r'clip|mag|shell|ammo|round|cell|drum|missile|rocket|nuke|grenade|cartridge|bullet|battery', re.I)

def _seq(n):
    return [i for i in range(n.nblocks) if n.tname(i) == 'NiControllerSequence'][0]

def _textkeys(n, seq):
    o = n.boff[seq]; _, ncb, _ = struct.unpack_from('<iII', n.d, o)
    tk, = struct.unpack_from('<i', n.d, o + 12 + 29 * ncb + 4)
    stop, = struct.unpack_from('<f', n.d, o + 12 + 29 * ncb + 20)
    ks = []
    if tk >= 0:
        to = n.boff[tk]; _, nk = struct.unpack_from('<iI', n.d, to)
        for j in range(nk):
            t, si = struct.unpack_from('<fi', n.d, to + 8 + 8 * j); ks.append((t, n.strings[si] if si >= 0 else ''))
    return ks, stop

def timemap(hkeys, hlen, okeys, olen):
    """piecewise-linear map human time -> creature time through text keys present in both"""
    def norm(s): return s.strip().lower().replace(' ', '')
    oi = {}
    for t, s in okeys: oi.setdefault(norm(s), t)
    pairs = [(0.0, 0.0)]
    used = set()
    for t, s in hkeys:
        k = norm(s)
        if k in ('start', 'end') or k in used or k not in oi or k.startswith('blend') or k.startswith('sound') or k.startswith('enum'): continue
        used.add(k); pairs.append((t, oi[k]))
    pairs.append((hlen, olen))
    pairs.sort()
    mono = [pairs[0]]
    for a, b in pairs[1:]:
        if a > mono[-1][0] + 1e-6 and b > mono[-1][1] + 1e-6: mono.append((a, b))
    if mono[-1][0] < hlen - 1e-6: mono.append((hlen, max(olen, mono[-1][1] + 1e-3)))
    def f(t):
        if t <= mono[0][0]: return mono[0][1] + (t - mono[0][0])
        for (a0, b0), (a1, b1) in zip(mono, mono[1:]):
            if t <= a1: return b0 + (t - a0) * (b1 - b0) / (a1 - a0)
        a0, b0 = mono[-1]; return b0 + (t - a0)
    return f

def _remap_keys(b, off, nk, ktype, vsize, f):
    """rewrite nk keys starting at off: key = time + value(vsize bytes) (+ tangents by type)"""
    extra = {1: 0, 5: 0, 2: 2 * vsize, 3: 12}.get(ktype, 0)
    step = 4 + vsize + extra
    for j in range(nk):
        t, = struct.unpack_from('<f', b, off + j * step); struct.pack_into('<f', b, off + j * step, f(t))
    return off + nk * step

def _remap_data(tname, raw, f):
    b = bytearray(raw)
    if tname == 'NiBoolData':
        nk, = struct.unpack_from('<I', b, 0)
        if nk: kt, = struct.unpack_from('<I', b, 4); _remap_keys(b, 8, nk, kt, 1, f)
    elif tname == 'NiFloatData':
        nk, = struct.unpack_from('<I', b, 0)
        if nk: kt, = struct.unpack_from('<I', b, 4); _remap_keys(b, 8, nk, kt, 4, f)
    elif tname == 'NiPosData':
        nk, = struct.unpack_from('<I', b, 0)
        if nk: kt, = struct.unpack_from('<I', b, 4); _remap_keys(b, 8, nk, kt, 12, f)
    elif tname in ('NiTransformData', 'NiKeyframeData'):
        o = 0
        nr, = struct.unpack_from('<I', b, o); o += 4
        if nr:
            rt, = struct.unpack_from('<I', b, o); o += 4
            if rt == 4:
                for _ in range(3):
                    nk, = struct.unpack_from('<I', b, o); o += 4
                    if nk:
                        kt, = struct.unpack_from('<I', b, o); o += 4
                        o = _remap_keys(b, o, nk, kt, 4, f)
            else:
                step = 20 + (12 if rt == 3 else 0)
                for j in range(nr):
                    t, = struct.unpack_from('<f', b, o + j * step); struct.pack_into('<f', b, o + j * step, f(t))
                o += nr * step
        nt, = struct.unpack_from('<I', b, o); o += 4
        if nt:
            kt, = struct.unpack_from('<I', b, o); o += 4
            o = _remap_keys(b, o, nt, kt, 12, f)
        ns, = struct.unpack_from('<I', b, o); o += 4
        if ns:
            kt, = struct.unpack_from('<I', b, o); o += 4
            o = _remap_keys(b, o, ns, kt, 4, f)
    return bytes(b)

# interpolator type -> offsets of block refs inside it
IREFS = {'NiBoolInterpolator': [1], 'NiBoolTimelineInterpolator': [1], 'NiFloatInterpolator': [4],
         'NiPoint3Interpolator': [12], 'NiTransformInterpolator': [32],
         'NiBSplineCompTransformInterpolator': [8, 12], 'NiBSplineTransformInterpolator': [8, 12],
         'NiBSplineCompFloatInterpolator': [8, 12], 'NiBSplineFloatInterpolator': [8, 12],
         'NiBSplineCompPoint3Interpolator': [8, 12], 'NiBSplinePoint3Interpolator': [8, 12]}

def part_tracks(human_path, keep_loose_transforms=True):
    n = Nif(human_path); s = _seq(n); o = n.boff[s]
    _, ncb, _ = struct.unpack_from('<iII', n.d, o)
    tracks = []
    for j in range(ncb):
        interp, ctrl, prio, node, pt, ct, cid, iid = struct.unpack_from('<iiBiiiii', n.d, o + 12 + 29 * j)
        name = n.str(node) or ''
        if not name.startswith('##') or interp < 0: continue
        itype = n.tname(interp)
        if itype not in IREFS: continue
        ctype = n.str(ct) or ''
        if not keep_loose_transforms and ctype == 'NiTransformController' and LOOSE.search(name): continue
        subs = []
        for off in IREFS[itype]:
            r, = struct.unpack_from('<i', n.d, n.boff[interp] + off)
            subs.append((off, None if r < 0 else (n.tname(r), n.d[n.boff[r]:n.boff[r] + n.bsize[r]])))
        tracks.append(dict(name=name, prio=prio, pt=n.str(pt), ct=ctype, cid=n.str(cid), iid=n.str(iid),
                           itype=itype, interp=n.d[n.boff[interp]:n.boff[interp] + n.bsize[interp]], subs=subs))
    keys, stop = _textkeys(n, s)
    return tracks, keys, stop

def merge(our_path, human_path, keep_loose_transforms=True):
    """append the human file's weapon-part tracks to our KF (in place). returns number of tracks added"""
    tracks, hkeys, hlen = part_tracks(human_path, keep_loose_transforms)
    if not tracks: return 0
    f = NifFile(our_path)
    si = f.str_index
    seq = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    ours = Nif(our_path); okeys, olen = _textkeys(ours, _seq(ours))
    have = set()
    sb = f.blocks[seq]
    name, ncb, grow = struct.unpack_from('<iII', sb, 0)
    for j in range(ncb):
        nd, = struct.unpack_from('<i', sb, 12 + 29 * j + 9)
        if 0 <= nd < len(f.strings): have.add(f.strings[nd])
    tm = timemap(hkeys, hlen, okeys, olen)
    cbs = []
    for tr in tracks:
        if tr['name'] in have: continue
        ib = bytearray(tr['interp'])
        if tr['itype'].startswith('NiBSpline'):
            st, sp = struct.unpack_from('<ff', ib, 0); struct.pack_into('<ff', ib, 0, tm(st), tm(sp))
        for off, sub in tr['subs']:
            if sub is None: continue
            tname, raw = sub
            if not tname.startswith('NiBSpline'): raw = _remap_data(tname, raw, tm)
            struct.pack_into('<i', ib, off, f.add_block(tname, raw))
        ii = f.add_block(tr['itype'], bytes(ib))
        S = lambda x: -1 if x is None else si(x)
        cbs.append(struct.pack('<iiBiiiii', ii, -1, tr['prio'], si(tr['name']), S(tr['pt']), S(tr['ct']), S(tr['cid']), S(tr['iid'])))
    if not cbs: return 0
    head = struct.pack('<iII', name, ncb + len(cbs), grow)
    f.blocks[seq] = head + sb[12:12 + 29 * ncb] + b''.join(cbs) + sb[12 + 29 * ncb:]
    open(our_path, 'wb').write(f.to_bytes())
    Nif(our_path)
    return len(cbs)

def rotate_node(path, node, Rrel):
    """post-multiply the local rotation of `node` by Rrel in every transform track of the KF (in place).
    Returns the number of tracks changed."""
    import numpy as np
    from kf import q2m, m2q
    f = NifFile(path)
    seq = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    sb = f.blocks[seq]; _, ncb, _ = struct.unpack_from('<iII', sb, 0)
    Rrel = np.asarray(Rrel, float); n = 0
    def rq(b, off):
        q = struct.unpack_from('<4f', b, off)
        if q[0] < -1e30: return
        struct.pack_into('<4f', b, off, *m2q(q2m(q) @ Rrel))
    for j in range(ncb):
        interp, = struct.unpack_from('<i', sb, 12 + 29 * j)
        nd, = struct.unpack_from('<i', sb, 12 + 29 * j + 9)
        if interp < 0 or not (0 <= nd < len(f.strings)) or f.strings[nd] != node: continue
        t = f.types[f.btype[interp]]; b = bytearray(f.blocks[interp])
        if t == 'NiTransformInterpolator':
            rq(b, 12); db, = struct.unpack_from('<i', b, 32)
            if db >= 0:
                d = bytearray(f.blocks[db]); nr, = struct.unpack_from('<I', d, 0)
                if nr:
                    rt, = struct.unpack_from('<I', d, 4)
                    if rt == 4:
                        d = bytearray(_xyz_to_quat(bytes(d), Rrel))
                    else:
                        step = 20 + (12 if rt == 3 else 0)
                        for k in range(nr): rq(d, 8 + k * step + 4)
                f.blocks[db] = bytes(d)
        elif t in ('NiBSplineCompTransformInterpolator', 'NiBSplineTransformInterpolator'):
            rh, = struct.unpack_from('<I', b, 52)
            if rh not in (0xFFFF, 0xFFFFFFFF):
                # animated spline rotation (e.g. Point Lookout swampfolk rifles): the track is resampled at
                # 30 fps into a new linear NiTransformInterpolator / NiTransformData, rotated, and the controlled
                # block points at it (the spline blocks stay in the file, unreferenced)
                f.blocks[seq] = sb = _resample_rotated(f, sb, j, path, node, Rrel); n += 1
                continue
            rq(b, 28)
        else: continue
        f.blocks[interp] = bytes(b); n += 1
    open(path, 'wb').write(f.to_bytes())
    return n

def _resample_rotated(f, sb, j, path, node, Rrel, fps=30):
    import numpy as np
    from kf import KFEval, m2q, q2m
    k = KFEval(path); L = k.stop; n = max(2, int(round(L * fps)) + 1)
    qs = []; ts = []; prev = None
    for i in range(n):
        t = L * i / (n - 1); smp = k.sample(t)[node]
        q = m2q(np.asarray(smp[1], float) @ Rrel)
        if prev is not None and np.dot(q, prev) < 0: q = -q
        prev = q; qs.append((t, q)); ts.append((t, smp[0]))
    body = struct.pack('<II', len(qs), 1) + b''.join(struct.pack('<f4f', t, *q) for t, q in qs)
    if ts[0][1] is None: body += struct.pack('<I', 0); t0 = (0.0, 0.0, 0.0)
    else:
        body += struct.pack('<II', len(ts), 1) + b''.join(struct.pack('<f3f', t, *p) for t, p in ts); t0 = tuple(ts[0][1])
    body += struct.pack('<I', 0)
    di = f.add_block('NiTransformData', body)
    ii = f.add_block('NiTransformInterpolator', struct.pack('<3f4ffi', *t0, *qs[0][1], 1.0, di))
    b = bytearray(sb); struct.pack_into('<i', b, 12 + 29 * j, ii)
    return bytes(b)

def _xyz_to_quat(d, Rrel):
    """NiTransformData with XYZ euler rotation keys -> linear quaternion keys (times = union of the axis
    keys), each post-multiplied by Rrel; translation/scale sections are kept as they are."""
    import numpy as np
    from kf import m2q
    o = 8; groups = []
    for _ in range(3):
        nk, = struct.unpack_from('<I', d, o); o += 4; ks = []
        if nk:
            kt, = struct.unpack_from('<I', d, o); o += 4
            step = 8 + (8 if kt == 2 else 12 if kt == 3 else 0)
            for j in range(nk): ks.append(struct.unpack_from('<ff', d, o + j * step))
            o += nk * step
        groups.append(ks)
    rest = d[o:]
    def val(ks, t):
        if not ks: return 0.0
        if t <= ks[0][0]: return ks[0][1]
        for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
            if t <= t1: return v0 + (v1 - v0) * ((t - t0) / (t1 - t0) if t1 > t0 else 0)
        return ks[-1][1]
    times = sorted(set(t for g in groups for t, _ in g)) or [0.0]
    out = struct.pack('<II', len(times), 1)
    prev = None
    for t in times:
        ax, ay, az = (val(g, t) for g in groups)
        Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
        Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
        Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
        q = m2q(Rz @ Ry @ Rx @ Rrel)
        if prev is not None and np.dot(q, prev) < 0: q = -q
        prev = q
        out += struct.pack('<f4f', t, *q)
    return out + rest
