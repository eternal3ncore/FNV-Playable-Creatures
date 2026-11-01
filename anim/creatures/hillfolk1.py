"""Swampfolk Tracker / Bruiser (Point Lookout Hillfolk1 skeleton) - creature config.
Big Bip01 biped (~1.2x human height, arms ~1.5x), three-fingered left hand. Own set: H2H (aim, 5 swings, power), 2HM
(aim, swings, powers, equips) + walk/run/strafe/turn locomotion (sources normalized by prep_ttw.py). Missing: 1HM
(its own 2HM set with the off arm free), all guns (synthetic holds on its idle), throws / mines (chest hold),
procedural attacks / reloads / jams (vanilla timing and sounds)."""
from creatures._ttw import SRC, bones, variants, families, sc, LAUNCHER_ROT
NAME = 'Swampfolk (Hillfolk1)'
ANIM_SRC = SRC + '/hillfolk1'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], ['Bip01 Neck', 'Bip01 Neck1'])
S = 1.25
GRASP = (9.0, 0.0, 0.0)
CURL_AXIS = (0, 0, 1)
POLE_R = sc((8, -4, -8), S)
POLE_L = sc((-6, 0, -10), S)
POUCH = sc((-10, 6, -18), S)
HOLD = dict(wpos=sc((-8, -22, -10), S), pitch=30)
GUN1, GUN2, HEAVY, LAUNCHER = families(S)
NATIVE = {'h2h': ['h2haim.kf'] * 6, '2hm': ['2hmaim.kf'] * 6}
# (shoulders ~14 above Spine2: the guns sit lower and closer than on the human-sized configs, ~0.8 arm length)
SYN2HR = dict(base='mtidle.kf', wpos=(4, 26, -10), grip=(13.0, -2.0, 0.0), curl=0.6,
              variants=variants(dict(wpos=(4, 2, 9), head=10), S))
SYN1HP = dict(base='mtidle.kf', wpos=(8, 30, -6), grip=None, variants=variants(dict(wpos=(-8, -6, 8), head=6), S))
WEAPON_TYPES = {
    'h2h': dict(power_src='h2hattackrightpower.kf'),
    '2hm': dict(power_src='2hmattackrightpower.kf'),
    '1hm': dict(release_from='2hm', equip_from='2hm', power_src='1hmattackrightpower.kf'),
    '1hp': dict(synth=SYN1HP, equip_from='2hm', family=GUN1, ranged=True),
    '2hr': dict(synth=SYN2HR, equip_from='2hm', family=GUN2, ranged=True),
    '2ha': dict(src='2hr', family=GUN2, ranged=True),
    '2hh': dict(src='2hr', family=HEAVY, ranged=True),
    '2hl': dict(src='2hr', family=LAUNCHER, ranged=True, weapon_rot=LAUNCHER_ROT),
    '1gt': dict(src='1hp', thrown=True, equip_from='2hm'),
    '1md': dict(src='1hp', mine=True, equip_from='2hm'),
    '1lm': dict(src='1hp', mine=True, equip_from='2hm'),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
