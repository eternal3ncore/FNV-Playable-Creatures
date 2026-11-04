"""Missing power attacks (and AttackCustom1-5Power, see fill_custom). The engine has no fallback for a power-attack direction a creature lacks: the
player freezes. For every race / melee type (H2H, 1HM, 2HM), standing and sneak, each of AttackPower, AttackForward /
Back / Left / RightPower that has no file gets a renamed copy (sequence name only) of one of the race's own power
attacks of that type, chosen in the PLAN below: a non-lunging one (no root travel, feet planted) wherever a direction
other than forward is filled. Sneak copies come from the sneak version of the same source.
usage: python3 power_fill.py <PlayableCreatures meshes folder> [--apply]"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))   # parent last: it has a dis.py
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
    'SuperMutantDC': {'h2h': {'AttackPower': 'h2hattackleftpower', 'AttackBackPower': 'h2hattackrightpower'}},   # TTW: Fallout 3's own
    'Trog': {T: {'AttackBackPower': f'{T}attackpower'} for T in ('h2h', '1hm', '2hm')},
    'Zetan': {'h2h': {g: 'h2hattackpower' for g in ('AttackForwardPower', 'AttackBackPower', 'AttackLeftPower', 'AttackRightPower')}},
    # Deathclaw: own forward / left / right power attacks only; its side powers are in-place swings (no root travel)
    'Deathclaw': {T: {'AttackPower': f'{T}attackrightpower', 'AttackBackPower': f'{T}attackleftpower'} for T in ('h2h', '1hm', '2hm')},
    # Mirelurk: own standing / forward / left / right powers; the standing one (in place) fills the back power
    'Mirelurk': {T: {'AttackBackPower': f'{T}attackpower'} for T in ('h2h', '1hm', '2hm')},
    # Lakelurk: own standing and forward powers only; the standing one fills back / left / right
    'Lakelurk': {T: {g: f'{T}attackpower' for g in ('AttackBackPower', 'AttackLeftPower', 'AttackRightPower')} for T in ('h2h', '1hm', '2hm')},
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
        d = os.path.join(root, race)
        if not os.path.isdir(d): continue            # race folder not in this tree (one pack built at a time)
        have = groups(d)
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
    n += fill_custom(root, rep, apply)
    rep.append(f'{n} files')
    return rep


CUSTOM = range(1, 6)
# melee weapons only ever replace the forward power attack; unarmed (no weapon or an Unarmed-skill weapon) the special-move
# perks replace each direction: forward 0x61 (entry 0x3D), back 0x62 (0x3E), left 0x64 (0x41), right 0x65 (0x42), and
# the sneaking power attack 0x63 (0x3F) - so the unarmed ones are the race's own power attack of that direction
CUSTOM_SRC = {'h2h': {1: 'attackforwardpower', 2: 'attackbackpower', 3: 'attackpower', 4: 'attackleftpower', 5: 'attackrightpower'},
              '1hm': {i: 'attackforwardpower' for i in CUSTOM}, '2hm': {i: 'attackforwardpower' for i in CUSTOM}}


def fill_custom(root, rep, apply=False, replace=()):
    """AttackCustom1-5Power for H2H / 1HM / 2HM, standing and sneak, in every race folder under root. Vanilla melee
    weapons replace the forward power attack with one of them (WEAP DNAM power attack override = weapon +0x198: the
    player's forward group 0x5D becomes it unless 0xFF, PlayerCharacter 0x949AB2; machete / knife -> Custom3, lead pipe /
    sledgehammer -> Custom2, Dead Money 2HM -> Custom4, chainsaw -> Custom5...), and the perk moves pick them too (0x949B5C).
    A missing group stops the attack, so the forward power attack did nothing with those weapons. Each missing one = a
    renamed copy of the type's own power attack (CUSTOM_SRC: 1HM / 2HM the forward one; unarmed the perk's direction;
    sneak from sneak). replace: (race, type) whose existing ones are rewritten as well."""
    n = 0
    for race in sorted(os.listdir(root)):
        d = os.path.join(root, race)
        if not os.path.isdir(d): continue
        for T in ('h2h', '1hm', '2hm'):
            for sn in ('', 'sneak'):
                for i in CUSTOM:
                    src = os.path.join(d, f'{sn}{T}{CUSTOM_SRC[T][i]}.kf')
                    if not os.path.exists(src): continue
                    dst = os.path.join(d, f'{sn}{T}attackcustom{i}power.kf')
                    if os.path.exists(dst) and (race, T) not in replace: continue
                    rep.append(f'{race}: {os.path.basename(dst)} <- {os.path.basename(src)} [AttackCustom{i}Power]')
                    if apply: renamed(src, dst, f'AttackCustom{i}Power')
                    n += 1
    return n


if __name__ == '__main__':
    for line in run(sys.argv[1], apply='--apply' in sys.argv): print(line)
