"""KF / skeleton reading + FK for creature-anim authoring."""
import struct, sys, numpy as np
sys.path.insert(0, '/home/claude/fnv')
from nif import Nif
NEG = -3.0e38

def q2m(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                     [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                     [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])
def m2q(m):
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t+1)*2; w = .25*s; x = (m[2,1]-m[1,2])/s; y = (m[0,2]-m[2,0])/s; z = (m[1,0]-m[0,1])/s
    elif m[0,0] > m[1,1] and m[0,0] > m[2,2]:
        s = np.sqrt(1+m[0,0]-m[1,1]-m[2,2])*2; w = (m[2,1]-m[1,2])/s; x = .25*s; y = (m[0,1]+m[1,0])/s; z = (m[0,2]+m[2,0])/s
    elif m[1,1] > m[2,2]:
        s = np.sqrt(1+m[1,1]-m[0,0]-m[2,2])*2; w = (m[0,2]-m[2,0])/s; x = (m[0,1]+m[1,0])/s; y = .25*s; z = (m[1,2]+m[2,1])/s
    else:
        s = np.sqrt(1+m[2,2]-m[0,0]-m[1,1])*2; w = (m[1,0]-m[0,1])/s; x = (m[0,2]+m[2,0])/s; y = (m[1,2]+m[2,1])/s; z = .25*s
    q = np.array([w, x, y, z]); return q/np.linalg.norm(q)

class Skeleton:
    def __init__(s, path):
        n = Nif(path); s.parent = {}; s.local = {}; s.order = []
        def walk(b, par):
            t = n.tname(b)
            if t not in n.NODE_TYPES: return
            r = n.node(b); nm = r['name']
            R = np.array(r['rot']).reshape(3, 3)
            s.local[nm] = (np.array(r['trans']), R, r['scale']); s.parent[nm] = par; s.order.append(nm)
            for c in r['children']:
                if c >= 0: walk(c, nm)
        walk(0, None)
    def fk(s, pose=None, T=False):
        """pose: name -> (trans, R). returns name -> (worldpos, worldR)."""
        W = {}
        for nm in s.order:
            t, R, sc = s.local[nm]
            if pose and nm in pose:
                pt, pR = pose[nm]
                if pt is not None: t = pt
                if pR is not None: R = pR
            if T: R = R.T
            p = s.parent[nm]
            if p is None: W[nm] = (t.copy(), R.copy())
            else:
                pp, pRw = W[p]
                W[nm] = (pp + pRw @ t, pRw @ R)
        return W

