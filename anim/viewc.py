import sys, importlib, numpy as np
sys.path.insert(0, '/home/claude/fnv/anim')
from rig import Creature, Rig
from kf import KFEval
import strip as S
def viewer(cfgname):
    cfg = importlib.import_module('creatures.' + cfgname); cr = Creature(cfg); S.SK = cr.sk
    def frames(path, n):
        k = KFEval(path); out = []
        for t in np.linspace(0, k.stop, n):
            r = Rig(cr, base_pose=k.sample(t)); out.append(('%s %.2f' % (path.split('/')[-1][:-3], t), r.base, r))
        return out
    return cr, frames
def show(cfgname, files, out, n=1, gun=(-4, 30), ylim=(-10, 130)):
    cr, frames = viewer(cfgname); S.YLIM = ylim
    fr = []
    for f in files: fr += frames(f, n)
    S.strip(fr[0][2], [(a, b) for a, b, _ in fr], out, gunlen=gun)
