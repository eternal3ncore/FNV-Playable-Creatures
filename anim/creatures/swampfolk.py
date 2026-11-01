"""Swampfolk (Point Lookout Hillfolk2and3 skeleton: Brawler, Scrapper, Creeper) - creature config.
Human-sized Bip01 biped, long arms. Own set: H2H, 1HM, 2HM, 2HR (aims +-, Attack3/5/6, AttackRight, ReloadA/C/E/G,
JamA/C/E/G, equips) + walk/run/strafe/turn locomotion. Missing: 1HP (synthetic hold), 2HA/2HH/2HL (from its own
2HR), 1GT / 1MD / 1LM (chest hold from the 1HP hold), power attacks (its own swings), reload / attack groups the
other guns need (procedural, vanilla timing and sounds)."""
from creatures._ttw import SRC, bones, variants, families, LAUNCHER_ROT
NAME = 'Swampfolk'
ANIM_SRC = SRC + '/swampfolk'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], ['Bip01 Neck', 'Bip01 Neck1'])
GRASP = (7.0, 0.0, 0.0)
CURL_AXIS = (0, 0, 1)
POLE_R = (8, -4, -8)
POLE_L = (-6, 0, -10)
POUCH = (-10, 6, -18)
HOLD = dict(wpos=(-8, -22, -10), pitch=30)
GUN1, GUN2, HEAVY, LAUNCHER = families()
NATIVE = {'h2h': ['h2haim.kf'] * 6, '1hm': ['1hmaim.kf'] * 6, '2hm': ['2hmaim.kf'] * 6,
          '2hr': ['2hraim.kf', '2hraimup.kf', '2hraimdown.kf'] * 2}
SYN1HP = dict(base='mtidle.kf', wpos=(8, 34, 2), grip=None, variants=variants(dict(wpos=(-8, -6, 8), head=6)))
WEAPON_TYPES = {
    'h2h': dict(power_src='h2hattackright.kf'),
    '1hm': dict(power_src='1hmattackright.kf'),
    '2hm': dict(power_src='2hmattackright.kf'),
    '2hr': dict(family=GUN2, ranged=True),
    '2ha': dict(src='2hr', family=GUN2, ranged=True),
    '2hh': dict(src='2hr', family=HEAVY, ranged=True),
    '2hl': dict(src='2hr', family=LAUNCHER, ranged=True, weapon_rot=LAUNCHER_ROT),
    '1hp': dict(synth=SYN1HP, equip_from='1hm', family=GUN1, ranged=True),
    '1gt': dict(src='1hp', thrown=True, equip_from='1hm'),
    '1md': dict(src='1hp', mine=True, equip_from='1hm'),
    '1lm': dict(src='1hp', mine=True, equip_from='1hm'),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
