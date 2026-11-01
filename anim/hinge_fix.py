"""Hinge fix: re-solves arm / leg chains of generated animations so elbows and knees only bend about their real hinge.
The creature rigs (Bip01 bipeds, every playable race) bend Forearm and Calf ONLY about local Z (verified against all of
their own vanilla animations: zero off-axis rotation). The generators' 2-bone IK (rig.ik, loco2/retarget IK, jumps)
aimed those bones with a free minimal rotation, so they also twisted / bent sideways -> wrung elbows, knees and wrists.
Per frame and per chain (UpperArm-Forearm-Hand, Thigh-Calf-Foot), in the chain's parent frame (so unkeyed ancestors
don't matter):
  * the end (hand / foot) keeps its position and world orientation, the elbow / knee stays on the same side (pole =
    its original position);
  * hinge angle about local Z from the end distance (law of cosines on the real bone geometry), within the creature's
    own hinge range (from its vanilla animations) on its bending side - no hyperextension, no over-fold;
  * upper arm / thigh = the rotation that puts end and elbow there; hand / foot local = the remaining rotation (any
    twist ends up at the wrist / ankle, where the vanilla animations carry it).
Only chains that actually violate the hinge (off-axis > TOL deg, or angle outside the range) are rewritten: their
three tracks are resampled at 30 fps into linear keys; everything else in the file is untouched.
usage: python3 hinge_fix.py <folder> <audit json with hinge_range> [--dry] [--files a.kf,b.kf]"""
import sys, os, json, struct, glob, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from kf import KFEval, Skeleton, m2q, q2m
from nifedit import NifFile
CHAINS = [('Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand'), ('Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand'),
          ('Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot'), ('Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot')]
TOL = 3.0          # off-hinge degrees tolerated before a chain is rewritten
RANGE_MARGIN = 5.0
MIN_FOLD = 135.0
RANGE_FIX = 15.0   # a chain with a clean hinge is only rewritten when its angle leaves the own range by more than this
                   # (vanilla files sampled finer than the envelope peek a few degrees past it - left untouched)
FPS = 30

