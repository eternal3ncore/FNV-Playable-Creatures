"""Mirelurk (Tale of Two Wastelands: Mirelurk, Mirelurk Hunter, Nukalurk) - creature config for the weapon-set builder.
Vanilla Creatures\\Mirelurk\\skeleton.nif: a crab - Bip01 biped body carried low on two digitigrade legs (Thigh..Toe1)
plus four side legs (Bip01 Ponytail1-4 / 5-8 / 9-12 / 13-16 under Spine1), a tail, pincer claws (Hand + Finger0 = the
moving jaw), a Weapon node under the right claw. Own set: H2H (aim, left / right claw strikes, four power attacks,
equips, recoil) + walk / run / backward / strafe / turn locomotion (+ hurt). Melee only: one- and two-handed melee
weapons strike with its own claw attacks (weapon unseen, as the deathclaw); it can't hold guns, throws or mines."""
from creatures._ttw import bones
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
WEAPON_TYPES = {
    'h2h': dict(),
    '1hm': dict(src='h2h', copy_attacks=True),
    '2hm': dict(src='h2h', copy_attacks=True),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM'
# furniture (eyebot_furniture.py ... mirelurk): no seated pose of its own - it climbs onto the seat and stands on it in its
# idle pose (head height above the seat = its standing head height above the floor)
SPHERE_LOW = 120.4
