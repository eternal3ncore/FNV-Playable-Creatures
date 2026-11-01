"""Retarget the human furniture idle set (chair enter/exit x4 sides, seated loop + relax specials, stool) onto a
creature-race skeleton (Feral Ghoul, Super Mutant, ...). Generic version of retarget_idle.py (Zetan).

Same method as retarget_idle.py (world-space bone deltas, Bip01 entry path unscaled because the furniture marker sets
it, NonAccum height mapped seat->seat / stand->stand, 2-bone leg IK with ground contact). Creatures without a seated
pose of their own use the retargeted human seated loop and relax specials, so no seat blend is needed.
  stand height = the creature's own NonAccum height in its idle (accum root at the origin)
  seat height  = human seat + 25 % of the stand-height difference (a bigger body sits a little higher)
usage: python3 retarget_idle_creature.py <creature cfg> <skeleton.nif (with stand-ins)> <out_dir>"""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval
from rig import Creature, write_kf
import retarget_idle as RI

HUMAN_SIT = '/home/claude/fnv/human_sit/meshes/characters/_male/idleanims/'
JOBS = [(o, s, None) for o, s, _ in RI.JOBS] + [
    ('DynamicIdle_ChairSit.kf', 'dynamicidle_chairsit.kf', None),
    ('SitChairRelaxA.kf', 'sitchairrelaxa.kf', None),
    ('SitChairRelaxB.kf', 'sitchairrelaxb.kf', None),
    ('SitChairRelaxC.kf', 'sitchairrelaxc.kf', None)]

def stand_height(cfg):
    k = KFEval(os.path.join(cfg.ANIM_SRC, cfg.IDLE_KF)); p = k.sample(0.0)
    return float(p['Bip01 NonAccum'][0][2])

def build(cfgname, skel, out_dir, fps=30):
    cfg = importlib.import_module('creatures.' + cfgname)
    cr = Creature(cfg)
    hz = stand_height(cfg)
    hs, _ = RI.Z_SEAT[0], None
    RI.Z_STAND = (RI.Z_STAND[0], hz)
    # cfg.SIT_SEAT_OFFSET overrides the seat offset: a crouched creature (trog, idle NonAccum 20) sits at the
    # human seat height instead of 25 % of its (negative) stand difference below it
    RI.Z_SEAT = (RI.Z_SEAT[0], RI.Z_SEAT[0] + getattr(cfg, 'SIT_SEAT_OFFSET', 0.25 * (hz - RI.Z_STAND[0])))
    rt = RI.IdleRetarget(RI.HUMAN_SKEL, skel)
    # piecewise height map: chair seat and bar-stool seat keep their world height (+ the creature's seat offset),
    # standing maps to the creature's own standing height
    (hs, zs), (hS, zS) = RI.Z_SEAT, RI.Z_STAND
    H_STOOL = 54.55                                  # human NonAccum height on a bar stool (dynamicidle_sitstool)
    pts = [(hs, zs), (H_STOOL, H_STOOL + (zs - hs)), (hS, zS)]
    def map_z(z):
        if z <= pts[0][0]: return z + (zs - hs)
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            if z <= a1: return b0 + (z - a0) * (b1 - b0) / (a1 - a0)
        return z + (zS - hS)
    rt.map_z = map_z
    os.makedirs(out_dir, exist_ok=True)
    rep = []
    for out, src, _ in JOBS:
        k = KFEval(HUMAN_SIT + src); L = k.stop; n = int(round(L * fps)) + 1
        keyed = {b[0] for b in k.blocks}
        prio = max(b[2] for b in k.blocks)
        frames = [(L * i / (n - 1), rt.frame(k, L * i / (n - 1))) for i in range(n)]
        names = [nm for nm in rt.hs.order if nm.startswith('Bip01') and (nm in ('Bip01', 'Bip01 NonAccum') or rt.map.get(nm) in keyed)]
        if 'Bip01' not in keyed: names = [nm for nm in names if nm != 'Bip01']
        write_kf(cr, os.path.join(out_dir, out), k.name, L, RI.keys_of(k), frames, bones=[(nm, prio) for nm in names], cycle=k.cycle)
        rep.append((out, k.name, round(L, 2), k.cycle, prio, len(names)))
    return rt, rep, RI.Z_SEAT, RI.Z_STAND

if __name__ == '__main__':
    rt, rep, zs, zt = build(sys.argv[1], sys.argv[2], sys.argv[3])
    print('leg ratio %.3f ankle src %.2f dst %.2f seat %s stand %s' % (rt.ratio, rt.ankle_g, rt.ankle_h, zs, zt))
    for r in rep: print(r)