class KF:
    def __init__(s, path):
        s.n = n = Nif(path); d = n.d
        s.seq = [i for i in range(n.nblocks) if n.tname(i) == 'NiControllerSequence'][0]
        o = n.boff[s.seq]
        nm, ncb, _ = struct.unpack_from('<iII', d, o); s.name = n.strings[nm]
        s.blocks = []
        for k in range(ncb):
            interp, ctrl, prio, node, pt, ct, cid, iid = struct.unpack_from('<iiBiiiii', d, o+12+29*k)
            s.blocks.append((n.strings[node], interp, prio))
        off = o + 12 + 29*ncb
        s.weight, s.tk, s.cycle, s.freq, s.start, s.stop = struct.unpack_from('<fiIfff', d, off)
        s.textkeys = []
        if s.tk >= 0:
            to = n.boff[s.tk]; _, nk = struct.unpack_from('<iI', d, to)
            for j in range(nk):
                t, si = struct.unpack_from('<fi', d, to+8+8*j); s.textkeys.append((t, n.strings[si]))
    def static_pose(s):
        """name -> (trans or None, R or None) from interpolator transform (t=0 if keyed)."""
        n = s.n; d = n.d; out = {}
        for nm, ib, pr in s.blocks:
            if ib < 0: continue
            tn = n.tname(ib); o = n.boff[ib]
            if tn == 'NiTransformInterpolator':
                t = np.array(struct.unpack_from('<3f', d, o)); q = struct.unpack_from('<4f', d, o+12)
                data, = struct.unpack_from('<i', d, o+32)
                tt = None if t[0] < NEG else t; R = None if q[0] < NEG else q2m(q)
                if data >= 0:
                    kt, kr = s.first_keys(data)
                    if kt is not None: tt = kt
                    if kr is not None: R = q2m(kr)
                out[nm] = (tt, R)
            elif tn == 'NiBSplineCompTransformInterpolator':
                t = np.array(struct.unpack_from('<3f', d, o+16)); q = struct.unpack_from('<4f', d, o+28)
                th, rh, sh = struct.unpack_from('<III', d, o+48)
                out[nm] = (None if t[0] < NEG else t, None if q[0] < NEG else q2m(q))
                out[nm] += (('spline', th, rh),)
        return out
    def first_keys(s, db):
        d = s.n.d; o = s.n.boff[db]
        nr, = struct.unpack_from('<I', d, o); o += 4; R = None; T = None
        if nr:
            rt, = struct.unpack_from('<I', d, o); o += 4
            if rt == 4: return None, None
            R = struct.unpack_from('<4f', d, o+4)
            o += nr * (20 + (12 if rt == 3 else 0))
        nt, = struct.unpack_from('<I', d, o); o += 4
        if nt:
            tt, = struct.unpack_from('<I', d, o); o += 4
            T = np.array(struct.unpack_from('<3f', d, o+4))
        return T, R

# ---------------- full evaluation (keyed + B-spline) ----------------
def slerp(q0, q1, u):
    q0 = np.asarray(q0, float); q1 = np.asarray(q1, float)
    d = np.dot(q0, q1)
    if d < 0: q1 = -q1; d = -d
    if d > 0.9995: q = q0 + (q1 - q0) * u; return q / np.linalg.norm(q)
    th = np.arccos(d); s = np.sin(th)
    return (np.sin((1 - u) * th) * q0 + np.sin(u * th) * q1) / s

def _keys_at(keys, t, interp):
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return interp(v0, v1, u)

def _bspline(cps, nctrl, u01):
    """open uniform cubic B-spline, cps: (nctrl, dim)"""
    deg = 3
    if nctrl <= deg: return cps[0]
    nk = nctrl + deg + 1
    inner = nctrl - deg
    knots = np.array([0] * (deg + 1) + list(range(1, inner)) + [inner] * (deg + 1), float)
    x = min(max(u01, 0.0), 1.0) * inner
    span = min(int(x) + deg, nctrl - 1)
    # de Boor
    d = [cps[j + span - deg].astype(float) for j in range(deg + 1)]
    for r in range(1, deg + 1):
        for j in range(deg, r - 1, -1):
            i = j + span - deg
            den = knots[i + deg + 1 - r] - knots[i]
            a = 0.0 if den == 0 else (x - knots[i]) / den
            d[j] = (1 - a) * d[j - 1] + a * d[j]
    return d[deg]

