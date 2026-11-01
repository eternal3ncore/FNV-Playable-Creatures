"""Trog jumps from its own leap (DLCPitt StreetTrog IdleAnims\\specialidle_jumphorizontal384.kf): the procedural jumps
folded its sideways-hanging legs about the wrong axis (audit: foot twist ~140 deg on landing).
  JumpLoop*  : the leap's airborne tuck (t = 0.35), held, hip node 'Bip' at its idle height (the jump height is physics)
  JumpLand*  : that tuck blending into its own idle (first 45 % of the landing, smoothstep), then the idle
Every existing jump file (and sneak copy) keeps its length, text keys and cycle. The accum root is not keyed.
usage: python3 trog_jumps.py <cfg> <deployed folder> <own leap kf>"""
import sys, os, re, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KF, KFEval, m2q, q2m
from rig import Creature, write_kf
import retarget_idle as RI
cfg = importlib.import_module('creatures.' + sys.argv[1]); cr = Creature(cfg); folder = sys.argv[2]
leap = KFEval(sys.argv[3]); idle = KFEval(os.path.join(folder, 'mtidle.kf'))
ACC = cfg.ACCUM_ROOT
bones = [nm for nm, _, _ in leap.blocks if nm in cr.sk.local and nm != ACC]
def pose(k, t):
    s = k.sample(t); out = {}
    for nm in cr.sk.order:
        tt, R, _ = cr.sk.local[nm]
        if nm in s:
            if s[nm][0] is not None: tt = s[nm][0]
            if s[nm][1] is not None: R = s[nm][1]
        out[nm] = (np.array(tt, float), np.array(R, float))
    out[ACC] = (np.zeros(3), np.eye(3))
    return out
idle0 = pose(idle, 0.0)
tuck = pose(leap, 0.35); tuck['Bip'] = (idle0['Bip'][0].copy(), tuck['Bip'][1])
def blend(a, b, u):
    return {nm: (a[nm][0] + (b[nm][0] - a[nm][0]) * u, q2m(RI.slerp(m2q(a[nm][1]), m2q(b[nm][1]), u))) for nm in a}
n = 0
for fn in sorted(os.listdir(folder)):
    m = re.match(r'^(sneak)?mtjump(loop|land)\w*\.kf$', fn.lower())
    if not m: continue
    k = KF(os.path.join(folder, fn)); L = k.stop; nf = max(2, int(round(L * 30)) + 1); frames = []
    for i in range(nf):
        t = L * i / (nf - 1)
        if m.group(2) == 'loop': frames.append((t, tuck))
        else:
            u = min(1.0, (t / L) / 0.45); u = u * u * (3 - 2 * u)
            frames.append((t, blend(tuck, pose(idle, t % idle.stop), u)))
    write_kf(cr, os.path.join(folder, fn), k.name, L, list(k.textkeys), frames, bones=[(nm, 30) for nm in bones], cycle=k.cycle)
    n += 1
print(n, 'trog jump files from its own leap')
