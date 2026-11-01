"""Furniture animations for the trog race (The Pitt street trog: crouched, on all fours; its bind pose is not a human
standing pose, so the retargeted human sitting of retarget_idle_creature.py turns it into a tangle).
The trog keeps its own crouched idle (looping) and, following the human file, walks the human entry path (accum root
Bip01, copied unscaled - the furniture marker sets it), turns with the human's yaw, and hops up to crouch ON the seat:
its NonAccum is raised by the seat surface height as the human's hips go from standing (67.4) to seated (chair 36.85,
bar stool 54.55); surface = seated hip height - 6. Text keys / lengths / cycles / priorities = the human files', so
the furniture timing is vanilla. Seated loops and relax specials = its idle on the seat.
usage: python3 trog_furniture.py <cfg> <out_dir>"""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval
from rig import Creature, write_kf, rotm
import retarget_idle_creature as RC

HUMAN_SIT = RC.HUMAN_SIT
STAND = 67.4

def yaw(R): return np.degrees(np.arctan2(R[1, 0], R[0, 0]))

def build(cfgname, out_dir, fps=30):
    cfg = importlib.import_module('creatures.' + cfgname); cr = Creature(cfg); sk = cr.sk
    ki = KFEval(cr.path(cfg.IDLE_KF)); Li = ki.stop
    idle_bones = [nm for nm, _, _ in ki.blocks if nm in sk.local]
    NA = 'Bip01 NonAccum'; ACC = cfg.ACCUM_ROOT
    os.makedirs(out_dir, exist_ok=True); rep = []
    for out, src, _ in RC.JOBS:
        k = KFEval(HUMAN_SIT + src); L = k.stop; n = int(round(L * fps)) + 1
        keyed = {b[0] for b in k.blocks}; prio = max(b[2] for b in k.blocks)
        stool = 'stool' in src.lower(); zseat = 54.55 if stool else 36.85
        frames = []
        for i in range(n):
            t = L * i / (n - 1); hsmp = k.sample(t)
            isp = ki.sample(t % Li if Li > 0 else 0)
            loc = {}
            for nm in sk.order:
                tt, R, _ = sk.local[nm]
                if nm in isp:
                    if isp[nm][0] is not None: tt = isp[nm][0]
                    if isp[nm][1] is not None: R = isp[nm][1]
                loc[nm] = (np.array(tt, float), np.array(R, float))
            acc = hsmp.get('Bip01')
            at = np.array(acc[0], float) if acc and acc[0] is not None else np.zeros(3)
            aR = np.array(acc[1], float) if acc and acc[1] is not None else np.eye(3)
            loc[ACC] = (at, aR)
            hna = hsmp[NA]; zh = float(hna[0][2]); dyaw = yaw(np.array(hna[1], float)) - 90.0
            off = float(np.clip((STAND - zh) / (STAND - zseat), 0.0, 1.0)) * (zseat - 6.0)
            nt, nR = loc[NA]
            loc[NA] = (nt + np.array([hna[0][0], hna[0][1], off]), rotm((0, 0, 1), dyaw) @ nR)
            frames.append((t, loc))
        names = [nm for nm in sk.order if nm in idle_bones or nm == NA or (nm == ACC and 'Bip01' in keyed)]
        write_kf(cr, os.path.join(out_dir, out), k.name, L, list(k.textkeys), frames, bones=[(nm, prio) for nm in names], cycle=k.cycle)
        rep.append((out, k.name, round(L, 2), k.cycle, prio, len(names), 'stool' if stool else 'chair'))
    return rep

if __name__ == '__main__':
    for r in build(sys.argv[1], sys.argv[2]): print(r)
