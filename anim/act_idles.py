"""The player's action idles for a creature skeleton folder (PlayableCreatures\\<folder>\\IdleAnims): the engine plays them
from the actor's own idle tree (ActivateIdles / StartCannibal of the vanilla human tree) and the action waits for them -
with none the activation does nothing (drinking from a water source only played the activate sound).
  ActWaterSource.kf   drinking from a water source: bends down by WATER deg over its trunk / neck chain, holds (the
                      human file's StartLoop / EndLoop) with a small bob, comes back up; the human file's name, length,
                      cycle and text keys (drinking sounds)
  Cannibal.kf         Cannibal perk: bends lower (CANNIBAL deg) and feeds with a slow bob; the human file's timing and its
                      'Sound: NPCHumanPerkCannibal'
  Stimpak.kf          using a stimpak (ActStimpakSource): looks down (STIM deg) and back; the human file's timing
  (Cannibal.kf is then replaced by cannibal.py's per-race feeding animation; Ghost gets the vanilla Sandman files)
  SandManBedLeft.kf / SandManBedRight.kf / SandManFlrLeft.kf / SandManFlrRight.kf   the Mister Sandman kill (the
                      engine's StartMisterSandman, FurnitureIdles > Sleeping > SandMan / SandManFloor by the victim's
                      bed marker): leans over the sleeper (bed WATER x 0.6 deg, floor WATER deg) and strikes with the
                      creature's own standing power attack (h2hattackpower.kf), its Hit on the human file's
                      'Sound: NPCHumanPerkMrSandman' (the kill), then straightens; the attack's own Sound keys shifted
Each keeps the creature's own idle (its mtidle.kf, looped) for every bone the idle keys; the bend is spread evenly over
the bones from the trunk up to Bip01 Head (the root, NonAccum and pelvis excluded), about the actor's sideways axis.
Bip01 is not keyed (the locomotion keeps its heading). Priority 45.
usage: python3 act_idles.py <race folder with mtidle.kf> <Skeleton.nif> <out IdleAnims dir> [water cannibal stim deg]"""
import os, shutil, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KF, KFEval, Skeleton, slerp, m2q, q2m
import rig

REF = '/home/claude/fnv/ref_act'
HUMAN = {'ActWaterSource.kf': 'actwatersource.kf', 'Cannibal.kf': '3rdp_cannibal.kf', 'Stimpak.kf': '3rdp_specialidle_stempak.kf'}
SANDMAN = {'SandManBedLeft.kf': ('sandmanbedleft.kf', 0.6), 'SandManBedRight.kf': ('sandmanbedright.kf', 0.6),
           'SandManFlrLeft.kf': ('sandmanflrleft.kf', 1.0), 'SandManFlrRight.kf': ('sandmanflrright.kf', 1.0)}
PRIO = 45


def rotx(a):
    c, s = np.cos(a), np.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


class _Cfg: pass


class Shim:
    """what rig.write_kf needs of a Creature"""
    def __init__(s, skel, template):
        s.sk = Skeleton(skel); s.cfg = _Cfg(); s.cfg.TEMPLATE_KF = template; s.cfg.ACCUM_ROOT = 'Bip01'; s.upper = []
    def path(s, f): return f


def wrot(sk, loc, n):
    """world rotation of n along its parent chain (skeletons with grafted duplicate names break the full FK)"""
    R = np.eye(3)
    while n is not None:
        R = loc[n][1] @ R if n in loc else sk.local[n][1] @ R; n = sk.parent.get(n)
    return R


def chain_of(sk):
    if 'Bip01 Head' not in sk.local: return ['Bip01 NonAccum']
    out = []; n = 'Bip01 Head'
    while n and n not in ('Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis', 'Scene Root'):
        out.append(n); n = sk.parent.get(n)
    return out[::-1]


