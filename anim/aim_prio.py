"""Harmonize bone priorities inside each aim blend triple (<pre><wt>aim[is].kf / ...up.kf / ...down.kf).
The engine blends Aim/AimUp/AimDown (and the IS triple) by camera pitch. When the base file keys a bone at a different
priority than Up/Down, the three poses land in different blend groups and the rotations are combined without the
quaternion hemisphere check -> the bone swings through 180 deg as the pitch crosses zero (Zetan 2HR iron sights).
For every bone keyed in Up and Down at the same priority, the base file gets that priority. Originals are backed up.
usage: python3 aim_prio.py <anim folder> <backup folder> [--dry]"""
import os, struct, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from nif import Nif
WT = ('h2h', '1hm', '2hm', '1hp', '2hr', '2ha', '2hh', '2hl', '1gt', '1md', '1lm')
def blocks(path):
    d = open(path, 'rb').read(); n = Nif(d)
    i = [j for j in range(n.nblocks) if n.tname(j) == 'NiControllerSequence'][0]
    o = n.boff[i]; nm, ncb, _ = struct.unpack_from('<iII', d, o)
    out = {}
    for k in range(ncb):
        off = o + 12 + 29 * k
        _, _, pr, name = struct.unpack_from('<iiBi', d, off)
        out[n.strings[name]] = (pr, off + 8)
    return d, out
folder, backup = sys.argv[1], sys.argv[2]; dry = '--dry' in sys.argv
fs = set(os.listdir(folder)); total = 0
for pre in ('', 'sneak'):
    for wt in WT:
        for is_ in ('', 'is'):
            b, u, dn = (f'{pre}{wt}aim{is_}{v}.kf' for v in ('', 'up', 'down'))
            if not {b, u, dn} <= fs: continue
            data, B = blocks(os.path.join(folder, b)); _, U = blocks(os.path.join(folder, u)); _, D = blocks(os.path.join(folder, dn))
            data = bytearray(data); changed = []
            for bone, (pr, off) in B.items():
                if bone in U and bone in D and U[bone][0] == D[bone][0] and U[bone][0] != pr:
                    changed.append((bone, pr, U[bone][0])); data[off] = U[bone][0]
            if not changed: continue
            total += 1
            print(f'{b}: {len(changed)} bones re-prioritized, e.g. {changed[:3]}')
            if dry: continue
            os.makedirs(backup, exist_ok=True)
            if not os.path.exists(os.path.join(backup, b)): shutil.copy2(os.path.join(folder, b), os.path.join(backup, b))
            open(os.path.join(folder, b), 'wb').write(bytes(data))
            _, chk = blocks(os.path.join(folder, b))
            assert all(chk[bn][0] == new for bn, _, new in changed)
print('files changed:', total)
