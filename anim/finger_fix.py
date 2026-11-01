"""Off-hand finger curl fix.

rig.pose curls the off hand with R @ rotm(CURL_AXIS, -35 * curl) on every Bip01 L Finger{1-4}{,1,2} bone. Every
creature's own fingers (both hands) flex toward the palm about local +Z (measured: relaxed idles and native grips of all
races are positive), so the generated curl bent the left fingers backwards. synth_aims also applied the aim curl twice
(loc0 with curl, then each variant with curl again): synthetic aims sat at idle o Rz(-2 * 35 * 0.6 = -42 deg).
Signature: all curled bones carry the SAME rotation about their local Z relative to the base pose. Per type T:
  synthetic aim (Taim = idle o Rz(-42) on every curl bone): base = idle, phi = deviation from idle,
      intended = 21 (aim curl once) + 35 * curl  ->  new = idle o Rz(-phi - 21)
  own aim (anything else): base = Taim's first pose, phi = deviation from it, new = base o Rz(-phi)
Frames whose curl bones don't share one Z angle at or below -41 (synthetic grip) / -8 (own aim) are left as they are
(native motion; e.g. the Ghost's pistol reloads come from another generator and curl the natural way).
usage: python3 finger_fix.py <race folder> [--apply]"""
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile, times

CURL = [f'Bip01 L Finger{a}{b}' for a in '1234' for b in ('', '1', '2')]
TYPES = ['1hp', '2hr', '2ha', '2hh', '2hl', '1gt', '1md', '1lm']        # ranged / thrown: the generated off-hand motions
SYNTH_MIN, OWN_MIN = -41.0, -8.0     # a curl frame: uniform Z offset <= -41 from idle (synthetic grip) / <= -8 from an own aim


def rz(a):
    c, s = np.cos(np.radians(a)), np.sin(np.radians(a)); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def zdev(B, R):
    """signed angle about local Z of B^T R, and how far it is from a pure Z rotation"""
    D = B.T @ R; a = np.degrees(np.arctan2(D[1, 0] - D[0, 1], D[0, 0] + D[1, 1]))
    return a, float(np.abs(D - rz(a)).max())


def uniform(base, pose, bones):
    angs = []
    for n in bones:
        if n not in pose or pose[n][1] is None or n not in base: return None
        a, err = zdev(base[n], pose[n][1])
        if err > 0.02: return None
        angs.append(a)
    if max(angs) - min(angs) > 1.0: return None
    return float(np.mean(angs))


def first_pose(path):
    k = KFEval(path); s = k.sample(k.start); return {n: v[1] for n, v in s.items() if v[1] is not None}


def fix(folder, apply=False):
    files = sorted(fn for fn in os.listdir(folder) if fn.endswith('.kf'))
    idle = first_pose(os.path.join(folder, 'mtidle.kf'))
    sk = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    bones = [n for n in CURL if n in idle]
    report = []; nfix = 0
    for T in TYPES:
        aim = os.path.join(folder, T + 'aim.kf')
        if not os.path.exists(aim): continue
        A = first_pose(aim)
        if any(n not in A for n in bones): continue
        d = uniform(idle, {n: (None, A[n]) for n in bones}, bones)
        synth = d is not None and abs(d + 42.0) < 1.0
        base = idle if synth else A
        mine = [fn for fn in files if re.match(r'^(sneak)?' + T + r'[a-z]', fn)]
        for fn in mine:
            path = os.path.join(folder, fn); k = KFEval(path)
            if any(n not in k.chan for n in bones): continue
            ts = times(k); poses = [k.sample(t) for t in ts]
            phis = [uniform(base, p, bones) for p in poses]
            lim = SYNTH_MIN if synth else OWN_MIN
            hit = [(t, ph) for t, ph in zip(ts, phis) if ph is not None and ph <= lim]
            if not hit: continue
            new = {n: [] for n in bones}
            for t, p, ph in zip(ts, poses, phis):
                for n in bones:
                    tr = p[n][0] if p[n][0] is not None else sk.local[n][0]      # unkeyed translation = the bone's own
                    if ph is not None and ph <= lim:
                        R = base[n] @ rz((-ph - 21.0) if synth else -ph)
                    else: R = p[n][1]
                    new[n].append((t, np.array(tr), R))
            # keep static channels static
            kf = KFFile(path)
            for n in bones:
                ks = new[n]
                if all(np.allclose(ks[0][2], x[2], atol=1e-5) for x in ks): ks = [ks[0]]
                kf.set_channel(n, ks)
            if apply: kf.save()
            nfix += 1
            report.append(f'{fn}: {"synthetic aim" if synth else "own aim"} base, {len(hit)}/{len(ts)} frames, curl {min(h for _, h in hit):.0f}..{max(h for _, h in hit):.0f} -> '
                          f'{(-max(h for _, h in hit) - 21) if synth else -max(h for _, h in hit):.0f}..{(-min(h for _, h in hit) - 21) if synth else -min(h for _, h in hit):.0f} deg')
    return nfix, report


if __name__ == '__main__':
    n, rep = fix(sys.argv[1], apply='--apply' in sys.argv)
    for line in rep: print(line)
    print('files', n)
