"""Hides the player's weapon model by animation (no DLL): the skeleton's Weapon node, which carries the weapon model, is
keyed at scale 0.001 in every file of the listed weapon types (and their sneak copies).
  guns / thrown / mines (TYPE=EMITTER): prn keys -> the Weapon node's own skeleton parent (a prn key moves the Weapon
      node under the named bone with its bind transform), and Weapon keyed every 1/30 s onto the emitter node, the
      model's +X along the emitter's forward (its local axis nearest the actor's forward in the type's aim), +Y along
      its up: the unseen model's own ProjectileNode sits on the emitter, pointing ahead, so the shot leaves there;
      equip / unequip / holster files: Weapon at its skeleton bind, scale 0.001
  melee / unarmed (--melee TYPES): the file's own Weapon motion kept (or its bind when it has none), scale 0.001
Priority of the Weapon channel 55. Files the tool already handled are rewritten the same way (idempotent).
usage: python3 weapon_hide.py <folder> <Skeleton.nif> [type=emitter ...] [--melee h2h,1hm,2hm]
       python3 weapon_hide.py --race <name> <folder> <Skeleton.nif>      (the settings below, run after the race's build)
Mister Handy / Gutsy guns are keyed by build_robot.py (weapon_follow); their melee here. Deathclaw / Lakelurk / Mirelurk:
deathclaw_mouth.py / mouth_fire.py --hide do the same for their sets."""
import os, re, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval, Skeleton
from holster_fix import KFFile
from hip_spine_fix import drop_channel
import robotlib as RL

SCALE = 0.001


def axis_toward(R, v):
    """the signed local axis of rotation R that points most along world v"""
    d = R.T @ v; i = int(np.argmax(np.abs(d))); a = np.zeros(3); a[i] = np.sign(d[i]); return a


ROOT_R = {}           # folder -> the root's (Bip01) rotation as the idle / locomotion key it, for files that don't


def root_r(folder):
    if folder not in ROOT_R:
        ROOT_R[folder] = None
        for f in ('mtidle.kf', 'mtforward.kf', os.path.join('Locomotion', 'mtforward.kf')):
            p = os.path.join(folder, f)
            if os.path.exists(p):
                b = KFEval(p).sample(0.0).get('Bip01')
                if b is not None and b[1] is not None: ROOT_R[folder] = np.array(b[1], float); break
    return ROOT_R[folder]


def pose(sk, k, t, folder=None):
    s = dict(k.sample(t)); loc = {}
    b = s.get('Bip01')
    if folder and (b is None or b[1] is None) and root_r(folder) is not None:     # (the securitron / sentry bot aims don't
        s['Bip01'] = (b[0] if b else None, root_r(folder))                         #  key it: bind = turned 180 / 90 deg)
    for n in sk.order:
        tr, R, _ = sk.local[n]
        if n in s:
            if s[n][0] is not None: tr = s[n][0]
            if s[n][1] is not None: R = s[n][1]
        loc[n] = (np.array(tr, float), np.array(R, float))
    W = {}
    def world(n):                                  # along the parent chain only (skeletons with grafted duplicate names)
        if n not in W:
            t, R = loc[n]; p = sk.parent[n]
            if p is None: W[n] = (t, R)
            else: pp, pR = world(p); W[n] = (pp + pR @ t, pR @ R)
        return W[n]
    class _W(dict):
        def __missing__(self, n): return world(n)
    return _W()


def set_scale(kf, keys_t0):
    ent = [o for o, c in kf.cb if c == 'Weapon'][0]
    ii = struct.unpack_from('<i', kf.f.blocks[kf.seq], ent)[0]
    b = bytearray(kf.f.blocks[ii]); struct.pack_into('<f', b, 28, SCALE); kf.f.blocks[ii] = bytes(b)
    di = struct.unpack_from('<i', b, 32)[0]
    if di >= 0:
        db = kf.f.blocks[di]; assert db[-4:] == b'\0\0\0\0', 'Weapon data with scale keys'
        kf.f.blocks[di] = db[:-4] + struct.pack('<IIff', 1, 1, keys_t0, SCALE)


