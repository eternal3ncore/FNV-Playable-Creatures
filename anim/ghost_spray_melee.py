"""Ghost People gas spray as the melee forward power attack: the one- and two-handed AttackForwardPower and the
AttackCustom1-5Power that melee weapons play in its place (+ sneak) are the gas spray of ghost_spray.py (step in, rear
back, thrust and spray from the mask at the Hit, step back), built on that type's own stance - the first frame of its
aim (1hmaim / 2hmaim, + sneak), which every attack of the type starts from - with the arms keeping the stance's hold
on the weapon (they move with the leaning torso; no arm IK, hands stay closed). The customs are renamed copies of the
forward file. PlayableCreatures_GhostMelee.dll (UnarmedEffectWeapons=1) casts the race's unarmed effect on those hits.
usage: python3 -P ghost_spray_melee.py <source folder: (sneak)1hm|2hm attackforwardpower + aim> <out folder>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from ghost_spray import build
from power_fill import renamed


def run(src, dst):
    os.makedirs(dst, exist_ok=True)
    for T in ('1hm', '2hm'):
        for sn in ('', 'sneak'):
            out = os.path.join(dst, f'{sn}{T}attackforwardpower.kf')
            build(os.path.join(src, f'{sn}{T}attackforwardpower.kf'), os.path.join(src, f'{sn}{T}aim.kf'), out, arms='')
            for i in range(1, 6):
                renamed(out, os.path.join(dst, f'{sn}{T}attackcustom{i}power.kf'), f'AttackCustom{i}Power')


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
