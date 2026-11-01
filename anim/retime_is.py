"""retime_is.py: an aimed (IS) attack that is shorter than the hip
attack of the same group (the hip one is the creature's own, the IS one generated: Super Mutant / Nightkin 2HR Attack3
and 2HL AttackRight, Swampfolk 2HR Attack3, Zetan 1HP Attack3) is time-warped onto the hip file's timing, in place:
  [0, IS Hit] -> [0, hip Hit], [IS Hit, IS end] -> [hip Hit, hip end] - every key of every interpolator data block
  (body bones and weapon parts alike) is moved, the raised aim pose is kept, the recoil / recovery plays slower;
  stop time, cycle and text keys (sounds, Eject, a:, BlendIn) = the hip file's. Fire rate aimed = hip.
usage: python3 -P retime_is.py <race folder> [--dry]   (pairs (sneak)<type>attack<g>is(up|down).kf with the hip file)"""
import os, re, struct, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))); sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy
from holster_fix import KFFile
from kf import KF, KFEval
import weaponparts as WP
from robotlib import set_meta

def hit(tks):
    for want in ('hit', 'release'):
        h = [t for t, v in tks if v.strip().lower() == want]
        if h: return h[0]
    return None

def retime(is_path, hip_path):
    a = KF(is_path); b = KF(hip_path)
    Li, Lh = a.stop - a.start, b.stop - b.start
    if Li >= Lh - 0.05: return None
    hi, hh = hit(a.textkeys), hit(b.textkeys)
    if hi is None or hh is None: hi = hh = 0.0
    def f(t):
        if t <= hi: return t * (hh / hi) if hi > 0 else t
        return hh + (t - hi) * (Lh - hh) / max(Li - hi, 1e-6)
    assert abs(a.start) < 1e-6, is_path
    kf = KFFile(is_path); fl = kf.f; n = 0; nb0 = len(fl.blocks)
    if any(fl.types[ti].startswith('NiBSpline') for ti in fl.btype):
        # B-spline (compressed) curves can't be key-shifted: every transform channel is resampled at 30 fps through
        # the inverse map onto linear keys (KFEval evaluates the splines)
        ev = KFEval(is_path); inv = lambda u: (u * hi / hh if u <= hh else hi + (u - hh) * (Li - hi) / max(Lh - hh, 1e-6)) if hh > 0 else (u * Li / Lh)
        N = max(2, int(round(Lh * 30)) + 1); ts = [Lh * j / (N - 1) for j in range(N)]
        smp = [ev.sample(a.start + inv(u)) for u in ts]
        for _, nm in kf.cb:
            if nm is None or nm not in smp[0]: continue
            tr0, R0 = smp[0][nm]
            if tr0 is None or R0 is None: continue
            kf.set_channel(nm, [(u, numpy.array(s[nm][0], float), numpy.array(s[nm][1], float)) for u, s in zip(ts, smp)]); n += 1
    for i, ti in enumerate(fl.btype[:nb0]):                  # key-based data (all of it, or the non-spline rest; not the new linear blocks)
        tn = fl.types[ti]
        if tn in ('NiTransformData', 'NiKeyframeData', 'NiFloatData', 'NiBoolData', 'NiPosData'):
            fl.blocks[i] = WP._remap_data(tn, fl.blocks[i], f); n += 1
    set_meta(kf, length=Lh, cycle=b.cycle, textkeys=list(b.textkeys))
    kf.save(is_path)
    return Li, Lh, n

if __name__ == '__main__':
    d = sys.argv[1]; dry = '--dry' in sys.argv
    files = {x.lower(): x for x in os.listdir(d)}
    for fl, f in sorted(files.items()):
        m = re.match(r'^(.*attack.*?)is(up|down)?\.kf$', fl)
        if not m: continue
        hip = files.get(m.group(1) + (m.group(2) or '') + '.kf')
        if not hip: continue
        a = KF(os.path.join(d, f)); b = KF(os.path.join(d, hip))
        if (a.stop - a.start) >= (b.stop - b.start) - 0.05: continue
        if dry: print('would retime', f, '%.2f -> %.2f' % (a.stop - a.start, b.stop - b.start)); continue
        r = retime(os.path.join(d, f), os.path.join(d, hip))
        print('retimed %-28s %.2f -> %.2f s (%d data blocks)' % (f, r[0], r[1], r[2]))
