"""Aim-up / aim-down groups a creature lacks = renamed copies of the regular one. Only adds files; nothing existing is changed.
For every weapon prefix (+ sneak) in a skeleton folder's top level and every group that has Up / Down variants in the
vanilla human set (Aim, AttackLeft, AttackRight, Attack3-9, AttackLoop, AttackSpin, AttackSpin2): if the folder has the
group but no <group>Up (or Down) for that prefix, each file of the group (all its _b/_c variants) is copied as
<prefix><group>up[_x].kf with the sequence renamed <Group>Up[_X] (text keys, timing and tracks unchanged).
Pure struct (nifedit only), so it runs on the game PC too.  usage: python3 fill_updown.py <folder> [--dry]"""
import sys, os, re, struct
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from nifedit import NifFile
BASES = ['Aim', 'Attack3', 'Attack4', 'Attack5', 'Attack6', 'Attack7', 'Attack8', 'Attack9', 'AttackLeft', 'AttackLoop',
         'AttackRight', 'AttackSpin', 'AttackSpin2']
PREF = re.compile(r'^(sneak)?(h2h|1hm|2hm|1hp|2hr|2ha|2hh|2hl|1gt|1md|1lm)')
def seq_of(f):
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    return bi, f.strings[struct.unpack_from('<i', f.blocks[bi], 0)[0]]
def run(folder, dry=False):
    files = {}
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith('.kf'): continue
        m = PREF.match(fn.lower())
        if not m: continue
        f = NifFile(os.path.join(folder, fn)); _, name = seq_of(f)
        files[fn] = (m.group(0), name)
    have = {}
    for fn, (pre, name) in files.items(): have.setdefault(pre, set()).add(name.split('_')[0].lower())
    made = []
    for fn, (pre, name) in sorted(files.items()):
        base, _, var = name.partition('_')
        if base not in BASES: continue
        stem = fn.lower()[len(pre):-3]                          # e.g. attackleft_b
        if not stem.startswith(base.lower()): continue
        for d in ('Up', 'Down'):
            if (base + d).lower() in have[pre]: continue
            new_fn = pre + base.lower() + d.lower() + stem[len(base):] + '.kf'
            new_seq = base + d + (('_' + var) if var else '')
            if os.path.exists(os.path.join(folder, new_fn)): continue
            made.append((fn, new_fn, new_seq))
            if dry: continue
            f = NifFile(os.path.join(folder, fn)); bi, _ = seq_of(f)
            b = bytearray(f.blocks[bi]); struct.pack_into('<i', b, 0, f.str_index(new_seq)); f.blocks[bi] = bytes(b)
            open(os.path.join(folder, new_fn), 'wb').write(f.to_bytes())
    return made
if __name__ == '__main__':
    m = run(sys.argv[1], '--dry' in sys.argv)
    for a, b, s in m: print(f'{a:34s} -> {b:36s} {s}')
    print(len(m), 'files', '(dry run)' if '--dry' in sys.argv else 'written')
