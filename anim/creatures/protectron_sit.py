"""Protectron - furniture only (retarget_idle_creature.py): the human chair / stool set on the deployed
PlayableCreatures\\Protectron skeleton. Its short legs sit like a toddler's (leg IK reaches for the floor)."""
from creatures._ttw import bones
NAME = 'Protectron'
ANIM_SRC = '/home/claude/fnv/robot_sit/Protectron'
SKELETON = ANIM_SRC + '/Skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], ['Bip01 Neck', 'Bip01 Neck1'])
SIT_SEAT_OFFSET = 3.0           # pelvis 40 on a chair: its hip box rests on the seat
SIT_OWN_ARMS = True             # arms keep playing its standing idle while seated (rigid arms went into the body)
