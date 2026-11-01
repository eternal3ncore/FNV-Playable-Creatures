"""Regenerates the procedural throws (AttackThrow..AttackThrow8 x plain/Up/Down/IS...) of a race without an own throw,
with an overhand throw: hand up beside the head (elbow bent, out to the side), forward release at head height, follow
through down across the body. build_creature's default wind-up put a straight arm behind the body with the wrist bent
back ~170 deg (audit). Each existing file keeps its own length / text keys / cycle (vanilla human timing:
Hold, Release, Attach, sounds); the hold base is the race's deployed 1HP aim of the same variant (as build_creature).
Run hinge_fix.py and wrist_relax.py afterwards. usage: python3 regen_throws.py <cfg> <deployed folder> [scale]"""
import sys, os, re, shutil, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KF
from rig import Creature, Rig, sample, write_kf
import motions as M
import weaponparts as WP
SUF = ['', 'up', 'down', 'is', 'isup', 'isdown']
def keyt(ks, name, L, d):
    for t, s in ks:
        if s.lower() == name.lower(): return t / L
    return d
def run(cfgname, folder, S=1.0):
    cfg = importlib.import_module('creatures.' + cfgname)
    sc = lambda v: tuple(round(x * S, 2) for x in v)
    # wind-up at ear height, not above the head: the creatures' own animations never raise the upper arm that far
    cfg.THROW = dict(wind=dict(wpos=sc((12, -14, 18)), pitch=30, lean=-6, twist=22, head=-5),
                     rel=dict(wpos=sc((8, 26, 16)), pitch=0, lean=12, twist=-12, head=5),
                     follow=dict(wpos=sc((-10, 30, -12)), pitch=-25, lean=16, twist=-18, head=8))
    cr = Creature(cfg); REF = getattr(cfg, 'HUMAN_REF', '/home/claude/fnv/ref_male'); refs = set(os.listdir(REF))
    rigs = {}; done = []
    for fn in sorted(os.listdir(folder)):
        m = re.match(r'^1gtattackthrow(\d?)(up|down|is|isup|isdown)?\.kf$', fn.lower())
        if not m: continue
        suf = m.group(2) or ''
        base = os.path.join(folder, f'1hpaim{suf}.kf')
        if not os.path.exists(base): base = os.path.join(folder, f'1hpaim{suf.replace("is", "")}.kf')   # Zetan: no IS aims
        if base not in rigs: rigs[base] = Rig(cr, base)
        k = KF(os.path.join(folder, fn)); L = k.stop; ks = list(k.textkeys)
        plan = M.throw(cfg, keyt(ks, 'Hold', L, .33), keyt(ks, 'Release', L, .51))
        p = os.path.join(folder, fn)
        write_kf(cr, p, k.name, L, ks, sample(rigs[base], plan, L), priority=65, cycle=k.cycle)
        src = next((c for c in (fn.lower(), '1gtaim.kf') if c in refs), None)
        if src: WP.merge(p, os.path.join(REF, src), keep_loose_transforms=True)
        shutil.copyfile(p, os.path.join(folder, 'sneak' + fn))
        done.append(fn)
    return done
if __name__ == '__main__':
    d = run(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
    print(len(d), 'throws regenerated (+ sneak copies)')
