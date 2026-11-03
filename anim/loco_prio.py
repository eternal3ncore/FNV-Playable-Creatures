"""Locomotion / jump files: upper-body priorities capped below every weapon stance.
A walking / running / sneaking / turning / jumping file that keys the spine, neck, head, arms, fingers or the Weapon node at
a priority at or above a weapon type's aim (Ghost: Dead Money's mtforward arms 45, h2hforward 46, the 1GT walks 46-48,
vs 2HR / 2HA aims 35) takes the arms over whenever the creature moves with a weapon out and isn't aiming: the arms swing
with the walk and the off hand leaves the gun. Every bone but the root and legs is capped at CAP (above the idle's 20, so
with nothing out the walk still drives the arms; below the lowest aim, 25). Legs, pelvis and the root are untouched.
Dodges / hops (full-body moves that must win) are skipped.
usage: python3 -P loco_prio.py <race folder> [cap=22]   (in place; prints what changed)"""
import os, re, struct, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nifedit import NifFile

LOWER = re.compile(r'^Bip01( NonAccum| Pelvis| [LR] (Thigh|Calf|Foot|Toe0))?$')
MOVE = re.compile(r'(forward|backward|left|right|turnleft|turnright)\.kf$|jump', re.I)
SKIP = re.compile(r'dodge|attack|block|aim|equip|holster|reload|jam|idle', re.I)

def cap_file(path, cap):
    f = NifFile(path)
    seq = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    sb = bytearray(f.blocks[seq]); _, ncb, _ = struct.unpack_from('<iII', sb, 0); n = 0
    for j in range(ncb):
        o = 12 + 29 * j; nd = struct.unpack_from('<i', sb, o + 9)[0]
        name = f.strings[nd] if 0 <= nd < len(f.strings) else ''
        if LOWER.match(name) or sb[o + 8] <= cap: continue
        sb[o + 8] = cap; n += 1
    if n:
        f.blocks[seq] = bytes(sb); open(path, 'wb').write(f.to_bytes())
    return n

if __name__ == '__main__':
    root = sys.argv[1]; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    tot = 0
    for d, _, fs in os.walk(root):
        for fn in sorted(fs):
            if not fn.lower().endswith('.kf') or not MOVE.search(fn) or SKIP.search(fn): continue
            n = cap_file(os.path.join(d, fn), cap); tot += n
            if n: print(os.path.relpath(os.path.join(d, fn), root), n)
    print('blocks capped', tot)