class KFEval(KF):
    def __init__(s, path):
        KF.__init__(s, path); s.chan = {}
        n = s.n; d = n.d
        for nm, ib, pr in s.blocks:
            if ib < 0: continue
            tn = n.tname(ib); o = n.boff[ib]
            if tn == 'NiTransformInterpolator':
                t = np.array(struct.unpack_from('<3f', d, o)); q = np.array(struct.unpack_from('<4f', d, o + 12))
                db, = struct.unpack_from('<i', d, o + 32)
                ch = dict(t=None if t[0] < NEG else t, q=None if q[0] < NEG else q, tk=None, rk=None, xyz=None)
                if db >= 0: s._read_data(db, ch)
                s.chan[nm] = ch
            elif tn in ('NiBSplineCompTransformInterpolator', 'NiBSplineTransformInterpolator'):
                st, sp, sdat, bdat = struct.unpack_from('<ffii', d, o)
                t = np.array(struct.unpack_from('<3f', d, o + 16)); q = np.array(struct.unpack_from('<4f', d, o + 28))
                th, rh, sh = struct.unpack_from('<III', d, o + 48)
                comp = tn.startswith('NiBSplineComp')
                offs = struct.unpack_from('<6f', d, o + 60) if comp else None
                nctrl, = struct.unpack_from('<I', d, n.boff[bdat])
                so = n.boff[sdat]; nf, = struct.unpack_from('<I', d, so); fl = np.array(struct.unpack_from(f'<{nf}f', d, so + 4))
                so2 = so + 4 + 4 * nf; ns, = struct.unpack_from('<I', d, so2); sh_ = np.array(struct.unpack_from(f'<{ns}h', d, so2 + 4), float)
                def cps(handle, dim, oi):
                    if handle == 0xFFFFFFFF or handle == 0xFFFF: return None
                    if comp: raw = sh_[handle:handle + nctrl * dim] / 32767.0 * offs[oi + 1] + offs[oi]
                    else: raw = fl[handle:handle + nctrl * dim]
                    return raw.reshape(nctrl, dim)
                s.chan[nm] = dict(t=None if t[0] < NEG else t, q=None if q[0] < NEG else q, span=(st, sp), nctrl=nctrl,
                                  tc=cps(th, 3, 0), rc=cps(rh, 4, 2), tk=None, rk=None, xyz=None)
    def _read_data(s, db, ch):
        d = s.n.d; o = s.n.boff[db]
        nr, = struct.unpack_from('<I', d, o); o += 4
        if nr:
            rt, = struct.unpack_from('<I', d, o); o += 4
            if rt == 4:
                xyz = []
                for _ in range(3):
                    nk, = struct.unpack_from('<I', d, o); o += 4; ks = []
                    if nk:
                        it, = struct.unpack_from('<I', d, o); o += 4
                        step = 8 + (8 if it == 2 else 12 if it == 3 else 0)
                        for j in range(nk): ks.append(struct.unpack_from('<ff', d, o + j * step))
                        o += nk * step
                    xyz.append(ks)
                ch['xyz'] = xyz
            else:
                step = 20 + (12 if rt == 3 else 0)
                ch['rk'] = [(struct.unpack_from('<f', d, o + j * step)[0], np.array(struct.unpack_from('<4f', d, o + j * step + 4))) for j in range(nr)]
                o += nr * step
        nt, = struct.unpack_from('<I', d, o); o += 4
        if nt:
            tt, = struct.unpack_from('<I', d, o); o += 4
            step = 16 + (24 if tt == 2 else 12 if tt == 3 else 0)
            ch['tk'] = [(struct.unpack_from('<f', d, o + j * step)[0], np.array(struct.unpack_from('<3f', d, o + j * step + 4))) for j in range(nt)]
    def sample(s, t):
        out = {}
        for nm, ch in s.chan.items():
            T = ch['t']; Q = ch['q']; R = None
            if 'span' in ch:
                st, sp = ch['span']; u = (t - st) / (sp - st) if sp > st else 0
                if ch['tc'] is not None: T = _bspline(ch['tc'], ch['nctrl'], u)
                if ch['rc'] is not None: Q = _bspline(ch['rc'], ch['nctrl'], u); Q = Q / np.linalg.norm(Q)
            else:
                if ch['tk']: T = _keys_at(ch['tk'], t, lambda a, b, u: a + (b - a) * u)
                if ch['rk']: Q = _keys_at(ch['rk'], t, slerp)
                if ch['xyz']:
                    ang = [(_keys_at(k, t, lambda a, b, u: a + (b - a) * u) if k else 0.0) for k in ch['xyz']]
                    ax, ay, az = ang
                    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
                    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
                    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
                    R = Rz @ Ry @ Rx
            if R is None and Q is not None: R = q2m(Q)
            out[nm] = (T, R)
        return out
