"""Re-generates only the procedural jump files of a built set (build_creature.py step 6), e.g. after a jumps.py change.
usage: python3 regen_jumps.py <cfg> <set dir>"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KF
from rig import Creature, write_kf
import jumps as J
cfg = importlib.import_module('creatures.' + sys.argv[1]); cr = Creature(cfg); OUT = sys.argv[2]
JREF = getattr(cfg, 'HUMAN_JUMP_REF', '/home/claude/fnv/ref_weap')
for g, jrig, K, cyc in J.build(cr):
    fname = f'mt{g.lower()}.kf'; rp = os.path.join(JREF, fname)
    for out in (fname, 'sneak' + fname):
        p = os.path.join(OUT, out)
        if not os.path.exists(p): continue
        hk = KF(p); L = hk.stop; ks = list(hk.textkeys)
        nf = max(2, int(round(L * 30)) + 1)
        frames = [(L * i / (nf - 1), J.jump_pose(jrig, K.at(i / (nf - 1)))) for i in range(nf)]
        write_kf(cr, p, g, L, ks, frames, bones=J.jump_bones(cr), cycle=cyc); print('rewrote', out, g, round(L, 2))
