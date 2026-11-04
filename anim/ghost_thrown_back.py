"""Ghost People thrown weapons sheathed on the back again. holster_fix.py (2026-10-30) gave every weapon type the human
holster spot, which put the ghosts' grenades / throwing spears (1GT) on the hip; Dead Money's own 1GT files sheathe
them on the back (prn Bip01 Spine2, the spear's 2HM spot), and the Ghost's 1GT equip / unequip / holster are those
files' body motion. Their Weapon channel and prn keys are put back as Dead Money's (sampled at 30 fps), standing and
sneak (the sneak files carry the standing upper body). holster_fix.OWN_SPOT keeps 1GT out of its pass from now on.
usage: python3 -P ghost_thrown_back.py <Dead Money ghosts folder> <Ghost anim folder> [--apply]"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KFEval
from holster_fix import KFFile, prn_keys, times


def run(vdir, folder, apply=False):
    for sn in ('', 'sneak'):
        for kind in ('equip', 'unequip', 'holster'):
            fn = f'{sn}1gt{kind}.kf'; path = os.path.join(folder, fn)
            if not os.path.exists(path): print(fn, 'missing'); continue
            v = KFEval(os.path.join(vdir, f'1gt{kind}.kf')); k = KFEval(path)
            if abs((v.stop - v.start) - (k.stop - k.start)) > 1e-3: print(fn, 'length differs from Dead Money - skipped'); continue
            vp = prn_keys(v); kp = prn_keys(k)
            if [round(t, 3) for t, _ in vp] != [round(t, 3) for t, _ in kp]: print(fn, 'prn times differ - skipped', vp, kp); continue
            kf = KFFile(path)
            for (_, cur), (_, want) in zip(kp, vp):
                if cur != want: kf.set_prn(cur, want)
            keys = [(t, np.array(v.sample(t)['Weapon'][0]), np.array(v.sample(t)['Weapon'][1])) for t in times(v)]
            kf.set_weapon(keys if kind != 'holster' else keys[:1])
            print(fn, 'prn', [b for _, b in kp], '->', [b for _, b in vp], '; Weapon = Dead Money', len(keys), 'keys')
            if apply: kf.save()


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], '--apply' in sys.argv)
