"""Cannibal.kf per skeleton folder (StartCannibal: the player's feeding idle; the engine's Cannibal package ends with it).
  vanilla feeding idle of the same skeleton (re-baked, clamped, the human cannibal gore sound added where it has none):
      Ghoul / GlowingOne   creatures\\ghoul\\idleanims\\specialidle_corpsecheck.kf        (feral ghouls at a corpse)
      Mirelurk             creatures\\mirelurk\\idleanims\\specialidle_feed.kf
      Lakelurk             creatures\\mirelurkking\\idleanims\\specialidle_feed.kf       (its skeleton)
      Tunneler             creatures\\nvsporecarrier\\idleanims\\specialidle_cannibal.kf  (Lonesome Road STCannibal)
      Trog                 dlcpitt\\creatures\\streettrog\\idleanims\\specialidle_cannibal.kf
      SuperMutant / Nightkin / SuperMutantDC   creatures\\smspinebreaker\\idleanims\\nvdlc01specialidle_devour.kf (Dead Money)
  Ghost                    the human 3rdP_Cannibal.kf, copied as is (the Ghost skeleton is the human one)
  Zetan / Swampfolk / Hillfolk   the human 3rdP_Cannibal.kf retargeted (retarget.Retarget: world-space deltas from
                           the human bind onto the creature's bind, legs by IK to the scaled human ankles)
  Deathclaw                its own crouch (specialidle_crouchloop: down / loop / up, the loop played twice) with a
                           feeding overlay: the neck dips to the corpse once a second, the jaw (Bip01 Ponytail3)
                           opens on the way down and snaps shut at the bottom, the head tugs sideways coming up
  robots                   placeholder: their own idle for the human file's length / keys, no sound (the event
                           needs an idle to finish; robots don't eat)
usage: python3 cannibal.py <folder name> <race folder with mtidle.kf + Skeleton.nif> <out IdleAnims dir>"""
import os, shutil, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KF, KFEval
import rig
from act_idles import Shim, wrot, rotx, chain_of, REF, ease

FEED = '/home/claude/fnv/ref_act/feed/meshes/'
HUMAN_CANNIBAL = os.path.join(REF, '3rdp_cannibal.kf')
HUMAN_SKEL = '/home/claude/fnv/ref_weap/skeleton.nif'
GORE = 'Sound: NPCHumanPerkCannibal'
PRIO = 45
VANILLA = {'Ghoul': 'creatures/ghoul/idleanims/specialidle_corpsecheck.kf', 'GlowingOne': 'creatures/ghoul/idleanims/specialidle_corpsecheck.kf',
           'Mirelurk': 'creatures/mirelurk/idleanims/specialidle_feed.kf', 'Lakelurk': 'creatures/mirelurkking/idleanims/specialidle_feed.kf',
           'Tunneler': 'creatures/nvsporecarrier/idleanims/specialidle_cannibal.kf', 'Trog': 'dlcpitt/creatures/streettrog/idleanims/specialidle_cannibal.kf',
           'SuperMutant': 'creatures/smspinebreaker/idleanims/nvdlc01specialidle_devour.kf',
           'Nightkin': 'creatures/smspinebreaker/idleanims/nvdlc01specialidle_devour.kf',
           'SuperMutantDC': 'creatures/smspinebreaker/idleanims/nvdlc01specialidle_devour.kf'}
RETARGET = ('Zetan', 'Swampfolk', 'Hillfolk')
ROBOTS = ('Eyebot', 'Protectron', 'Robobrain', 'Securitron', 'SentryBot', 'MisterHandy', 'MisterGutsy')


def base_loc(sk, s):
    loc = {}
    for nm in sk.order:
        tr, R, _ = sk.local[nm]
        if nm in s:
            if s[nm][0] is not None: tr = s[nm][0]
            if s[nm][1] is not None: R = s[nm][1]
        loc[nm] = (np.array(tr, float), np.array(R, float))
    return loc


def with_gore(tk, t=0.37):
    if any(v.lower().startswith('sound:') and 'cannibal' in v.lower() for _, v in tk) or \
       any(v.lower().startswith('sound:') and ('eat' in v.lower()) for _, v in tk): return list(tk)
    return sorted(list(tk) + [(t, GORE)], key=lambda x: x[0])


def rebake(src, folder, skel, out, add_gore=True):
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    k = KF(src); ev = KFEval(src); L = k.stop; n = int(round(L * 30)) + 1
    keyed = [b[0] for b in ev.blocks if b[0] in sk.local]
    frames = [(L * i / (n - 1), base_loc(sk, ev.sample(L * i / (n - 1)))) for i in range(n)]
    tk = [(t, v.strip()) for t, v in k.textkeys if not v.strip().startswith('-Global')]
    if add_gore: tk = with_gore(tk)
    rig.write_kf(cr, out, 'SpecialIdle_Cannibal', L, tk, frames, bones=[(b, PRIO) for b in keyed], cycle=2)


