"""Ghost People gas spray as the melee forward power attack: the one- and two-handed AttackForwardPower and the
AttackCustom1-5Power that melee weapons play in its place (+ sneak) are the gas spray of ghost_spray.py (step in, rear
back, thrust and spray from the mask at the Hit, step back), built on that type's own stance - the first frame of its
aim (1hmaim / 2hmaim, + sneak), which every attack of the type starts from - with the unarmed spray's arm motion:
one-handed, both arms swing down and back at the sides as unarmed, the weapon in the right hand, the free left hand
opening; two-handed, the right arm makes that swing and the left hand keeps its grip on the weapon (carried low at the
side). The customs are renamed copies of the forward file. PlayableCreatures_GhostMelee.dll (UnarmedEffectWeapons=1) casts the race's unarmed effect on those hits.
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
            if T == '1hm': kw = dict(arms='LR', open_hands='L')                   # the weapon swings back in the right hand
            else: kw = dict(arms='R', open_hands='', grip=True)                    # the left hand stays on the shaft
            build(os.path.join(src, f'{sn}{T}attackforwardpower.kf'), os.path.join(src, f'{sn}{T}aim.kf'), out, **kw)
            for i in range(1, 6):
                renamed(out, os.path.join(dst, f'{sn}{T}attackcustom{i}power.kf'), f'AttackCustom{i}Power')


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
