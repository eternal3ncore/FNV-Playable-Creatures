"""One- and two-handed melee for robots without a melee set (Eyebot, Protectron, Robobrain, Securitron, Sentry Bot):
every 1HM / 2HM group (the human set's group names, as Mister Handy's) is a renamed copy (sequence name only) of the
robot's own H2H file for that move, sneak from sneak. Their H2H files already key the Weapon node at scale 0.001
(weapon_hide.py), so the melee weapon is drawn and swung unseen with the unarmed attack.
  aims / blocks / equip / unequip / holster / powers  <- the H2H file of the same name
  AttackLeft_A / _B (Up / Down)   <- AttackLeft (Up / Down);   AttackRight_A / _B (Up / Down) <- AttackRight (Up / Down)
  AttackCustom1-5Power            <- AttackForwardPower (melee weapons put these in place of the forward power attack,
                                     see power_fill.fill_custom);   AttackSpin (Up / Down) <- AttackRight (Up / Down)
  Recoil                          <- BlockHit
No 1HM / 2HM Idle: the H2H set has none either (the robot's own idle plays).
usage: python3 robot_melee.py <robot folder> [...]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from power_fill import renamed

PLAN = {   # file stem after the type prefix -> (sequence name, H2H source stem)
    'aim': ('Aim', 'aim'), 'aimdown': ('AimDown', 'aimdown'), 'aimup': ('AimUp', 'aimup'),
    'blockhit': ('BlockHit', 'blockhit'), 'blockidle': ('BlockIdle', 'blockidle'), 'recoil': ('Recoil', 'blockhit'),
    'equip': ('Equip', 'equip'), 'unequip': ('Unequip', 'unequip'), 'holster': ('Holster', 'holster'),
    'attackpower': ('AttackPower', 'attackpower'), 'attackforwardpower': ('AttackForwardPower', 'attackforwardpower'),
    'attackbackpower': ('AttackBackPower', 'attackbackpower'), 'attackleftpower': ('AttackLeftPower', 'attackleftpower'),
    'attackrightpower': ('AttackRightPower', 'attackrightpower'),
    'attackcustom1power': ('AttackCustom1Power', 'attackforwardpower'), 'attackcustom2power': ('AttackCustom2Power', 'attackforwardpower'),
    'attackcustom3power': ('AttackCustom3Power', 'attackforwardpower'), 'attackcustom4power': ('AttackCustom4Power', 'attackforwardpower'),
    'attackcustom5power': ('AttackCustom5Power', 'attackforwardpower'),
    'attackspin': ('AttackSpin', 'attackright'), 'attackspinup': ('AttackSpinUp', 'attackrightup'),
    'attackspindown': ('AttackSpinDown', 'attackrightdown'),
}
for side in ('Left', 'Right'):
    for v in ('', 'Up', 'Down'):
        for ab in ('A', 'B'):
            PLAN[f'attack{side}{v}_{ab}'.lower()] = (f'Attack{side}{v}_{ab}', f'attack{side}{v}'.lower())


def run(folder):
    n = 0; miss = []
    for T in ('1hm', '2hm'):
        for sn in ('', 'sneak'):
            for stem, (seq, src) in PLAN.items():
                s = os.path.join(folder, f'{sn}h2h{src}.kf')
                if not os.path.exists(s): miss.append(os.path.basename(s)); continue
                renamed(s, os.path.join(folder, f'{sn}{T}{stem}.kf'), seq); n += 1
    print(os.path.basename(os.path.normpath(folder)), n, 'files', 'missing sources:', sorted(set(miss)))


if __name__ == '__main__':
    for f in sys.argv[1:]: run(f)
