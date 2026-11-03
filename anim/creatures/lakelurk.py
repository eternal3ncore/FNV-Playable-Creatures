"""Lakelurk (New Vegas: Lakelurk, Alpha Male Lakelurk) - creature config for the procedural weapon-set builder.
Vanilla Creatures\\MirelurkKing\\skeleton.nif (shared with the Mirelurk King): Bip01 biped ~1.2x human, upright idle,
crouched aims, digitigrade legs (four toes), four three-joint fingers per hand, a Weapon node under the right hand
(Dummy01) and ProjectileNode_Sonic on the head (Dummy01_HeadSonic: the shriek). Own set: H2H (aim, five left / right
swings, two power attacks, equips, side steps), 2HL (the shriek: aim, AttackRight, equip / unequip) + walk / run /
backward / turn locomotion (+ hurt). Melee weapons swing with its own claw attacks (weapon hidden, as the deathclaw);
guns are built here only for their names / timing - lakelurk_shriek.py replaces every gun file with its own shriek
(gun hidden, shot from the mouth); thrown weapons and mines are synthetic holds in its claw."""
from creatures._ttw import bones, variants, families, LAUNCHER_ROT
NAME = 'Lakelurk'
ANIM_SRC = '/home/claude/fnv/creature_src_lurk/meshes/creatures/mirelurkking'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], ['Bip01 Neck', 'Bip01 Neck1'])
S = 1.2                                  # body scale vs the human-sized configs (head 132.7 in its idle vs 111.6)
sc = lambda v: tuple(round(x * S, 2) for x in v)
GRASP = (10.0, 0.0, 0.0)                 # claw: palm point between the hand and the finger roots (fingers at x 14.5)
CURL_AXIS = (0, 0, 1)
POLE_R = sc((2, -6, -30))
POLE_L = sc((0, -40, -30))
POUCH = sc((-10, 6, -30))
HOLD = dict(wpos=sc((-8, -16, -6)), pitch=30)
THROW = dict(wind=dict(wpos=sc((-6, -26, 34)), pitch=50, lean=-8, twist=20, head=-5),
             rel=dict(wpos=sc((-14, 14, 32)), pitch=10, lean=12, twist=-12, head=5),
             follow=dict(wpos=sc((-26, 16, 6)), pitch=-20, lean=16, twist=-20, head=8))
PLACE = dict(wpos=sc((-12, 10, -26)), pitch=-40, lean=35, head=25)
JUMP_SCALE = 0.8
SNEAK_DROP = 0.3
SNEAK_LEAN = 15.0
GUN1, GUN2, HEAVY, LAUNCHER = families(S)
NATIVE = {'h2h': ['h2haim.kf'] * 6, '1hm': ['h2haim.kf'] * 6, '2hm': ['h2haim.kf'] * 6}
SYN2HR = dict(base='h2haim.kf', wpos=sc((7.6, 30.0, -10.0)), grip=(10.0, -2.0, 0.0), curl=0.6,
              variants=variants(dict(wpos=(-1.7, 0.8, 12.0), head=10), S))
SYN1HP = dict(base='h2haim.kf', wpos=sc((8.9, 32.0, -8.0)), grip=None, variants=variants(dict(wpos=(-4.3, 2.8, 10.0), head=6), S))
WEAPON_TYPES = {
    'h2h': dict(),
    '1hm': dict(src='h2h', copy_attacks=True),
    '2hm': dict(src='h2h', copy_attacks=True),
    '1hp': dict(synth=SYN1HP, equip_from='h2h', family=GUN1, ranged=True),
    '2hr': dict(synth=SYN2HR, equip_from='h2h', family=GUN2, ranged=True),
    '2ha': dict(src='2hr', family=GUN2, ranged=True),
    '2hh': dict(src='2hr', family=HEAVY, ranged=True),
    '2hl': dict(src='2hr', family=LAUNCHER, ranged=True, weapon_rot=LAUNCHER_ROT),
    '1gt': dict(src='1hp', thrown=True, equip_from='h2h'),
    '1md': dict(src='1hp', mine=True, equip_from='h2h'),
    '1lm': dict(src='1hp', mine=True, equip_from='h2h'),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
SIT_HAND_MIN = 55.0                       # furniture: below this the long arms rest along the thighs
