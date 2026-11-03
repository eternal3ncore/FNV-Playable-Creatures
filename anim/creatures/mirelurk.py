"""Mirelurk (Tale of Two Wastelands: Mirelurk, Mirelurk Hunter, Nukalurk) - creature config for the weapon-set builder.
Vanilla Creatures\\Mirelurk\\skeleton.nif: a crab - Bip01 biped body on two digitigrade legs (Thigh..Toe1), four
mouthpart / feeler chains around the face (Bip01 Ponytail1-4 / 5-8 / 9-12 / 13-16 under Spine1), a tail, pincer claws
(Hand + Finger0 = the moving jaw), a Weapon node under the right claw. Own set: H2H (aim, left / right claw strikes, four power attacks,
equips, recoil), 2HL (aim, its lunge AttackSpin, equips) + walk / run / backward / strafe / turn locomotion (+ hurt).
One- and two-handed melee weapons strike with its own claw attacks (weapon unseen, as the deathclaw); guns are built
here only for their names / timing - mouth_fire.py replaces every gun file with its own 2HL lunge, claws raised, the
shot from its mouth (gun unseen). Grenades and mines are launched from the right pincer with its own H2H strike
(mouth_fire.py: every 1GT / 1MD / 1LM aim = its fighting stance, every throw / placement = its claw strike, the
grenade released at the strike's Hit)."""
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
SNEAK_DROP = 0.25                # crouched sneak (gen_loco_ttw crouch): its two legs fold
SNEAK_LEAN = 10.0
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
    '1gt': dict(src='1hp', thrown=True, equip_from='h2h'),
    '1md': dict(src='1hp', mine=True, equip_from='h2h'),
    '1lm': dict(src='1hp', mine=True, equip_from='h2h'),
}
THROW = dict(wind=dict(wpos=(-6, -26, 34), pitch=50, lean=-8, twist=20, head=-5),       # (builder only: the throws are
             rel=dict(wpos=(-14, 14, 32), pitch=10, lean=12, twist=-12, head=5),          #  replaced by its claw strike)
             follow=dict(wpos=(-26, 16, 6), pitch=-20, lean=16, twist=-20, head=8))
PLACE = dict(wpos=(-12, 10, -26), pitch=-40, lean=35, head=25)
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
# furniture (eyebot_furniture.py ... mirelurk): no seated pose of its own - it climbs onto the seat and stands on it, its
# idle playing (head height above the seat = its standing head height above the floor)
SPHERE_LOW = 120.4
SIT_ANIMATED = True
