"""Holster positions per weapon type.

The engine re-parents the weapon with a `prn: <bone>` text key: the unequip animation moves it from the hand to the
holster bone, the equip animation back to Bip01 R Hand, and <type>holster.kf keys the Weapon node's transform in the
holster bone's space while the weapon is put away. Humans (characters\\_male): rifles / assault rifles / launchers on
Bip01 Spine2 (each its own spot), heavy weapons stay in Bip01 R Hand, melee / grenades / mines / pistols on Bip01 Pelvis.

Races whose sets borrowed equip / unequip / holster files from one other type (equip_from / src in anim/creatures/*.py)
put every weapon at that type's spot: Ghost (two-handed melee spot on the spine), Ghoul (all stay in the hand),
Hillfolk (all at one pelvis spot). This pass gives every weapon type the human holster bone and the human Weapon
transform for that type, translation scaled by the creature's / human's torso length (Pelvis -> Neck in the bind pose;
checked against vanilla: the super mutant's own rifle holster is 1.53x the human offset, torso ratio 1.56), and keeps
each race's own draw / sheathe motion. A type whose holster already matches the human one (bone + transform) is left
alone (Ghost pistols):
  holster  : Weapon = target transform (static), prn -> target bone
  unequip  : prn -> target bone (same time); Weapon unchanged before the prn key, = target from it on
  equip    : prn stays Bip01 R Hand (same time); Weapon = target before it, unchanged from it on
Only the Weapon channel and the prn text keys change (new interpolator / data blocks; every other block untouched).
OWN_SPOT types stay at the race's own vanilla spot (Ghost 1GT: the back).
usage: python3 holster_fix.py <human ref dir> <human skeleton.nif> <race folder> [--only 1gt,...] [--apply]"""
import os, re, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KFEval, Skeleton, m2q, q2m
from nifedit import NifFile

TYPES = ['1hp', '2hr', '2ha', '2hh', '2hl', '1hm', '1gt', '1md', '1lm', '2hm']
# types a race keeps at its own vanilla spot (never moved to the human one): the Ghost People carry their throwing
# spears / gas bombs on the back, as Dead Money's nvdlc01\creatures\ghosts\1gt* files place them (their spear's 2HM
# spot), not on the hip - restored from those files by ghost_thrown_back.py
OWN_SPOT = {'Ghost': ('1gt',)}


def prn_keys(kf):
    return [(t, v[5:].strip()) for t, v in kf.textkeys if v.lower().startswith('prn:')]


def human_targets(ref):
    out = {}
    for T in TYPES:
        p = os.path.join(ref, T + 'holster.kf')
        if not os.path.exists(p): continue
        k = KFEval(p); pk = [b for _, b in prn_keys(k) if b.startswith('Bip01')]
        bone = pk[-1]                                  # 1md: R Hand '-at none' then Pelvis -> the last one
        t, R = k.sample(k.start)['Weapon']
        out[T] = (bone, np.array(t), np.array(R))
    return out


def torso(sk):
    W = sk.fk(); return float(np.linalg.norm(W['Bip01 Neck'][0] - W['Bip01 Pelvis'][0]))


class KFFile:
    """in-place edits of a KF: the Weapon controlled block's interpolator and the text keys"""
    def __init__(s, path):
        s.path = path; s.f = NifFile(path); f = s.f
        s.seq = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
        d = f.blocks[s.seq]
        nm, ncb, _ = struct.unpack_from('<iII', d, 0)
        s.cb = []
        for k in range(ncb):
            o = 12 + 29 * k
            interp, ctrl, prio, node = struct.unpack_from('<iiBi', d, o)
            s.cb.append((o, f.strings[node] if node >= 0 else None))
        s.tk_block = struct.unpack_from('<i', d, 12 + 29 * ncb + 4)[0]
    def weapon_entry(s):
        return [o for o, n in s.cb if n == 'Weapon'][0]
    def set_weapon(s, keys): s.set_channel('Weapon', keys)
    def set_channel(s, name, keys):
        """keys: [(t, trans(3), R(3x3))] -> new NiTransformInterpolator + NiTransformData (linear keys) for `name`"""
        f = s.f
        qs = []; prev = None
        for t, p, R in keys:
            q = m2q(R)
            if prev is not None and np.dot(q, prev) < 0: q = -q
            qs.append((t, q)); prev = q
        t0, p0, _ = keys[0]; q0 = qs[0][1]
        static = len(keys) == 1
        data = -1
        if not static:
            body = struct.pack('<II', len(qs), 1) + b''.join(struct.pack('<f4f', t, *q) for t, q in qs)
            body += struct.pack('<II', len(keys), 1) + b''.join(struct.pack('<f3f', t, *p) for t, p, _ in keys)
            body += struct.pack('<I', 0)
            data = f.add_block('NiTransformData', body)
        interp = f.add_block('NiTransformInterpolator', struct.pack('<3f4ffi', *p0, *q0, 1.0, data))
        entry = [o for o, n in s.cb if n == name][0]
        d = bytearray(f.blocks[s.seq]); struct.pack_into('<i', d, entry, interp); f.blocks[s.seq] = bytes(d)
    def set_prn(s, old_bone, new_bone):
        f = s.f; d = bytearray(f.blocks[s.tk_block])
        n, = struct.unpack_from('<I', d, 4); changed = 0
        for j in range(n):
            o = 8 + 8 * j; t, si = struct.unpack_from('<fi', d, o)
            v = f.strings[si]
            if v.lower().startswith('prn:') and v[5:].strip() == old_bone:
                struct.pack_into('<i', d, o + 4, f.str_index('prn: ' + new_bone)); changed += 1
        f.blocks[s.tk_block] = bytes(d); return changed
    def add_prn(s, t, bone):
        f = s.f; d = f.blocks[s.tk_block]
        name, n = struct.unpack_from('<iI', d, 0)
        ent = [struct.unpack_from('<fi', d, 8 + 8 * j) for j in range(n)] + [(t, f.str_index('prn: ' + bone))]
        ent.sort(key=lambda e: e[0])
        f.blocks[s.tk_block] = struct.pack('<iI', name, len(ent)) + b''.join(struct.pack('<fi', *e) for e in ent)
    def save(s, path=None):
        open(path or s.path, 'wb').write(s.f.to_bytes())


