"""Mirelurk locomotion completion: backward run (its run reversed) and side runs (loco2 crab runs from its run), as
gen_loco_ttw.py, without its crouched sneak - the mirelurk sneaks in its standing gait (assemble_mirelurk.py copies
the standing movement files as the sneak ones): crouching drops the body onto its four side legs (Bip01 Ponytail*,
under Spine1), which the leg IK doesn't reach.
usage: python3 loco_mirelurk.py <out dir>"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_loco_ttw as G, loco2
from rig import Creature, write_kf
cfg = importlib.import_module('creatures.mirelurk'); cr = Creature(cfg)
out = os.path.join(sys.argv[1], 'Locomotion'); os.makedirs(out, exist_ok=True)
fr, bones, L, keys, cyc, name = G.reverse_frames(cr, 'locomotion/mtfastforward.kf')
write_kf(cr, os.path.join(out, 'mtfastbackward.kf'), name, L, keys, fr, bones=bones, cycle=cyc); print('mtfastbackward', round(L, 2))
for side in 'LR':
    fr, bones, L, keys, cyc, name = loco2.crab_frames(cr, 'locomotion/mtfastforward.kf', side)
    fn = f'mtfast{"left" if side == "L" else "right"}.kf'
    write_kf(cr, os.path.join(out, fn), name, L, keys, fr, bones=bones, cycle=cyc); print(fn, name, round(L, 2))
