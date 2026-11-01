"""Adds creature voice text keys ("Sound: <SOUN EDID>") to a playable creature's animation folder.
usage: python3 sound_keys.py <race: zetan|ghost> <anim folder> <backup folder> [--dry]

Rules (per KF in the folder's top level; 'sneak' prefix and '_pc' suffix are ignored for classification):
  melee attacks  (h2h/1hm/2hm *attack*)  -> MELEE sound at t=0 (SOUN folder padded with silence = play chance)
  throws         (1gt *attackthrow*)     -> THROW sound at t=0
  jump landings  (mtjumpland*)           -> JUMP sound at t=0
A KF that already voices itself (any 'Sound:' key containing 'vox', e.g. the Ghost People's own spear stabs)
is left alone, and so is a KF that already carries our key (the script is idempotent).
Ranged weapons get no per-shot key (automatic fire would spam); the DLL voices those on landed hits instead.
Every changed file is copied to the backup folder first."""
import os, sys, struct, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from nifedit import NifFile

RACES = {
    'zetan': dict(melee='PCZetanAttackVox', throw='PCZetanAttackVox', jump=None),
    'ghost': dict(melee='PCGhostAttackVox', throw='PCGhostThrowVox', jump='PCGhostJumpVox'),
    'supermutant': dict(melee='PCSuperMutantAttackVox', throw='PCSuperMutantAttackVox', jump=None),
}
MELEE = ('h2h', '1hm', '2hm')

def classify(fn):
    b = fn.lower()[:-3]
    if b.startswith('sneak'): b = b[5:]
    if b.endswith('_pc'): b = b[:-3]
    if b.startswith('mtjumpland'): return 'jump'
    if b[:3] in MELEE and 'attack' in b: return 'melee'
    if b[:3] == '1gt' and 'attackthrow' in b: return 'throw'
    return None

def text_keys(f):
    for i, b in enumerate(f.blocks):
        if f.types[f.btype[i]] == 'NiTextKeyExtraData':
            name, n = struct.unpack_from('<iI', b, 0)
            keys = [struct.unpack_from('<fi', b, 8 + 8 * k) for k in range(n)]
            assert len(b) == 8 + 8 * n, 'text key block size'
            return i, name, [(t, f.strings[s]) for t, s in keys]
    return None, None, None

def add_key(path, sound):
    raw = open(path, 'rb').read()
    f = NifFile(path)
    assert f.to_bytes() == raw, 'round trip mismatch'
    i, name, keys = text_keys(f)
    if i is None: return 'no text keys'
    if any(s.lower().startswith('sound:') and 'vox' in s.lower() for _, s in keys): return 'already voiced'
    tag = 'Sound: ' + sound
    if any(s == tag for _, s in keys): return 'already has key'
    # insert after every key at t=0 (after 'start'), so the order stays time-sorted
    pos = 0
    while pos < len(keys) and keys[pos][0] <= 1e-6: pos += 1
    keys.insert(pos, (0.0, tag))
    blk = struct.pack('<iI', name, len(keys)) + b''.join(struct.pack('<fi', t, f.str_index(s)) for t, s in keys)
    f.blocks[i] = blk
    return f

def main():
    race, folder, backup = sys.argv[1], sys.argv[2], sys.argv[3]
    dry = '--dry' in sys.argv
    cfg = RACES[race]
    stats = {}
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith('.kf'): continue
        kind = classify(fn)
        snd = cfg.get(kind) if kind else None
        if not snd: continue
        p = os.path.join(folder, fn)
        r = add_key(p, snd)
        if isinstance(r, str):
            stats[(kind, r)] = stats.get((kind, r), 0) + 1; continue
        stats[(kind, 'added ' + snd)] = stats.get((kind, 'added ' + snd), 0) + 1
        if dry: continue
        os.makedirs(backup, exist_ok=True)
        bk = os.path.join(backup, fn)
        if not os.path.exists(bk): shutil.copy2(p, bk)
        data = r.to_bytes()
        open(p, 'wb').write(data)
        _, _, keys = text_keys(NifFile(p))
        assert ('Sound: ' + snd) in [s for _, s in keys]
    for k in sorted(stats): print(f'{k[0]:6s} {k[1]:28s} {stats[k]}')

if __name__ == '__main__':
    main()
