"""Trog (The Pitt street trog: Trog, Brute, Savage) - creature config.
Bip01 biped that moves on all fours (idle and locomotion crouched, hands on the ground); no Spine2 (torso = Spine1),
four fingers. Own set: H2H (aim, swings, four power attacks, equips) + walk/run/strafe/turn locomotion. Melee weapons
swing with its own claw attacks (as the feral ghoul); guns / throws / mines are synthetic holds on its crouched idle,
procedural attacks / reloads / jams with vanilla timing and sounds."""
from creatures._ttw import SRC, bones, variants, families, LAUNCHER_ROT
NAME = 'Trog'
ANIM_SRC = SRC + '/trog'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1'], ['Bip01 Neck', 'Bip01 Neck1'])
GRASP = (7.5, 0.0, 0.0)
CURL_AXIS = (0, 0, 1)
POLE_R = (8, -4, -8)
POLE_L = (-6, 0, -10)
POUCH = (-10, 6, -10)
SIT_SEAT_OFFSET = 0.0           # furniture: sits at the human seat height (its standing pose is a crouch)
JUMP_SCALE = 0.35                # jumps: leg fold of the crouched trog
SNEAK_DROP = 0.15
SNEAK_LEAN = 0.0
HOLD = dict(wpos=(-8, -16, -6), pitch=30)
GUN1, GUN2, HEAVY, LAUNCHER = families()
NATIVE = {'h2h': ['h2haim.kf'] * 6, '1hm': ['h2haim.kf'] * 6}
SYN2HR = dict(base='mtidle.kf', wpos=(4, 26, 6), grip=(11.0, -2.0, 0.0), curl=0.6,
              variants=variants(dict(wpos=(4, 2, 9), head=10)))
SYN1HP = dict(base='mtidle.kf', wpos=(8, 28, 8), grip=None, variants=variants(dict(wpos=(-8, -6, 8), head=6)))
WEAPON_TYPES = {
    'h2h': dict(),
    # moves on all fours: every melee type is its own H2H set (aim, swings, power attacks, equips) with the
    # weapon in the hand - no off-hand grip for two-handed weapons
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
# melee only: the gun / throw / mine sets rotated its spine, and its legs hang off the spine -
# the body twisted and the legs dragged into the ground. Firearms, throws and mines are refused (ini WeaponAnims);
# the builder still lists them above, so after a rebuild move their files to Trog\_disabled (as deployed).
INI_WEAPON_ANIMS = 'H2H,1HM,2HM'
