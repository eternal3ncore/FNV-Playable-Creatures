"""Mirelurk block guard: both pincers raised before its face, as the human unarmed block holds the forearms up before
the face, on the mirelurk's own proportions (long arms from shoulders level with its head, pincer claws). Its unarmed
aim (h2haim, the fighting stance) plays as is - body, legs, side legs and its breathing; each arm is re-solved every
frame by 2-bone IK: the wrist GUARD_FWD in front of the head, GUARD_SIDE to its side, GUARD_UP above / below the head,
the elbow out and down (pole), the pincer turned to point up and in across the face (CLAW_DIR). Writes <folder>/_guard.kf
and <folder>/sneak_guard.kf (it sneaks in its standing gait), the source own_block.py --src _guard turns into the
BlockIdle / BlockHit files; assemble_mirelurk.py removes them after.
usage: python3 mirelurk_guard.py <Mirelurk folder>"""
import os, sys, importlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval
from rig import Creature, Rig, write_kf, align

GUARD_FWD, GUARD_SIDE, GUARD_UP = 26.0, 15.0, -6.0
POLE = (60.0, -5.0, -35.0)                 # elbow pole from the shoulder: out, back, down
CLAW_DIR = (-0.3, 0.25, 1.0)                # pincer direction (right claw; mirrored for the left): up, a little in and forward

cfg = importlib.import_module('creatures.mirelurk')
cr = Creature(cfg); sk = cr.sk
D = sys.argv[1]
aim = KFEval(os.path.join(cfg.ANIM_SRC, 'h2haim.kf'))
L = aim.stop; n = int(round(L * 30)) + 1


def full(sample):
    out = {}
    for nm in sk.order:
        t, R, _ = sk.local[nm]
        if nm in sample:
            if sample[nm][0] is not None: t = sample[nm][0]
            if sample[nm][1] is not None: R = sample[nm][1]
        out[nm] = (np.array(t, float), np.array(R, float))
    out['Bip01'] = (np.zeros(3), np.eye(3))
    return out


rig = Rig(cr, base_kf='h2haim.kf')
frames = []
for i in range(n):
    t = L * i / (n - 1)
    loc = full(aim.sample(t)); W = sk.fk(loc)
    B = W['Bip01 NonAccum'][1]
    fwd = W['Bip01 Head'][0] - W['Bip01 Pelvis'][0]; fwd[2] = 0; fwd /= np.linalg.norm(fwd)
    up = np.array([0, 0, 1.0]); right = np.cross(fwd, up)
    head = W['Bip01 Head'][0]
    for side, sgn in (('R', 1.0), ('L', -1.0)):
        _, ua, fa, hand = cr.arm[side]
        target = head + fwd * GUARD_FWD + right * (sgn * GUARD_SIDE) + up * GUARD_UP
        pole = W[ua][0] + right * (sgn * POLE[0]) + fwd * POLE[1] + up * POLE[2]
        rig.ik(loc, side, target, np.asarray(sk.local[hand][0], float), pole)
        W = sk.fk(loc)
        claw_local = np.asarray(sk.local[f'Bip01 {side} Finger0'][0], float)        # pincer direction in the hand frame
        cur = W[hand][1] @ (claw_local / np.linalg.norm(claw_local))
        want = right * (sgn * CLAW_DIR[0]) + fwd * CLAW_DIR[1] + up * CLAW_DIR[2]; want /= np.linalg.norm(want)
        rig.set_world_rot(loc, W, hand, align(cur, want) @ W[hand][1])
        W = sk.fk(loc)
    frames.append((t, loc))
bones = [(b[0], b[2]) for b in aim.blocks if b[0] != 'Bip01']
for fn in ('_guard.kf', 'sneak_guard.kf'):
    write_kf(cr, os.path.join(D, fn), 'Aim', L, [(0.0, 'start'), (L, 'end')], frames, bones=bones, cycle=aim.cycle)
W = sk.fk(frames[0][1])
print('guard: wrists R', np.round(W['Bip01 R Hand'][0], 1), 'L', np.round(W['Bip01 L Hand'][0], 1), 'head', np.round(W['Bip01 Head'][0], 1),
      'claw tips R', np.round(W['Bip01 R Finger0'][0], 1), 'L', np.round(W['Bip01 L Finger0'][0], 1))
