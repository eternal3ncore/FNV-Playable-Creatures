"""The lakelurk / mirelurk king skeleton keeps its Weapon node under Dummy01 (under Bip01 R Hand); every other rig has it
right under the hand. The equip files' 'prn: Bip01 R Hand' (the vanilla lakelurk's own, and the copies the builder makes)
then put the weapon on the hand bone without Dummy01's offset and turn - the hidden gun (and its ProjectileNode) sat
beside the hand pointing up, and shots left there. This writes a copy of the vanilla skeleton with Weapon re-parented
to Bip01 R Hand (same world transform: Dummy01's bind folded in), the source skeleton of the Lakelurk config.
usage: python3 lurk_weapon_parent.py <vanilla skeleton.nif> <out skeleton.nif>"""
import sys
sys.path.insert(0, '/home/claude/fnv/anim'); sys.path.append('/home/claude/fnv')
import numpy as np
from kf import Skeleton
from nifedit import NifFile
SRC, OUT = sys.argv[1], sys.argv[2]
sk = Skeleton(SRC)
tD, RD, _ = sk.local['Dummy01']; tW, RW, _ = sk.local['Weapon']
t = np.array(tD) + np.array(RD) @ np.array(tW); R = np.array(RD) @ np.array(RW)
def world(s, n):
    return s.fk({m: (np.array(s.local[m][0]), np.array(s.local[m][1])) for m in s.order})[n]
for conv in ('row', 'col'):
    f = NifFile(SRC)
    wi, di, hi = f.find('Weapon'), f.find('Dummy01'), f.find('Bip01 R Hand')
    d = f.node(di); d['children'] = [c for c in d['children'] if c != wi]; f.set_node(di, d)
    h = f.node(hi); h['children'] = list(h['children']) + [wi]; f.set_node(hi, h)
    w = f.node(wi); w['trans'] = tuple(float(x) for x in t)
    w['rot'] = tuple(float(x) for x in (R.reshape(-1) if conv == 'row' else R.T.reshape(-1))); f.set_node(wi, w)
    open(OUT, 'wb').write(f.to_bytes())
    s2 = Skeleton(OUT); a = world(sk, 'Weapon'); b = world(s2, 'Weapon')
    err = max(np.abs(a[0] - b[0]).max(), np.abs(a[1] - b[1]).max())
    if err < 1e-4: break
assert err < 1e-4, err
print('Weapon under', s2.parent['Weapon'], 'local', np.round(t, 2), 'world error %.2g' % err)
