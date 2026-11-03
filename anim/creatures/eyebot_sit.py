"""Eyebot - furniture only (eyebot_furniture.py): rests on the seat, unanimated."""
from creatures._ttw import bones
NAME = 'Eyebot'
ANIM_SRC = '/home/claude/fnv/robot_sit/Eyebot'
SKELETON = ANIM_SRC + '/Skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
BONES = bones(SKELETON, ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], ['Bip01 Neck', 'Bip01 Neck1'])
SPHERE_LOW = 25.7               # eyebot.nif: lowest vertex below the head (sphere) node
