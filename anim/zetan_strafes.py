"""Zetan strafes. The Zetan (both races) has its own
walk / run / backward and sneak versions but no Left / Right / FastLeft / FastRight / FastBackward (only H2H-prefixed
sidesteps, used with fists out): the log showed 'creature has no group 0005/0006/0008/0009/000A' (+ sneak 1005...) and
the player stood still while strafing. Made from its own locomotion (loco2.crab_frames: root travel turned 90 deg,
lower body yawed 70 deg toward the motion, spine twisted back so the upper body faces ahead - as the ghoul / super
mutant fast strafes):
    Left / Right          <- its walk (Locomotion\\forwardwalk.kf)          sneak: <- sneakforwardwalk.kf
    FastLeft / FastRight  <- its run (Locomotion\\fastforward.kf)           sneak: <- sneakfastforward.kf
    FastBackward          <- its backward at twice the speed               sneak: <- sneakbackward.kf, same
usage: python3 -P zetan_strafes.py <out dir>"""
import importlib, os, sys
import numpy as np
sys.path.insert(0, '/home/claude/fnv/anim')
from rig import Creature, write_kf
from kf import KF, KFEval
import loco2
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
cr = Creature(importlib.import_module('creatures.zetan'))
made = []
for src, pre, base in (('locomotion/forwardwalk.kf', '', ''), ('locomotion/fastforward.kf', '', 'fast'),
                       ('sneakforwardwalk.kf', 'sneak', ''), ('sneakfastforward.kf', 'sneak', 'fast')):
    for side in 'LR':
        fr, bones, L, keys, cyc, name = loco2.crab_frames(cr, src, side)
        name = ('Fast' if base else '') + ('Left' if side == 'L' else 'Right')
        f = f'{pre}mt{base}{"left" if side == "L" else "right"}.kf'
        write_kf(cr, os.path.join(out, f), name, L, keys, fr, bones=bones, cycle=cyc); made.append((f, name, round(L, 2)))
# FastBackward: its backward, sampled at twice the speed (same distance per cycle in half the time)
for src, f in (('backward.kf', 'mtfastbackward.kf'), ('sneakbackward.kf', 'sneakmtfastbackward.kf')):
    k = KFEval(cr.path(src)); L = k.stop / 2; n = int(round(L * 30)) + 1
    bones = loco2._bones(cr, k)
    frames = []
    for i in range(n):
        t = L * i / (n - 1); frames.append((t, loco2._sample(cr, k, min(2 * t, k.stop))))
    keys = [(t / 2, v) for t, v in KF(cr.path(src)).textkeys]
    write_kf(cr, os.path.join(out, f), 'FastBackward', L, keys, frames, bones=bones, cycle=k.cycle); made.append((f, 'FastBackward', round(L, 2)))
for m in made: print(*m)