def Rz(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
def hinge_split(Rrel):
    phi = np.degrees(np.arctan2(Rrel[1, 0], Rrel[0, 0]))
    res = Rz(phi).T @ Rrel
    return phi, np.degrees(np.arccos(np.clip((np.trace(res) - 1) / 2, -1, 1)))
def frame(x, y):
    x = x / np.linalg.norm(x); y = y - x * np.dot(x, y); y = y / np.linalg.norm(y)
    return np.column_stack([x, y, np.cross(x, y)])

class Chain:
    def __init__(s, sk, idle, names, rng):
        s.u, s.h, s.e = names
        loc = lambda n: (np.array(idle[n][0] if n in idle and idle[n][0] is not None else sk.local[n][0], float),
                         np.array(idle[n][1] if n in idle and idle[n][1] is not None else sk.local[n][1], float))
        s.tu, s.Ru0 = loc(s.u); s.th, s.Rh0 = loc(s.h); s.te, s.Re0 = loc(s.e)
        lo, hi = rng
        grid = np.arange(lo - RANGE_MARGIN, hi + RANGE_MARGIN + 0.01, 0.25)
        lens = np.array([np.linalg.norm(s.th + s.Rh0 @ Rz(g) @ s.te) for g in grid])
        i_s = int(np.argmax(lens)); phis = grid[i_s]
        # bending side = the side of the straight angle with the larger extent of the creature's own range
        side = grid[:i_s + 1][::-1] if (phis - grid[0]) > (grid[-1] - phis) else grid[i_s:]
        # the bending side reaches at least MIN_FOLD from straight: a creature whose own animations never fold
        # the elbow much (the trog walks on its arms) still has an anatomical elbow / knee
        sgn = 1.0 if side[-1] >= side[0] else -1.0
        if abs(side[-1] - phis) < MIN_FOLD:
            side = np.arange(phis, phis + sgn * (MIN_FOLD + 0.01), sgn * 0.25)
            if sgn > 0: hi = max(hi, phis + MIN_FOLD - RANGE_MARGIN)
            else: lo = min(lo, phis - MIN_FOLD + RANGE_MARGIN)
        s.side = side; s.side_len = np.array([np.linalg.norm(s.th + s.Rh0 @ Rz(g) @ s.te) for g in side])
        s.lo, s.hi = lo - RANGE_MARGIN, hi + RANGE_MARGIN
    def bad(s, Rh):
        phi, off = hinge_split(s.Rh0.T @ Rh)
        lo, hi = s.lo + RANGE_MARGIN, s.hi - RANGE_MARGIN          # the own range itself
        return off > TOL or phi < lo - RANGE_FIX or phi > hi + RANGE_FIX
    def solve(s, tu, Ru, Rh, Re, th, te, prev_pole):
        """inputs: current locals (translations from the file); returns new (Ru, Rh, Re) locals and the pole used"""
        E = tu + Ru @ th; W = tu + Ru @ (th + Rh @ te); Hw = Ru @ Rh @ Re
        d = np.linalg.norm(W - tu)
        lens = np.array([np.linalg.norm(th + s.Rh0 @ Rz(g) @ te) for g in s.side]) if not np.allclose(te, s.te) or not np.allclose(th, s.th) else s.side_len
        i = int(np.argmin(np.abs(lens - d)))
        phi = s.side[i]
        Rh_new = s.Rh0 @ Rz(phi)
        p = th + Rh_new @ te                                   # end in the upper bone's frame
        w = W - tu
        pole = E - tu; pole_perp = pole - w * np.dot(pole, w) / max(np.dot(w, w), 1e-9)
        if np.linalg.norm(pole_perp) < 1e-3 * max(np.linalg.norm(th), 1e-3):
            pole_perp = prev_pole if prev_pole is not None else pole_perp + np.array([0, 0, 1e-3])
        A = frame(p, th); B = frame(w, pole_perp)
        Ru_new = B @ A.T
        Re_new = (Ru_new @ Rh_new).T @ Hw
        return Ru_new, Rh_new, Re_new, pole_perp

def _cb_index(f, seq_bi, name):
    sb = f.blocks[seq_bi]; _, ncb, _ = struct.unpack_from('<iII', sb, 0)
    for j in range(ncb):
        nd, = struct.unpack_from('<i', sb, 12 + 29 * j + 9)
        if 0 <= nd < len(f.strings) and f.strings[nd] == name: return j
    return None
def write_tracks(path, tracks, prio_default):
    """tracks: name -> list of (t, trans, R). Replaces / adds the controlled blocks of those nodes."""
    f = NifFile(path)
    seq = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    for name, keys in tracks.items():
        qs = []; prev = None
        for t, tr, R in keys:
            q = m2q(R)
            if prev is not None and np.dot(q, prev) < 0: q = -q
            prev = q; qs.append((t, q))
        ts = [(t, tr) for t, tr, _ in keys]
        tstatic = all(np.allclose(p, ts[0][1], atol=1e-4) for _, p in ts)
        body = struct.pack('<II', len(qs), 1) + b''.join(struct.pack('<f4f', t, *q) for t, q in qs)
        body += struct.pack('<I', 0) if tstatic else struct.pack('<II', len(ts), 1) + b''.join(struct.pack('<f3f', t, *p) for t, p in ts)
        body += struct.pack('<I', 0)
        di = f.add_block('NiTransformData', body)
        ii = f.add_block('NiTransformInterpolator', struct.pack('<3f4ffi', *ts[0][1], *qs[0][1], 1.0, di))
        j = _cb_index(f, seq, name)
        sb = bytearray(f.blocks[seq])
        if j is not None: struct.pack_into('<i', sb, 12 + 29 * j, ii)
        else:
            nm_, ncb, grow = struct.unpack_from('<iII', sb, 0)
            cb = struct.pack('<iiBiiiii', ii, -1, prio_default, f.str_index(name), -1, f.str_index('NiTransformController'), -1, -1)
            sb = sb[:12 + 29 * ncb] + cb + sb[12 + 29 * ncb:]; struct.pack_into('<I', sb, 4, ncb + 1)
        f.blocks[seq] = bytes(sb)
    open(path, 'wb').write(f.to_bytes())

def fix_file(path, sk, idle, chains, dry=False):
    k = KFEval(path); L = k.stop
    keyed = {nm: pr for nm, _, pr in k.blocks}
    n = max(2, int(round(L * FPS)) + 1); times = [L * i / (n - 1) for i in range(n)]
    smp = [k.sample(t) for t in times]
    def loc(s_, nm):
        tr = s_[nm][0] if nm in s_ and s_[nm][0] is not None else (idle[nm][0] if nm in idle and idle[nm][0] is not None else sk.local[nm][0])
        R = s_[nm][1] if nm in s_ and s_[nm][1] is not None else (idle[nm][1] if nm in idle and idle[nm][1] is not None else sk.local[nm][1])
        return np.array(tr, float), np.array(R, float)
    tracks = {}; report = []
    for ch in chains:
        if ch.h not in keyed: continue
        if not any(ch.bad(loc(s_, ch.h)[1]) for s_ in smp): continue
        worst = max(hinge_split(ch.Rh0.T @ loc(s_, ch.h)[1])[1] for s_ in smp)
        ku, kh, ke = [], [], []; pole = None
        for t, s_ in zip(times, smp):
            tu, Ru = loc(s_, ch.u); th, Rh = loc(s_, ch.h); te, Re = loc(s_, ch.e)
            Ru2, Rh2, Re2, pole = ch.solve(tu, Ru, Rh, Re, th, te, pole)
            ku.append((t, tu, Ru2)); kh.append((t, th, Rh2)); ke.append((t, te, Re2))
        tracks[ch.u] = ku; tracks[ch.h] = kh
        if ch.e in keyed: tracks[ch.e] = ke
        report.append((ch.h, round(worst, 1)))
    if tracks and not dry:
        write_tracks(path, tracks, max(keyed.values()) if keyed else 50)
    return report

def run(folder, audit_json, dry=False, only=None):
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    idle = KFEval(os.path.join(folder, 'mtidle.kf')).sample(0)
    rng = json.load(open(audit_json))['hinge_range']
    chains = [Chain(sk, idle, c, rng[c[1]]) for c in CHAINS if all(b in sk.local for b in c) and c[1] in rng]
    out = []
    files = sorted(glob.glob(os.path.join(folder, '**', '*.kf'), recursive=True))
    for p in files:
        rel = os.path.relpath(p, folder)
        if only and rel not in only: continue
        try: r = fix_file(p, sk, idle, chains, dry)
        except Exception as e: out.append((rel, 'ERROR ' + str(e)[:100])); continue
        if r: out.append((rel, r))
    return out

if __name__ == '__main__':
    only = None
    if '--files' in sys.argv: only = set(sys.argv[sys.argv.index('--files') + 1].split(','))
    res = run(sys.argv[1], sys.argv[2], '--dry' in sys.argv, only)
    for r in res: print(r)
    print(len(res), 'files', 'would change' if '--dry' in sys.argv else 'rewritten')
