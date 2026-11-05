"""Super Mutant / Nightkin / Capital (TTW) Super Mutant 1HM set from the human 1HM animations.
Neither New Vegas nor Fallout 3 ships a super mutant 1HM set; the packs had the mutant's own 2HM set with the off arm
free (anim/creatures/supermutant.py '1hm' release_from 2hm), which reads as two-handed swings. This rebuilds the
aim / attack / power files from the vanilla human 1HM files (ref_male) with xfer_human.transfer:
  * the creature's own trunk, neck, head and legs from the folder's idle (sneak: its crouched sneak idle), the human
    trunk's turn / lean in each swing spread over its spine (spine_ref = the human 1hmaim);
  * the hands where the human hands are from the shoulders, scaled by the arm-length ratio (REACH: mutant arm / human),
    arms by IK with the human elbows as poles; fingers and the Weapon node from the human file;
  * priorities / timing / Hit / swing-sound keys from the human file; the mutant's own attack vocal
    (Sound: PCSuperMutantAttackVox at 0, as its old files) kept where the old file had it;
  * fingers keep the mutant's own bone offsets (its hand is ~2.4x the human's), the Weapon node = the mutant's own grip
    point + the human's offset from the human grip point x the arm ratio, the human's orientation in the hand;
  * sequence names as the folder's old files ('AttackRight' for 1hmattackright_a.kf etc. - they play in game);
  * AttackCustom4 / 5Power = the forward power renamed (as power_fill.fill_custom); blocks, equip / unequip / holster
    stay the folder's own. Files: every (sneak)1hm*.kf the folder has except those.
usage: python3 -P sm_1hm.py <folder with the pack's files: skeleton.nif, mtidle.kf, sneakmtidle.kf, (sneak)1hm*.kf> <out>"""
import os, sys, re, types, importlib, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from rig import Creature, write_kf
from kf import KF, Skeleton
from xfer_human import transfer, HUMAN_SKEL

REF = '/home/claude/fnv/ref_male'
KEEP = re.compile(r'^(sneak)?1hm(block|equip|unequip|holster)')
VOX = 'Sound: PCSuperMutantAttackVox'


def arm_len(sk):
    W = sk.fk()
    return np.linalg.norm(W['Bip01 R Forearm'][0] - W['Bip01 R UpperArm'][0]) + np.linalg.norm(W['Bip01 R Hand'][0] - W['Bip01 R Forearm'][0])


def build(folder, out):
    os.makedirs(out, exist_ok=True)
    g = importlib.import_module('creatures.supermutant')
    made = []
    for sneak in (False, True):
        cfg = types.SimpleNamespace(**{k: getattr(g, k) for k in dir(g) if k.isupper()})
        cfg.ANIM_SRC = folder; cfg.SKELETON = os.path.join(folder, 'skeleton.nif')
        cfg.IDLE_KF = 'sneakmtidle.kf' if sneak else 'mtidle.kf'; cfg.TEMPLATE_KF = '1hmaim.kf'
        cfg.__name__ = 'sm1hm'
        cr = Creature(cfg)
        reach = arm_len(cr.sk) / arm_len(Skeleton(HUMAN_SKEL))
        pre = 'sneak' if sneak else ''
        hs = Skeleton(HUMAN_SKEL)
        wbind = np.array(cr.sk.local['Weapon'][0], float); hbind = np.array(hs.local['Weapon'][0], float)
        fingers = [n for side in 'LR' for n in cr.fingers[side] if n in cr.sk.local]
        for f in sorted(os.listdir(folder)):
            if not re.match(rf'^{pre}1hm.*\.kf$', f) or (not sneak and f.startswith('sneak')) or KEEP.match(f): continue
            old = KF(os.path.join(folder, f))
            hf = f[len(pre):]
            if re.match(r'1hmattackcustom[45]power\.kf$', hf): hf = '1hmattackforwardpower.kf'
            hp = os.path.join(REF, hf)
            if not os.path.exists(hp): print('no human file for', f); continue
            fr, bones, L, keys, cyc, seq = transfer(cr, hp, os.path.join(REF, '1hmaim.kf'), spine_ref=os.path.join(REF, '1hmaim.kf'), reach=reach)
            # fingers / Weapon came over as the human's local transforms: keep the mutant's own finger offsets (its hand is
            # ~2.4x the human's) and put the weapon at the mutant's own grip point plus the human's grip offset, scaled
            for _, loc in fr:
                for nm in fingers:
                    loc[nm] = (np.array(cr.sk.local[nm][0], float), loc[nm][1])
                t, R = loc['Weapon']; loc['Weapon'] = (wbind + (t - hbind) * reach, R)
            keys = [(t, v) for t, v in keys if 'GlobalRatio' not in v]
            if any(v == VOX for _, v in old.textkeys) and not any(v == VOX for _, v in keys):
                keys.insert(1, (0.0, VOX))
            write_kf(cr, os.path.join(out, f), old.name, L, keys, fr, bones=bones, cycle=cyc)
            made.append((f, old.name, round(L, 2), len(fr)))
    return made, reach


if __name__ == '__main__':
    made, reach = build(sys.argv[1], sys.argv[2])
    print('reach x%.3f' % reach)
    for m in made: print(m)
