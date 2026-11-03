"""Animation priority pass for a race folder (priorities only; no pose changes).
  1. up / down variants: a bone an aim / attack up / down file keys above its level file (<group>up / down -> <group>)
     is set to the level file's priority. The engine blends a group's level, up and down files by pitch; a higher
     priority in the up / down file takes the bone over at the slightest up / down weight (Ghost 2HR hip aim: up / down
     arms at 45 over the level's 35 pulled the arms out of the hold). Weapon-part tracks (##...) are left as vanilla has them.
  2. walk / run / sneak / turn / jump files: every bone but the root and legs capped below the race's lowest weapon
     stance (loco_prio), so the arms keep the weapon's hold while moving. `auto` = (lowest UpperArm priority over the
     race's <type>aim.kf files) - 1; nothing changes where the walk is already below it.
usage: python3 -P prio_fix.py <race folder> [--loco auto|N|none]"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from nifedit import NifFile
import loco_prio

def _seq(f):
    i = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    sb = bytearray(f.blocks[i]); _, ncb, _ = struct.unpack_from('<iII', sb, 0)
    return i, sb, ncb

def priorities(path):
    f = NifFile(path); _, sb, ncb = _seq(f); out = {}
    for j in range(ncb):
        o = 12 + 29 * j; nd = struct.unpack_from('<i', sb, o + 9)[0]
        if 0 <= nd < len(f.strings): out[f.strings[nd]] = sb[o + 8]
    return out

def updown(folder):
    names = {fn.lower(): fn for fn in os.listdir(folder) if fn.lower().endswith('.kf')}
    tot = 0
    for low, fn in sorted(names.items()):
        m = re.match(r'^(.*?)(up|down)\.kf$', low)
        if not m or not re.search(r'aim|attack', low) or m.group(1) + '.kf' not in names: continue
        lvl = priorities(os.path.join(folder, names[m.group(1) + '.kf']))
        f = NifFile(os.path.join(folder, fn)); si, sb, ncb = _seq(f); n = 0
        for j in range(ncb):
            o = 12 + 29 * j; nd = struct.unpack_from('<i', sb, o + 9)[0]
            nm = f.strings[nd] if 0 <= nd < len(f.strings) else None
            if nm in lvl and not nm.startswith('##') and sb[o + 8] > lvl[nm]: sb[o + 8] = lvl[nm]; n += 1   # (weapon-part tracks: vanilla's own)
        if n:
            f.blocks[si] = bytes(sb); open(os.path.join(folder, fn), 'wb').write(f.to_bytes()); tot += n
            print('  up/down', fn, n)
    return tot

def auto_cap(folder):
    ps = []
    for fn in os.listdir(folder):
        if re.match(r'^(1hp|2hr|2ha|2hh|2hl|h2h|1hm|2hm|1gt|1md|1lm)aim\.kf$', fn.lower()):
            p = priorities(os.path.join(folder, fn))
            ps += [p[b] for b in ('Bip01 R UpperArm', 'Bip01 L UpperArm') if b in p]
    return max(1, min(ps) - 1) if ps else None

if __name__ == '__main__':
    d = sys.argv[1]; loco = sys.argv[sys.argv.index('--loco') + 1] if '--loco' in sys.argv else 'auto'
    print(os.path.basename(d.rstrip('/')), 'up/down blocks lowered', updown(d))
    if loco != 'none':
        cap = auto_cap(d) if loco == 'auto' else int(loco)
        tot = 0
        for root, _, fs in os.walk(d):
            for fn in sorted(fs):
                if fn.lower().endswith('.kf') and loco_prio.MOVE.search(fn) and not loco_prio.SKIP.search(fn):
                    tot += loco_prio.cap_file(os.path.join(root, fn), cap)
        print(os.path.basename(d.rstrip('/')), 'walk cap', cap, 'blocks capped', tot)
