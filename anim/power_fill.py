"""Missing power attacks. The engine has no fallback for a power-attack direction a creature lacks: the
player freezes. For every race / melee type (H2H, 1HM, 2HM), standing and sneak, each of AttackPower, AttackForward /
Back / Left / RightPower that has no file gets a renamed copy (sequence name only) of one of the race's own power
attacks of that type, chosen in the PLAN below: a non-lunging one (no root travel, feet planted) wherever a direction
other than forward is filled. Sneak copies come from the sneak version of the same source.
usage: python3 power_fill.py <PlayableCreatures meshes folder> [--apply]"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from nifedit import NifFile
from kf import KF

# race -> type -> {missing group: source file stem (standing; 'sneak' prefixed for the sneak copy)}
#   measured root travel / foot range of the sources (deployed set):
#   Ghost h2hattackpower 25 / 10; Ghoul *attackright / left 0 / 0 (its side / forward powers are leaps, root ~385);
#   Super Mutant h2hattackleftpower 0 / 0, h2hattackrightpower 0 / 8; Trog *attackpower 0 / 8; Zetan h2hattackpower 12 / 15
PLAN = {
    'Ghost': {'h2h': {'AttackBackPower': 'h2hattackpower', 'AttackLeftPower': 'h2hattackpower', 'AttackRightPower': 'h2hattackpower'}},
    # Ghoul: its AttackBackPower is the Glowing One's resurrect cast, not an attack -> the standing power and the
    # back power are its own regular right / left swings (root 0, Hit 0.5 s), sneak files included
    'Ghoul': {T: {'AttackPower': f'{T}attackright', 'AttackBackPower': f'{T}attackleft'} for T in ('h2h', '1hm', '2hm')},
    'SuperMutant': {'h2h': {'AttackPower': 'h2hattackleftpower', 'AttackBackPower': 'h2hattackrightpower'}},
    'Trog': {T: {'AttackBackPower': f'{T}attackpower'} for T in ('h2h', '1hm', '2hm')},
    'Zetan': {'h2h': {g: 'h2hattackpower' for g in ('AttackForwardPower', 'AttackBackPower', 'AttackLeftPower', 'AttackRightPower')}},
}


def groups(folder):
    have = set()
    for f in os.listdir(folder):
        m = re.match(r'^(sneak)?(h2h|1hm|2hm)attack.*\.kf$', f, re.I)
        if not m: continue
        try: have.add((bool(m.group(1)), m.group(2).lower(), KF(os.path.join(folder, f)).name))
        except Exception: pass
    return have


def renamed(src, dst, seq):
    f = NifFile(src)
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = bytearray(f.blocks[bi]); struct.pack_into('<i', b, 0, f.str_index(seq)); f.blocks[bi] = bytes(b)
    open(dst, 'wb').write(f.to_bytes())


def run(root, apply=False):
    rep = []; n = 0
    for race, types in PLAN.items():
        d = os.path.join(root, race); have = groups(d)
        for T, fill in types.items():
            for g, stem in fill.items():
                for sn in (False, True):
                    if (sn, T, g) in have: rep.append(f'{race} {"sneak" if sn else ""}{T} {g}: present'); continue
                    src = os.path.join(d, ('sneak' if sn else '') + stem + '.kf')
                    if not os.path.exists(src): rep.append(f'{race} {src}: source missing - skipped'); continue
                    dst = os.path.join(d, ('sneak' if sn else '') + T + g.lower() + '.kf')
                    assert not os.path.exists(dst), dst
                    rep.append(f'{race}: {os.path.basename(dst)} <- {os.path.basename(src)} [{g}]')
                    if apply: renamed(src, dst, g)
                    n += 1
    rep.append(f'{n} files')
    return rep


if __name__ == '__main__':
    for line in run(sys.argv[1], apply='--apply' in sys.argv): print(line)
