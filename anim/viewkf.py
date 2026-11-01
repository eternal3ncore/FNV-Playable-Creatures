import sys, numpy as np
sys.path.insert(0, '/home/claude/fnv/anim')
from rig import Creature
from kf import KFEval
import importlib
cfg = importlib.import_module('creatures.zetan'); cr = Creature(cfg)
import strip as S
S.SK = cr.sk
class R:
    def fk(self, loc):
        W = {}
        for nm in cr.sk.order:
            t, Rm = loc[nm]; p = cr.sk.parent[nm]
            if p is None: W[nm] = (t.copy(), Rm.copy())
            else: pp, pR = W[p]; W[nm] = (pp + pR @ t, pR @ Rm)
        return W
def loc_at(k, t, base=None):
    smp = k.sample(t); loc = {}
    for nm in cr.sk.order:
        tt, Rm, _ = cr.sk.local[nm]
        if base and nm in base: tt, Rm = base[nm]
        if nm in smp:
            if smp[nm][0] is not None: tt = smp[nm][0]
            if smp[nm][1] is not None: Rm = smp[nm][1]
        loc[nm] = (np.array(tt, float), np.array(Rm, float))
    return loc
def view(path, out, n=6, gun=(-4, 30), base_kf=None):
    k = KFEval(path)
    base = None
    if base_kf:
        b = KFEval(cr.path(base_kf)); base = {nm: v for nm, v in loc_at(b, 0).items()}
    ts = np.linspace(0, k.stop, n)
    S.strip(R(), [('%s %.2f' % (path.split('/')[-1][:-3], t), loc_at(k, t, base)) for t in ts], out, gunlen=gun)
if __name__ == '__main__':
    view(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6)
