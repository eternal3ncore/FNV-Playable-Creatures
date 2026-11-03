"""Mirelurk (Tale of Two Wastelands: Mirelurk, Mirelurk Hunter, Nukalurk) - creature config for the weapon-set builder.
Vanilla Creatures\\Mirelurk\\skeleton.nif: a crab - Bip01 biped body carried low on two digitigrade legs (Thigh..Toe1)
plus four side legs (Bip01 Ponytail1-4 / 5-8 / 9-12 / 13-16 under Spine1), a tail, pincer claws (Hand + Finger0 = the
moving jaw), a Weapon node under the right claw. Own set: H2H (aim, left / right claw strikes, four power attacks,
equips, recoil), 2HL (aim, its lunge AttackSpin, equips) + walk / run / backward / strafe / turn locomotion (+ hurt).
One- and two-handed melee weapons strike with its own claw attacks (weapon unseen, as the deathclaw); guns are built
here only for their names / timing - mouth_fire.py replaces every gun file with its own 2HL lunge, claws raised, the
shot from its mouth (gun unseen). No thrown weapons or mines (nothing to throw them with)."""
from creatures._ttw import bones, variants, families, LAUNCHER_ROT
NAME = 'Mirelurk'
ANIM_SRC = '/home/claude/fnv/creature_src_lurk/meshes/creatures/mirelurk'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1'], ['Bip01 Neck'])
GRASP = (12.0, 0.0, 0.0)
CURL_AXIS = (0, 0, 1)
POLE_R = (2, -6, -30)
POLE_L = (0, -40, -30)
POUCH = (-10, 6, -30)
JUMP_SCALE = 0.5
NATIVE = {'h2h': ['h2haim.kf'] * 6, '1hm': ['h2haim.kf'] * 6, '2hm': ['h2haim.kf'] * 6}
HOLD = dict(wpos=(-8, -16, -6), pitch=30)
GUN1, GUN2, HEAVY, LAUNCHER = families()
SYN2HR = dict(base='h2haim.kf', wpos=(7.6, 30.0, -10.0), grip=None, variants=variants(dict(wpos=(-1.7, 0.8, 12.0), head=10)))
SYN1HP = dict(base='h2haim.kf', wpos=(8.9, 32.0, -8.0), grip=None, variants=variants(dict(wpos=(-4.3, 2.8, 10.0), head=6)))
WEAPON_TYPES = {
    'h2h': dict(),
    '1hm': dict(src='h2h', copy_attacks=True),
    '2hm': dict(src='h2h', copy_attacks=True),
    '1hp': dict(synth=SYN1HP, equip_from='h2h', family=GUN1, ranged=True),
    '2hr': dict(synth=SYN2HR, equip_from='h2h', family=GUN2, ranged=True),
    '2ha': dict(src='2hr', family=GUN2, ranged=True),
    '2hh': dict(src='2hr', family=HEAVY, ranged=True),
    '2hl': dict(src='2hr', family=LAUNCHER, ranged=True, weapon_rot=LAUNCHER_ROT),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL'
# furniture (eyebot_furniture.py ... mirelurk): no seated pose of its own - it climbs onto the seat and stands on it, its
# idle playing (head height above the seat = its standing head height above the floor)
SPHERE_LOW = 120.4
SIT_ANIMATED = True
