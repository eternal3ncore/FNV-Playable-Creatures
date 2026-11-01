"""Throws from the creature's own throw (races that have one: Ghost People, Feral Ghoul, Super Mutant).
The procedural AttackThrow2-8 (+ Up / Down / IS variants) of build_creature swung a straight arm behind the body with
the wrist cranked back (audit: wrist ~170 deg, upper arm flipped). Every throw group the creature does not
have natively becomes a renamed copy of its own throw: same suffix (Up / Down) if it has one, else its AttackThrow7
for group 7 if it has one, else its base AttackThrow. Own files are never touched.
usage: python3 throws_native.py <deployed folder> <own anim dir> [--dry]"""
import sys, os, re, struct, glob
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from nifedit import NifFile
SUF = {'': '', 'up': 'Up', 'down': 'Down', 'is': 'IS', 'isup': 'ISUp', 'isdown': 'ISDown'}
def run(folder, own_dir, dry=False):
    own = {os.path.basename(f).lower() for f in glob.glob(os.path.join(own_dir, '1gtattackthrow*.kf'))}
    out = []
    for fn in sorted(os.listdir(folder)):
        m = re.match(r'^(sneak)?1gtattackthrow(\d?)(up|down|is|isup|isdown)?\.kf$', fn.lower())
        if not m: continue
        sneak, n, suf = m.group(1) or '', m.group(2), m.group(3) or ''
        if not sneak and fn.lower() in own: continue                      # the creature's own throw
        cands = [f'1gtattackthrow{n}{suf}.kf', f'1gtattackthrow{suf}.kf' if suf in ('up', 'down') else None,
                 f'1gtattackthrow{n}.kf', '1gtattackthrow.kf']
        src = next((c for c in cands if c and c in own), None)
        if src is None: continue
        if sneak == '' and src == fn.lower(): continue
        seq = 'AttackThrow' + n + SUF[suf]
        out.append((fn, src, seq))
        if dry: continue
        f = NifFile(os.path.join(folder, src))
        bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
        b = bytearray(f.blocks[bi]); struct.pack_into('<i', b, 0, f.str_index(seq)); f.blocks[bi] = bytes(b)
        open(os.path.join(folder, fn), 'wb').write(f.to_bytes())
    return out
if __name__ == '__main__':
    r = run(sys.argv[1], sys.argv[2], '--dry' in sys.argv)
    for x in r[:8]: print(x)
    print(len(r), 'throw files from the own throw')
