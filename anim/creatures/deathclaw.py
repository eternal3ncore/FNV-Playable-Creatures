"""Deathclaw - creature config for the procedural weapon-set builder.
Vanilla Creatures\\DeathClaw\\skeleton.nif: Bip01 biped ~1.5x human, hunched, digitigrade legs (thigh, calf, foot,
three toes), long arms, five two-joint claws per hand; a Weapon node under the right hand. Own set: H2H (aim, left /
right swings with _b variants, three power attacks, equip / unequip / holster, recoil) + walk / run / strafe / turn
locomotion (+ hurt). Melee weapons swing with its own claw attacks (the weapon in the right claw), two-handed melee
too (as the trog); guns, throws and mines are synthetic holds on its own idle, procedural attacks / reloads / jams with
vanilla timing and sounds."""
from creatures._ttw import bones, variants, families, LAUNCHER_ROT
NAME = 'Deathclaw'
ANIM_SRC = '/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/deathclaw'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], ['Bip01 Neck', 'Bip01 Neck1'])
S = 1.5                                  # body scale vs the human-sized configs
sc = lambda v: tuple(round(x * S, 2) for x in v)
GRASP = (16.0, 0.0, 0.0)                 # claw: palm point between the hand and the finger roots
CURL_AXIS = (0, 0, 1)
POLE_R = sc((2, -6, -30))                # elbows hang down by the body (long upper arms flared out sideways)
POLE_L = sc((0, -40, -30))               # off elbow down when the hand is forward, back when it reaches the hip
POUCH = sc((-10, 6, -40))                # magazine pouch at the left hip (the belly is too near its high shoulders for its long arms)
HOLD = dict(wpos=sc((-8, -16, -6)), pitch=30)
THROW = dict(wind=dict(wpos=sc((-6, -26, 34)), pitch=50, lean=-8, twist=20, head=-5),
             rel=dict(wpos=sc((-14, 14, 32)), pitch=10, lean=12, twist=-12, head=5),
             follow=dict(wpos=sc((-26, 16, 6)), pitch=-20, lean=16, twist=-20, head=8))
PLACE = dict(wpos=sc((-12, 10, -26)), pitch=-40, lean=35, head=25)
JUMP_SCALE = 0.8
SNEAK_DROP = 0.4                         # its own crouch (specialidle_crouchloop) drops the pelvis 96 -> 71
SNEAK_LEAN = 20.0
GUN1, GUN2, HEAVY, LAUNCHER = families(S)
NATIVE = {'h2h': ['h2haim.kf'] * 6, '1hm': ['h2haim.kf'] * 6, '2hm': ['h2haim.kf'] * 6}
# its shoulders are as high as its head and its arms twice a human's: guns are held out in front at belly height (hip,
# ~45 from the shoulder) and raised to the right of the jaw for iron sights, never at head height (they clipped the head)
# guns: built here only for their names / timing - deathclaw_mouth.py (run by assemble_deathclaw.py) replaces every
# gun file with the mouth fire (gun hidden, shot from the mouth); thrown weapons and mines keep these claw holds
SYN2HR = dict(base='mtidle.kf', wpos=sc((7.6, 42.5, -21.5)), grip=(16.0, -3.0, 0.0), curl=0.6,
              variants=variants(dict(wpos=(-1.7, 0.8, 15.9), head=10), S))
SYN1HP = dict(base='mtidle.kf', wpos=sc((8.9, 44.5, -16.8)), grip=None, variants=variants(dict(wpos=(-4.3, 2.8, 13.9), head=6), S))
WEAPON_TYPES = {
    'h2h': dict(),
    # melee weapons swing with its own claw attacks (aim, swings, power attacks, equips), the weapon in the right claw
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
SIT_TAIL = ['Bip01 Tail']               # furniture: tail root keeps its idle direction (lies back behind the seat)
SIT_HAND_MIN = 65.0                       # furniture: below this the long arms rest along the thighs
