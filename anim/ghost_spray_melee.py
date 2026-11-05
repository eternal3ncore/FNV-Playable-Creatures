"""Ghost People gas spray as the melee back power attack: the one- and two-handed AttackBackPower (+ sneak) is the gas
spray of ghost_spray.py (step in, rear back, thrust and spray from the mask at the Hit, step back), built on that
type's own stance - the first frame of its aim (1hmaim / 2hmaim, + sneak), which every attack of the type starts from -
with the unarmed spray's arm motion: both arms swing down and back at the sides, the weapon in the right hand, the
free left hand opening (the ghosts hold the spear in one hand too, as their own animations do). A weapon's back power
attack has no override group, so no AttackCustom copies; Core (UnarmedEffectWeapons=1) casts the race's unarmed effect
on those hits. The forward power attack and the AttackCustom1-5Power that melee weapons play in its place stay the
Dead Money lunge (--lunge <folder>: (sneak)1hm|2hm attackforwardpower as shipped; the customs are renamed copies).
usage: python3 -P ghost_spray_melee.py <source folder: (sneak)1hm|2hm attackbackpower + aim> <out folder> [--lunge <folder>]"""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from ghost_spray import build
from power_fill import renamed


def run(src, dst, lunge=None):
    os.makedirs(dst, exist_ok=True)
    for T in ('1hm', '2hm'):
        for sn in ('', 'sneak'):
            build(os.path.join(src, f'{sn}{T}attackbackpower.kf'), os.path.join(src, f'{sn}{T}aim.kf'),
                  os.path.join(dst, f'{sn}{T}attackbackpower.kf'), arms='LR', open_hands='L')
            if lunge:
                fw = os.path.join(lunge, f'{sn}{T}attackforwardpower.kf')
                shutil.copy(fw, os.path.join(dst, f'{sn}{T}attackforwardpower.kf'))
                for i in range(1, 6):
                    renamed(fw, os.path.join(dst, f'{sn}{T}attackcustom{i}power.kf'), f'AttackCustom{i}Power')


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    run(a[0], a[1], sys.argv[sys.argv.index('--lunge') + 1] if '--lunge' in sys.argv else None)