def retargeted(folder, skel, out):
    from retarget import Retarget
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf'))
    legs = [(f'Bip01 {s} Thigh', f'Bip01 {s} Calf', f'Bip01 {s} Foot') for s in 'LR']
    rt = Retarget(HUMAN_SKEL, skel, legs); rt.clean_root = False
    sp = rt.src_pose
    def src_pose(k, t):                     # the human file doesn't key Bip01: in game it carries the locomotion's
        loc = sp(k, t)                      # heading (identity), not the skeleton's bind turn
        if k.sample(t).get('Bip01') is None: loc['Bip01'] = (loc['Bip01'][0], np.eye(3))
        return loc
    rt.src_pose = src_pose
    k = KF(HUMAN_CANNIBAL); ev = KFEval(HUMAN_CANNIBAL); L = k.stop; n = int(round(L * 30)) + 1
    frames = []
    for i in range(n):
        loc, _ = rt.frame(ev, L * i / (n - 1)); frames.append((L * i / (n - 1), loc))
    bones = [(b, PRIO) for b in rt.hs.order if b in rt.map or b in rt.ROOTS]
    rig.write_kf(cr, out, k.name, L, [(t, v.strip()) for t, v in k.textkeys], frames, bones=bones, cycle=2)


def deathclaw(folder, skel, out):
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    src = FEED + 'creatures/deathclaw/idleanims/specialidle_crouchloop.kf'
    k = KF(src); ev = KFEval(src)
    tkd = {v.strip().lower(): t for t, v in k.textkeys}
    a, b = tkd['startloop'], tkd['endloop']; cyc = b - a; loops = 2
    L = k.stop + cyc * (loops - 1); n = int(round(L * 30)) + 1
    def src_t(t):
        if t < a: return t
        if t < a + cyc * loops: return a + (t - a) % cyc
        return b + (t - a - cyc * loops)
    neck = [nm for nm in chain_of(sk) if 'Neck' in nm or 'Head' in nm]
    f0, f1 = a + 0.25, a + cyc * loops - 0.15                   # feeding window inside the crouch
    frames = []
    for i in range(n):
        t = L * i / (n - 1); loc = base_loc(sk, ev.sample(src_t(t)))
        w = ease((t - f0) / 0.3) * (1 - ease((t - (f1 - 0.3)) / 0.3))
        if w > 0:
            ph = ((t - f0) % 1.0)                                   # one bite a second
            dip = np.sin(np.pi * min(ph / 0.45, 1.0)) if ph < 0.45 else 0.0          # down to the corpse and back
            tug = np.sin(np.pi * (ph - 0.45) / 0.55) if ph >= 0.45 else 0.0          # sideways tug coming up
            jaw = np.radians(35) * (np.sin(np.pi * ph / 0.3) if ph < 0.3 else 0.0)   # open going down, shut at the bottom
            pitch = np.radians(28) * dip * w / len(neck); yaw = np.radians(12) * tug * w * (1 if int((t - f0)) % 2 else -1)
            for nm in neck:
                pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
                c, s_ = np.cos(yaw / len(neck)), np.sin(yaw / len(neck))
                Rz = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
                loc[nm] = (loc[nm][0], pR.T @ Rz @ rotx(-pitch) @ R)
            if 'Bip01 Ponytail3' in loc:
                c, s_ = np.cos(jaw * w), np.sin(jaw * w)
                jt, jR = loc['Bip01 Ponytail3']; loc['Bip01 Ponytail3'] = (jt, np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]]) @ jR)
        frames.append((t, loc))
    tk = [(0.0, 'start'), (tkd['blend:6'], 'Blend:6')]
    tk += [(t if t < a else (t + cyc * (loops - 1) if t >= b else t), v.strip()) for t, v in k.textkeys if v.lower().startswith('sound:')]
    tk += [(f0 + 0.3 + j, GORE) for j in range(0, int(f1 - f0 - 0.3), 2)]
    tk += [(L, 'end')]
    keyed = [bb[0] for bb in ev.blocks if bb[0] in sk.local] + neck + ['Bip01 Ponytail3']
    rig.write_kf(cr, out, 'SpecialIdle_Cannibal', L, sorted(tk, key=lambda x: x[0]), frames,
                 bones=[(bb, PRIO) for bb in dict.fromkeys(keyed) if bb in sk.local], cycle=2)


def robot(folder, skel, out):
    cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    idle = KFEval(os.path.join(folder, 'mtidle.kf')); h = KF(HUMAN_CANNIBAL); L = h.stop; n = int(round(L * 30)) + 1
    frames = []
    for i in range(n):
        t = L * i / (n - 1); s = idle.sample(t % idle.stop); loc = base_loc(sk, s)
        if not (s.get('Bip01') and s['Bip01'][1] is not None): loc['Bip01'] = (loc['Bip01'][0], np.eye(3))
        frames.append((t, loc))
    keyed = [b[0] for b in idle.blocks if b[0] != 'Bip01' and b[0] in sk.local]
    tk = [(t, v.strip()) for t, v in h.textkeys if not v.lower().startswith('sound:')]
    rig.write_kf(cr, out, h.name, L, tk, frames, bones=[(b, PRIO) for b in keyed], cycle=2)


def build(name, folder, out_dir):
    os.makedirs(out_dir, exist_ok=True); out = os.path.join(out_dir, 'Cannibal.kf'); skel = os.path.join(folder, 'Skeleton.nif')
    if name == 'Ghost': shutil.copyfile(HUMAN_CANNIBAL, out); return 'human copy'
    if name in VANILLA: rebake(FEED + VANILLA[name], folder, skel, out); return 'vanilla ' + VANILLA[name].split('/')[-1]
    if name in RETARGET: retargeted(folder, skel, out); return 'human retargeted'
    if name == 'Deathclaw': deathclaw(folder, skel, out); return 'crouch + bites'
    if name in ROBOTS: robot(folder, skel, out); return 'placeholder'
    raise SystemExit('no cannibal rule for ' + name)


if __name__ == '__main__':
    print(sys.argv[1], build(*sys.argv[1:4]))
