"""Sneak audit: per race and weapon type, (1) standing groups without a sneak version, (2) sneak files
that put the creature upright (they key the pelvis / legs at standing height, so the crouch is lost while the group
plays: aims, attacks, reloads, equips...).
Groups are mapped like the engine: filename prefix (sneak, weapon type; no type = mt) + NiControllerSequence name.
Pelvis height = world z of Bip01 Pelvis at the file's first frame (FK on the race skeleton with the file's keys;
unkeyed bones at the bind pose), compared with the race's own sneakmtidle and mtidle.
usage: python3 sneak_audit.py <race folder> [types,comma,separated]"""
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KF, KFEval, Skeleton

TYPES = ['h2h', '1hm', '2hm', '1hp', '2hr', '2ha', '2hh', '2hl', '1gt', '1md', '1lm']
MOVE = {'Forward', 'Backward', 'Left', 'Right', 'FastForward', 'FastBackward', 'FastLeft', 'FastRight', 'TurnLeft', 'TurnRight',
        'Idle', 'DodgeLeft', 'DodgeRight'}             # movement: a missing sneak<type> version falls back to sneakmt (as humans)
LEG_BONES = ('Bip01 Pelvis', 'Bip01 NonAccum', 'Bip01 L Thigh', 'Bip01 R Thigh')


def group_of(fn, seq):
    b = fn.lower()[:-3]; sneak = b.startswith('sneak'); b = b[5:] if sneak else b
    t = next((T for T in TYPES if b.startswith(T)), 'mt')
    seq = re.sub(r'_[a-z]$', '', seq)               # AttackLeft_A / _B variants = one group
    return sneak, t, seq


def scan(folder):
    out = {}
    for sub in ('', 'Locomotion', os.path.join('Locomotion', 'Hurt')):
        d = os.path.join(folder, sub)
        if not os.path.isdir(d): continue
        for fn in os.listdir(d):
            if not fn.lower().endswith('.kf'): continue
            try: k = KF(os.path.join(d, fn))
            except Exception: continue
            out.setdefault(group_of(fn, k.name), []).append(os.path.join(sub, fn))
    return out


def pelvis_z(sk, path):
    k = KFEval(path); s = k.sample(k.start)
    if not any(b in s for b in LEG_BONES): return None
    pose = {n: v for n, v in s.items() if n in sk.local}
    pose['Bip01'] = (np.zeros(3), pose['Bip01'][1] if 'Bip01' in pose else None)   # the accum root moves with the actor: height = NonAccum
    W = sk.fk(pose)
    return float(W['Bip01 Pelvis'][0][2]) if 'Bip01 Pelvis' in W else None


def audit(folder, types):
    G = scan(folder); sk = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    zs = {}
    for key, name in (((False, 'mt', 'Idle'), 'stand'), ((True, 'mt', 'Idle'), 'sneak')):
        if key in G: zs[name] = pelvis_z(sk, os.path.join(folder, G[key][0]))
    rep = [f'pelvis z: standing idle {zs.get("stand")}, sneak idle {zs.get("sneak")}']
    missing, upright = {}, {}
    for T in types:
        stand = {g for (s, t, g) in G if not s and t == T}
        sneak = {g for (s, t, g) in G if s and t == T}
        miss = sorted(g for g in stand - sneak if g.lower() not in {m.lower() for m in MOVE})
        if miss: missing[T] = miss
        if zs.get('stand') and zs.get('sneak'):
            mid = (zs['stand'] + zs['sneak']) / 2
            for g in sorted(sneak):
                for f in G[(True, T, g)]:
                    z = pelvis_z(sk, os.path.join(folder, f))
                    if z is not None and z > mid: upright.setdefault(T, []).append(f'{g}({z:.0f})')
    for T in types:
        if T in missing: rep.append(f'{T}: no sneak version of {len(missing[T])}: {" ".join(missing[T])}')
        if T in upright: rep.append(f'{T}: {len(upright[T])} sneak files upright: {" ".join(sorted(set(upright[T]))[:40])}')
    for g in sorted(MOVE):                           # sneak movement itself (mt)
        if (False, 'mt', g) in G and (True, 'mt', g) not in G: rep.append(f'mt: no sneak {g}')
    return rep


if __name__ == '__main__':
    folder = sys.argv[1]; types = sys.argv[2].split(',') if len(sys.argv) > 2 else TYPES
    for line in audit(folder, types): print(line)