def times(k, fps=30.0):
    n = max(2, int(round((k.stop - k.start) * fps)) + 1)
    return [k.start + (k.stop - k.start) * i / (n - 1) for i in range(n)]


def fix_race(ref, human_skel, folder, apply=False, only=None):
    H = human_targets(ref); hs = Skeleton(human_skel); cs = Skeleton(os.path.join(folder, 'Skeleton.nif'))
    report = []; ratio = torso(cs) / torso(hs)
    own = OWN_SPOT.get(os.path.basename(os.path.normpath(folder)), {})
    for T, (bone, ht, hR) in H.items():
        if T in ('2hm',): continue                     # the races' own two-handed melee placements stay
        if only and T not in only: continue
        if T in own: report.append(f'{T}: kept at the race\'s own spot'); continue
        tt = ht * ratio; tR = hR
        cur = os.path.join(folder, T + 'holster.kf')
        if os.path.exists(cur):
            kc = KFEval(cur); w = kc.sample(kc.start).get('Weapon'); cb = [b2 for _, b2 in prn_keys(kc) if b2.startswith('Bip01')]
            if w is not None and cb and cb[-1] == bone and np.allclose(w[0], tt, atol=0.05) and np.allclose(w[1], tR, atol=0.01):
                report.append(f'{T}: already the human holster - unchanged'); continue
        files = sorted(fn for fn in os.listdir(folder) if re.match(r'^(sneak)?' + T + r'(equip|unequip|holster)\.kf$', fn))
        for fn in files:
            path = os.path.join(folder, fn); k = KFEval(path)
            if 'Weapon' not in k.chan: report.append(f'{fn}: no Weapon channel - skipped'); continue
            pk = prn_keys(k); kind = re.sub(r'^(sneak)?' + T, '', fn)[:-3]
            kf = KFFile(path)
            if kind == 'holster':
                old = [b2 for _, b2 in pk if b2.startswith('Bip01')]
                for ob in set(old): kf.set_prn(ob, bone)
                if not old: kf.add_prn(min(k.start + 0.0667, k.stop), bone)
                kf.set_weapon([(k.start, tt, tR)])
                report.append(f'{fn}: prn {old} -> {bone}, Weapon -> {np.round(tt, 1).tolist()} (x{ratio:.2f})')
            elif kind == 'unequip':
                pt = [(t, b2) for t, b2 in pk if b2.startswith('Bip01') and b2 != 'Bip01 R Hand' or (t, b2) == pk[-1]]
                if not pk: report.append(f'{fn}: no prn key - skipped'); continue
                tp, ob = pk[-1]
                kf.set_prn(ob, bone)
                keys = []
                for t in times(k):
                    if t < tp - 1e-4:
                        w = k.sample(t)['Weapon']; keys.append((t, np.array(w[0]), np.array(w[1])))
                if keys and keys[-1][0] < tp - 1e-3:
                    w = k.sample(tp - 1e-3)['Weapon']; keys.append((tp - 1e-3, np.array(w[0]), np.array(w[1])))
                keys += [(tp, tt, tR), (k.stop, tt, tR)]
                kf.set_weapon(keys)
                report.append(f'{fn}: prn {ob}@{tp:.2f} -> {bone}; Weapon -> holster spot from {tp:.2f}')
            elif kind == 'equip':
                hand = [t for t, b2 in pk if b2 == 'Bip01 R Hand']
                if not hand: report.append(f'{fn}: no prn R Hand - skipped'); continue
                tp = hand[0]
                keys = [(k.start, tt, tR), (max(k.start, tp - 1e-3), tt, tR)]
                for t in times(k):
                    if t >= tp - 1e-4:
                        w = k.sample(max(t, tp))['Weapon']; keys.append((max(t, tp), np.array(w[0]), np.array(w[1])))
                kf.set_weapon(keys)
                report.append(f'{fn}: Weapon at the holster spot until prn R Hand@{tp:.2f}')
            if apply: kf.save()
    return report


if __name__ == '__main__':
    ref, hsk, folder = sys.argv[1:4]
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    for line in fix_race(ref, hsk, folder, apply='--apply' in sys.argv, only=only): print(line)
