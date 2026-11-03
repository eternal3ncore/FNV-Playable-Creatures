"""Ghost People heavy weapons (2HH: minigun, gatling laser, flamer, incinerator...) as spellcasting: the right arm
extended, palm forward, fingers open; the gun is never seen (Weapon node scale 0.001) and the shot leaves a little
in front of the palm.
Every Ghost 2HH file is rebuilt from the Ghost's matching one-handed pistol file (2hh<group> <- 1hp<group>, same
group list; sneak2hh <- sneak1hp): its body (one arm extended at shoulder height, the other free) is time-warped onto
the 2HH file's length (the 1HP 'Hit' / 'Fire' key lands on the 2HH one), the 2HH file's name, text keys, cycle and
length are kept (fire events / sounds stay the heavy weapon's). In aims and attacks the right hand is turned palm
forward (fingers along the up direction, perpendicular to the aim, thumb side toward the body - the hand's local
+X = fingers, +Z = index side, +Y = palm) and the fingers / thumb take their bind (open) pose; the Weapon node is
keyed PALM_AHEAD in front of the palm (+X = the aim direction, +Y up, +Z right, as a human gun), so the hidden gun's
projectile node - and with it the shot, its muzzle flash, a flamer's flame - is there. Reloads, jams, equips keep the
pistol file's hands (nothing seen in them). Weapon scale 0.001 everywhere.
usage: python3 -P ghost_cast.py <Ghost anim folder (1hp + 2hh files)> <out folder>"""
import os, re, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
import importlib
from kf import KFEval
from rig import Creature, write_kf
from nifedit import NifFile

PALM_AHEAD = 12.0          # shot origin in front of the palm
PALM_UP = 5.0              # palm centre along the fingers from the wrist
HIDE_SCALE = 0.001
cfg = importlib.import_module('creatures.ghost'); cr = Creature(cfg); sk = cr.sk
FINGERS = [n for n in cfg.BONES['fingers_R'] if n in sk.local]

def full(smp):
    out = {}
    for n in sk.order:
        t, R, _ = sk.local[n]
        if n in smp:
            if smp[n][0] is not None: t = smp[n][0]
            if smp[n][1] is not None: R = smp[n][1]
        out[n] = (np.array(t, float), np.array(R, float))
    out['Bip01'] = (np.zeros(3), np.eye(3))
    return out

def key_time(k, names=('Hit', 'Fire')):
    return next((t for t, s in k.textkeys if s in names), None)

def warp(t, L, Ls, ht, hs):
    if ht is None or hs is None or not (0 < ht < L) or not (0 < hs < Ls): return Ls * t / L
    return hs * t / ht if t <= ht else hs + (Ls - hs) * (t - ht) / (L - ht)

FWD = None                 # the actor's heading in the animation frame (set from the Ghost's 2hhaimis, level and ahead)
def cast_pose(loc):
    W = sk.fk(loc)
    g = W['Weapon'][1][:, 0]; g = g / np.linalg.norm(g)                # the pistol's aim: only its pitch is kept,
    p = np.arcsin(np.clip(g[2], -1, 1))                                  # the cast points straight ahead (the pistol
    up = np.array([0, 0, 1.0]); n = np.cos(p) * FWD + np.sin(p) * up    # hold is turned ~15 deg off the heading)
    u = up - n * (n @ up); u /= np.linalg.norm(u)
    Rh = np.column_stack([u, n, np.cross(u, n)])                          # fingers up, palm forward, index toward the body
    par = sk.parent['Bip01 R Hand']
    loc['Bip01 R Hand'] = (loc['Bip01 R Hand'][0], W[par][1].T @ Rh)
    for f in FINGERS: loc[f] = (np.array(sk.local[f][0], float), np.array(sk.local[f][1], float))
    W = sk.fk(loc)
    ph, Rhw = W['Bip01 R Hand']
    pw = ph + u * PALM_UP + n * PALM_AHEAD
    Rw = np.column_stack([n, u, np.cross(n, u)])                          # gun frame: X aim, Y up, Z right
    loc['Weapon'] = (Rhw.T @ (pw - ph), Rhw.T @ Rw)
    return loc

def scale_weapon_written(path):
    f = NifFile(path)
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = f.blocks[bi]; ncb = struct.unpack_from('<I', b, 4)[0]; o = 12
    for _ in range(ncb):
        ii, _, pr, nm = struct.unpack_from('<iiBi', b, o); o += 29
        if f.strings[nm] == 'Weapon':
            ib = bytearray(f.blocks[ii]); struct.pack_into('<f', ib, 28, HIDE_SCALE); f.blocks[ii] = bytes(ib)
    open(path, 'wb').write(f.to_bytes())

def build(dst_path, src_path, out_path):
    kt = KFEval(dst_path); ks = KFEval(src_path)
    L = kt.stop; Ls = ks.stop
    rest = re.sub(r'^(sneak)?2hh', '', os.path.basename(dst_path).lower())
    casting = bool(re.match(r'(aim|attack)', rest))
    ht, hs = key_time(kt), key_time(ks)
    n = max(2, int(round(L * 30)) + 1); frames = []
    for i in range(n):
        t = L * i / (n - 1)
        loc = full(ks.sample(min(Ls, warp(t, L, Ls, ht, hs))))
        if casting: loc = cast_pose(loc)
        frames.append((t, loc))
    pr = {b[0]: b[2] for b in ks.blocks}
    top = max(pr.values()) if pr else 65
    names = [b[0] for b in ks.blocks if b[0] != 'Bip01']
    for x in FINGERS + ['Bip01 R Hand', 'Weapon']:
        if x not in names: names.append(x)
    bones = [(nm, pr.get(nm, top)) for nm in names]
    keys = [(t, s) for t, s in kt.textkeys if not s.lower().startswith('prn')]
    write_kf(cr, out_path, kt.name, L, keys, frames, bones=bones, cycle=kt.cycle)
    scale_weapon_written(out_path)
    return casting

if __name__ == '__main__':
    D, OUT = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    Wl = sk.fk(full(KFEval(os.path.join(D, '2hhaimis.kf')).sample(0)))
    g = Wl['Weapon'][1][:, 0]; FWD = np.array([g[0], g[1], 0.0]); FWD /= np.linalg.norm(FWD)
    nc = no = miss = 0
    for fn in sorted(os.listdir(D)):
        m = re.match(r'^(sneak)?2hh(.*\.kf)$', fn, re.I)
        if not m: continue
        src = os.path.join(D, (m.group(1) or '') + '1hp' + m.group(2))
        if not os.path.exists(src): src = os.path.join(D, '1hp' + m.group(2))
        if not os.path.exists(src): print('no 1hp source for', fn); miss += 1; continue
        if build(os.path.join(D, fn), src, os.path.join(OUT, fn)): nc += 1
        else: no += 1
    print('cast files', nc, 'other files', no, 'missing', miss)
