"""Locomotion completion for the TTW creature races (swampfolk, trogs).
usage: python3 gen_loco_ttw.py <cfg> <out dir> <sneak: human|crouch> [human sneak dir]
  Locomotion/mtfastbackward.kf : the creature's own run (FastForward) played in reverse (root motion reversed, so it
                                 travels backward at the run speed; footstep keys mirrored in time). The creatures have
                                 no backward run: the engine would play the walk backward at ~4-5x speed.
  Locomotion/mtfastleft/right  : crab run from its own run (loco2.crab_frames), as for the ghoul / super mutant.
  sneak 'human' : vanilla human sneak locomotion retargeted (sneak_human.py creature neck/head and arm carriage)
  sneak 'crouch': the creature's own idle / locomotion crouched with leg IK (loco2.crouch_frames) - for the trog,
                  which moves on all fours (a human sneak would stand it up)."""
import sys, os, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kf import KFEval
from rig import Creature, write_kf
import loco2

def reverse_frames(cr, src, fps=30):
    sk = cr.sk; acc = cr.cfg.ACCUM_ROOT
    k = KFEval(cr.path(src)); L = k.stop; n = max(2, int(round(L * fps)) + 1)
    end = loco2._sample(cr, k, L)[acc][0]
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        loc = loco2._sample(cr, k, L - t)
        at, aR = loc[acc]; loc[acc] = (at - end, aR)
        frames.append((t, loc))
    keys = []
    for t, s in k.textkeys:
        if s.lower() in ('start', 'end'): keys.append((t, s))
        else: keys.append((L - t, s))
    keys.sort(key=lambda x: x[0])
    return frames, loco2._bones(cr, k), L, keys, k.cycle, 'FastBackward'

def build(cfgname, out, mode, hsneak=None):
    cfg = importlib.import_module('creatures.' + cfgname); cr = Creature(cfg)
    loc_dir = os.path.join(out, 'Locomotion'); os.makedirs(loc_dir, exist_ok=True)
    done = []
    fr, bones, L, keys, cyc, name = reverse_frames(cr, 'locomotion/mtfastforward.kf')
    p = os.path.join(loc_dir, 'mtfastbackward.kf'); write_kf(cr, p, name, L, keys, fr, bones=bones, cycle=cyc)
    cr.extra['locomotion/mtfastbackward.kf'] = p; done.append(('Locomotion/mtfastbackward.kf', name, round(L, 2)))
    for side in 'LR':
        fr, bones, L, keys, cyc, name = loco2.crab_frames(cr, 'locomotion/mtfastforward.kf', side)
        fn = f'mtfast{"left" if side == "L" else "right"}.kf'; p = os.path.join(loc_dir, fn)
        write_kf(cr, p, name, L, keys, fr, bones=bones, cycle=cyc)
        cr.extra['locomotion/' + fn] = p; done.append(('Locomotion/' + fn, name, round(L, 2)))
    if mode == 'human':
        import sneak_human as SH
        for fn, nm, L, lh, ex in SH.build(cfgname, hsneak, out): done.append((fn, nm, L))
    else:
        jobs = [('mtidle.kf', 'sneakmtidle.kf')] + [(f'locomotion/mt{g}.kf', f'sneakmt{g}.kf') for g in
                ('forward', 'backward', 'left', 'right', 'turnleft', 'turnright', 'fastforward', 'fastbackward', 'fastleft', 'fastright')]
        for src, dst in jobs:
            fr, bones, L, keys, cyc, name = loco2.crouch_frames(cr, src, drop=getattr(cfg, 'SNEAK_DROP', 0.15), lean=getattr(cfg, 'SNEAK_LEAN', 0.0))
            write_kf(cr, os.path.join(out, dst), name, L, keys, fr, bones=bones, cycle=cyc); done.append((dst, name, round(L, 2)))
    return done

if __name__ == '__main__':
    for d in build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None): print(d)
