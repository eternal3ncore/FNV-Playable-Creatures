"""Recoil for every melee type that has a BlockHit: (sneak)h2h / 1hm / 2hm recoil.kf = that type's BlockHit renamed
'Recoil' (sequence name only), where the folder has none.
Recoil (anim group 0xAC) is what the engine plays on the attacker when a melee hit bounces off (a blocking target, a power
attack meeting an attack); with no Recoil for the drawn type (and none for the generic type it falls back to) the
attack never finishes and the player can't attack again (Ghost gas spray, log: "creature has no group 02AC / 00AC").
The robots' 1HM / 2HM sets already took Recoil from BlockHit (robot_melee.py); this fills the rest.
usage: python3 -P recoil_fill.py <folder> [...]   (writes next to the BlockHit files, never over an existing Recoil)"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from power_fill import renamed


def run(folder):
    made = []
    names = {f.lower(): f for f in os.listdir(folder)}
    for low, f in sorted(names.items()):
        m = re.match(r'^((?:sneak)?(?:h2h|1hm|2hm))blockhit\.kf$', low)
        if not m or f'{m.group(1)}recoil.kf' in names: continue
        out = os.path.join(folder, f'{m.group(1)}recoil.kf')
        renamed(os.path.join(folder, f), out, 'Recoil'); made.append(os.path.basename(out))
    return made


if __name__ == '__main__':
    for d in sys.argv[1:]: print(d, run(d))