def run(folder, skel, emitters, melee):
    sk = Skeleton(skel); WP = sk.parent['Weapon']; wb = sk.local['Weapon']
    n = WP
    while n in sk.parent:
        assert abs(sk.local[n][2] - 1) < 1e-3, ('scaled parent', n); n = sk.parent[n]
    fwd_up = {}
    for t, em in emitters.items():                       # the emitter's forward / up axes, from the type's aim
        aim = os.path.join(folder, t + 'aim.kf')
        W = pose(sk, KFEval(aim), 0.0, folder); R = W[em][1]
        fwd_up[t] = (axis_toward(R, np.array([0, 1.0, 0])), axis_toward(R, np.array([0, 0, 1.0])))
        print(f'  {t}: emitter {em}, forward axis {fwd_up[t][0]}, up axis {fwd_up[t][1]}')
    done = 0
    for f in sorted(os.listdir(folder)):
        m = re.match(r'^(?:sneak)?(h2h|1hm|2hm|1hp|2ha|2hr|2hh|2hl|1gt|1md|1lm)(.*)\.kf$', f)
        if not m or (m.group(1) not in emitters and m.group(1) not in melee): continue
        T, g = m.group(1), m.group(2); p = os.path.join(folder, f)
        if T in emitters:
            em = emitters[T]; fa, ua = fwd_up[T]
            kf = KFFile(p); d = bytearray(kf.f.blocks[kf.tk_block]); nk, = struct.unpack_from('<I', d, 4)
            for j in range(nk):
                _, si = struct.unpack_from('<fi', d, 8 + 8 * j)
                if kf.f.strings[si].lower().startswith('prn:'): struct.pack_into('<i', d, 8 + 8 * j + 4, kf.f.str_index('prn: ' + WP))
            kf.f.blocks[kf.tk_block] = bytes(d)
            if 'Weapon' in [c for _, c in kf.cb]: drop_channel(kf, 'Weapon')
            RL.add_channel(kf, 'Weapon', tr=np.array(wb[0], float), R=np.array(wb[1], float))
            kf.save(p); kf = KFFile(p)
            if re.match(r'^(equip|unequip|holster)', g):
                keys = [(0.0, np.array(wb[0], float), np.array(wb[1], float))]
            else:
                k = KFEval(p); nf = max(2, int(round((k.stop - k.start) * 30)) + 1); keys = []
                for i in range(nf):
                    tt = k.start + (k.stop - k.start) * i / (nf - 1); W = pose(sk, k, tt, folder)
                    pp, pR = W[WP]; ep, eR = W[em]
                    X = eR @ fa; Y = eR @ ua
                    keys.append((tt, pR.T @ (ep - pp), pR.T @ np.column_stack([X, Y, np.cross(X, Y)])))
        else:
            kf = KFFile(p)
            if 'Weapon' in [c for _, c in kf.cb]:
                k = KFEval(p); nf = max(2, int(round((k.stop - k.start) * 30)) + 1); keys = []
                for i in range(nf):
                    tt = k.start + (k.stop - k.start) * i / (nf - 1); s = k.sample(tt).get('Weapon')
                    tr = np.array(s[0] if s and s[0] is not None else wb[0], float); R = np.array(s[1] if s and s[1] is not None else wb[1], float)
                    keys.append((tt, tr, R))
            else:
                RL.add_channel(kf, 'Weapon', tr=np.array(wb[0], float), R=np.array(wb[1], float)); kf.save(p); kf = KFFile(p)
                keys = [(0.0, np.array(wb[0], float), np.array(wb[1], float))]
        kf.set_channel('Weapon', keys); set_scale(kf, keys[0][0]); kf.save(p)
        kf = KFFile(p); dd = bytearray(kf.f.blocks[kf.seq])
        for o, c in kf.cb:
            if c == 'Weapon': dd[o + 8] = 55
        kf.f.blocks[kf.seq] = bytes(dd); kf.save(p); done += 1
    print('weapon_hide:', folder, done, 'files')


_G = ('1hp', '2ha', '2hr', '2hh', '2hl', '1gt', '1md', '1lm')
def _em(**kw): return {t: kw.get(t, kw['all']) for t in _G}
RACES = {
    'protectron': (_em(all='ProjectileNode_RHandLaser', **{'2hl': 'ProjectileNode_HeadLaser'}), ['h2h']),
    'robobrain': (_em(all='ProjectileNode_Right', **{'2hl': 'ProjectileNode_HeadLaser'}), ['h2h']),
    'sentrybot': (_em(all='PCMissileEmitter', **{t: 'ProjectileNode_RGatling' for t in ('1hp', '2ha', '2hr', '2hh')}), ['h2h']),
    'securitron': (_em(all='ProjectileNode_Launcher', **{'1hp': 'ProjectileNode_MachineGun', '2ha': 'ProjectileNode_MachineGun',
                                                     '2hr': 'ProjectileNode_GatlingLaser', '2hh': 'ProjectileNode_Missle'}), ['h2h']),
    'eyebot': ({}, ['h2h'] + list(_G)),                 # its Weapon node already sits on the emitter: kept at its bind
    'trog': ({}, ['h2h', '1hm', '2hm']), 'tunneler': ({}, ['h2h', '1hm', '2hm']),   # guns: mouth_fire.py
    'misterhandy': ({}, ['h2h', '1hm', '2hm']), 'mistergutsy': ({}, ['h2h', '1hm', '2hm']),
}


if __name__ == '__main__':
    a = sys.argv[1:]; melee = []
    if a[0] == '--race':
        em, ml = RACES[a[1]]; run(a[2], a[3], em, ml); sys.exit()
    if '--melee' in a:
        i = a.index('--melee'); melee = a[i + 1].split(','); del a[i:i + 2]
    run(a[0], a[1], dict(x.split('=', 1) for x in a[2:]), melee)
