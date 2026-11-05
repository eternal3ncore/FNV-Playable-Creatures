"""Super Mutant / Nightkin / Capital (TTW) Super Mutant one-handed melee = their own unarmed set, the weapon unseen
(as the robots' melee, robot_melee.py + weapon_hide.py). Neither New Vegas nor Fallout 3 ships a super mutant 1HM set;
every (sneak)1hm*.kf is written as a copy of the folder's H2H file for the same move (sneak from sneak), sequence name
set to the 1HM group, and the Weapon node is keyed at scale 0.001 in each (weapon_hide.run, melee) - the weapon is
drawn and swung unseen with the punches, its reach / damage / enchantment still applying.
  aims / blocks / recoil / equip / unequip / holster / powers <- the H2H file of the same name
  AttackLeft / Right (Up / Down) _A and _B <- the H2H _A / _B file (_A when the folder has no _B, e.g. sneak)
  AttackCustom1-5Power <- AttackForwardPower (melee weapons play these in place of the forward power attack)
The old 1HM files (left from the 2HM set / the human transfer) are replaced; 1HM files with no H2H source are reported.
usage: python3 -P sm_1hm.py <folder with the pack's files: Skeleton.nif, (sneak)h2h*.kf> <out folder>"""
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from power_fill import renamed
import weapon_hide

PLAN = {   # 1HM file stem -> (sequence name, H2H source stems in order of preference)
    'aim': ('Aim', ['aim']), 'aimdown': ('AimDown', ['aimdown']), 'aimup': ('AimUp', ['aimup']),
    'blockhit': ('BlockHit', ['blockhit']), 'blockidle': ('BlockIdle', ['blockidle']), 'recoil': ('Recoil', ['recoil', 'blockhit']),
    'equip': ('Equip', ['equip']), 'unequip': ('Unequip', ['unequip']), 'holster': ('Holster', ['holster']),
    'attackpower': ('AttackPower', ['attackpower']), 'attackforwardpower': ('AttackForwardPower', ['attackforwardpower']),
    'attackbackpower': ('AttackBackPower', ['attackbackpower']), 'attackleftpower': ('AttackLeftPower', ['attackleftpower']),
    'attackrightpower': ('AttackRightPower', ['attackrightpower']),
}
for i in range(1, 6): PLAN[f'attackcustom{i}power'] = (f'AttackCustom{i}Power', ['attackforwardpower'])
for side in ('Left', 'Right'):
    for v in ('', 'Up', 'Down'):
        for ab in ('a', 'b'):
            st = f'attack{side}{v}'.lower()
            PLAN[f'{st}_{ab}'] = (f'Attack{side}{v}', [f'{st}_{ab}', f'{st}_a', st])


def build(folder, out):
    os.makedirs(out, exist_ok=True)
    made, miss = [], []
    for sn in ('', 'sneak'):
        for stem, (seq, srcs) in PLAN.items():
            src = next((os.path.join(folder, f'{sn}h2h{s}.kf') for s in srcs if os.path.exists(os.path.join(folder, f'{sn}h2h{s}.kf'))), None)
            if not src: miss.append(f'{sn}1hm{stem}'); continue
            renamed(src, os.path.join(out, f'{sn}1hm{stem}.kf'), seq); made.append(f'{sn}1hm{stem}.kf')
    weapon_hide.run(out, os.path.join(folder, 'Skeleton.nif'), {}, ['1hm'])
    return made, miss


if __name__ == '__main__':
    made, miss = build(sys.argv[1], sys.argv[2])
    print(len(made), 'files; no H2H source for', miss)