def profile(name, t, L, tk):
    """bend fraction 0..1 at time t"""
    def ease(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
    keys = {v.split(':')[0].strip().lower(): tt for tt, v in tk}
    if name == 'ActWaterSource.kf':
        a, b = keys.get('startloop', 0.37), keys.get('endloop', 1.37); c = L - 0.5
        if t < a: return ease(t / a)
        if t < b: return 1.0 - 0.08 * np.sin(np.pi * 2 * (t - a) / (b - a))
        return 1.0 - ease((t - b) / max(c - b, 0.1))
    a, c = 0.8, L - 0.8
    if t < a: return ease(t / a)
    if t < c: return 1.0 - (0.1 * (0.5 - 0.5 * np.cos(np.pi * 2 * (t - a) / 1.2)) if name == 'Cannibal.kf' else 0.0)
    return 1.0 - ease((t - c) / 0.8)


def build(folder, skel, out, deg):
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    idle = KFEval(os.path.join(folder, 'mtidle.kf'))
    keyed = [b[0] for b in idle.blocks if b[0] not in ('Bip01',)]
    ch = chain_of(sk)
    os.makedirs(out, exist_ok=True)
    for name, hf in HUMAN.items():
        h = KF(os.path.join(REF, hf)); L = h.stop; n = int(round(L * 30)) + 1
        frames = []
        for i in range(n):
            t = L * i / (n - 1); s = idle.sample(t % idle.stop); loc = {}
            for nm in sk.order:
                tr, R, _ = sk.local[nm]
                if nm in s:
                    if s[nm][0] is not None: tr = s[nm][0]
                    if s[nm][1] is not None: R = s[nm][1]
                loc[nm] = (np.array(tr, float), np.array(R, float))
            if not (s.get('Bip01') and s['Bip01'][1] is not None):
                loc['Bip01'] = (loc['Bip01'][0], np.eye(3))       # the heading the locomotion keys (forward +Y)
            a = np.radians(deg[name]) * profile(name, t, L, h.textkeys) / len(ch)
            for nm in ch:                                       # pitch each down about the actor's sideways axis
                pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
                loc[nm] = (loc[nm][0], pR.T @ rotx(-a) @ R)
            frames.append((t, loc))
        bones = [(b, PRIO) for b in dict.fromkeys(keyed + ch) if b in sk.local]
        rig.write_kf(cr, os.path.join(out, name), h.name, L, h.textkeys, frames, bones=bones, cycle=h.cycle)
    return ch


def ease(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def pose_at(sk, ev, t, skip=('Bip01',)):
    s = ev.sample(t); out = {}
    for nm, v in s.items():
        if nm in skip or nm not in sk.local: continue
        tr, R, _ = sk.local[nm]
        out[nm] = (np.array(v[0] if v[0] is not None else tr, float), np.array(v[1] if v[1] is not None else R, float))
    return out


def build_sandman(folder, skel, out, water_deg):
    """the kill: idle -> lean over the sleeper -> the creature's own standing power attack, Hit on the kill key"""
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    idle = KFEval(os.path.join(folder, 'mtidle.kf')); atk = KFEval(os.path.join(folder, 'h2hattackpower.kf'))
    ak = KF(os.path.join(folder, 'h2hattackpower.kf'))
    a_hit = next((t for t, v in ak.textkeys if v.strip().lower() == 'hit'), (ak.stop - ak.start) / 2)
    a_snd = [(t, v) for t, v in ak.textkeys if v.lower().startswith('sound:')]
    keyed = [b[0] for b in idle.blocks if b[0] != 'Bip01'] + [b[0] for b in atk.blocks if b[0] != 'Bip01']
    ch = chain_of(sk)
    for name, (hf, k) in SANDMAN.items():
        h = KF(os.path.join(REF, hf)); L = h.stop; n = int(round(L * 30)) + 1
        kill = next(t for t, v in h.textkeys if 'mrsandman' in v.lower())
        t0 = kill - a_hit; t1 = t0 + (atk.stop - atk.start)            # attack window (may start before 0: clamped)
        lean0, lean1 = max(0.33, t0 - 0.9), max(0.5, t0)               # lean in before the strike
        back0 = max(t1 + 0.5, L - 1.6); back1 = L - 0.25               # straighten up at the end
        deg = np.radians(water_deg * k)
        frames = []
        for i in range(n):
            t = L * i / (n - 1); s = idle.sample(t % idle.stop); loc = {}
            for nm in sk.order:
                tr, R, _ = sk.local[nm]
                if nm in s:
                    if s[nm][0] is not None: tr = s[nm][0]
                    if s[nm][1] is not None: R = s[nm][1]
                loc[nm] = (np.array(tr, float), np.array(R, float))
            if not (s.get('Bip01') and s['Bip01'][1] is not None):
                loc['Bip01'] = (loc['Bip01'][0], np.eye(3))
            # the power attack over the idle, faded in / out
            w = min(ease((t - (t0 - 0.2)) / 0.2), 1.0 - ease((t - t1) / 0.3)) if t0 - 0.2 <= t <= t1 + 0.3 else 0.0
            if w > 0:
                ap = pose_at(sk, atk, min(max(atk.start + t - t0, atk.start), atk.stop))
                for nm, (tr, R) in ap.items():
                    if nm == 'Bip01': continue
                    q = slerp(m2q(loc[nm][1]), m2q(R), w)
                    loc[nm] = (loc[nm][0] * (1 - w) + tr * w, q2m(q))
            prof = ease((t - lean0) / max(lean1 - lean0, 0.1)) * (1.0 - ease((t - back0) / max(back1 - back0, 0.1)))
            a = deg * prof / len(ch)
            for nm in ch:
                pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
                loc[nm] = (loc[nm][0], pR.T @ rotx(-a) @ R)
            frames.append((t, loc))
        tk = list(h.textkeys) + [(min(max(t + t0 - atk.start, 0.0), L), v) for t, v in a_snd]
        tk.sort(key=lambda x: x[0])
        bones = [(b, PRIO) for b in dict.fromkeys(keyed + ch) if b in sk.local]
        rig.write_kf(cr, os.path.join(out, name), h.name.split('-Global')[0], L, tk, frames, bones=bones, cycle=h.cycle)
    return ch


# bend per skeleton folder (water, cannibal, stimpak); default 60 / 80 / 20 - robots and the creatures on all fours less
DEG = {f: (25.0, 35.0, 10.0) for f in ('Eyebot', 'Protectron', 'Robobrain', 'Securitron', 'SentryBot', 'MisterHandy', 'MisterGutsy')}
DEG.update({f: (35.0, 45.0, 15.0) for f in ('Trog', 'Tunneler')})


if __name__ == '__main__':
    a = sys.argv[1:]
    deg = {'ActWaterSource.kf': 60.0, 'Cannibal.kf': 80.0, 'Stimpak.kf': 20.0}
    if len(a) > 3: deg = dict(zip(deg, map(float, a[3:6])))
    elif os.path.basename(os.path.normpath(a[0])) in DEG: deg = dict(zip(deg, DEG[os.path.basename(os.path.normpath(a[0]))]))
    print(build(a[0], a[1], a[2], deg))
    name = os.path.basename(os.path.normpath(a[0]))
    if name == 'Ghost':                       # the human skeleton: the vanilla Sandman files as they are
        for o, (hf, _) in SANDMAN.items(): shutil.copyfile(os.path.join(REF, hf), os.path.join(a[2], o))
    elif os.path.exists(os.path.join(a[0], 'h2hattackpower.kf')): build_sandman(a[0], a[1], a[2], deg['ActWaterSource.kf'])
    import cannibal                           # Cannibal.kf: the race's own feeding animation (cannibal.py)
    print(cannibal.build(name, a[0], a[2]))
