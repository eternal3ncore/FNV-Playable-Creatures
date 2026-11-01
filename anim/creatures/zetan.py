"""Zetan (Mothership Zeta alien) - creature config for the procedural weapon-set builder."""
NAME = 'Zetan'
ANIM_SRC = '/home/claude/fnv/assets/meshes/dlc05/creatures/alien'   # the creature's own KFs (from the game's BSA)
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = '2hraim.kf'          # any of the creature's KFs (header/version template)
ACCUM_ROOT = 'Bip01'
BONES = dict(
    spine=['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], torso='Bip01 Spine2',
    neck=['Bip01 Neck', 'Bip01 Neck1'], head='Bip01 Head', weapon='Weapon',
    arm_R=['Bip01 R Clavicle', 'Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand'],
    arm_L=['Bip01 L Clavicle', 'Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand'],
    fingers_R=[f'Bip01 R Finger{a}{b}' for a in '012' for b in ('', '1', '2')],
    fingers_L=[f'Bip01 L Finger{a}{b}' for a in '012' for b in ('', '1', '2')],
    curl_L=[f'Bip01 L Finger{a}{b}' for a in '12' for b in ('', '1', '2')],
    root='Bip01 NonAccum', pelvis='Bip01 Pelvis',
    leg_R=['Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot', 'Bip01 R Toe0'],
    leg_L=['Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot', 'Bip01 L Toe0'],
)
IDLE_KF = 'mtidle.kf'              # standing pose used as the base for jumps
HUMAN_REF = '/home/claude/fnv/ref_male'   # vanilla _male KFs (weapon-part tracks + timing only)
GRASP = (10.0, 0.0, 0.0)          # palm point in the hand frame (alien hand ~13.5 units + long fingers)
CURL_AXIS = (0, 0, 1)
POLE_R = (6, -4, -4)              # elbow hints (world axes, added to the base elbow position)
POLE_L = (-8, 0, -6)
POUCH = (-10, 8, -16)             # waist pouch: world-axis offset from the base torso (Spine2) position

# Weapon types the creature can use natively: file prefix -> aim-variant source files (plain, Up, Down, IS, ISUp, ISDown)
NATIVE = {
    '1hp': ['1hpaim.kf', '1hpaimup.kf', '1hpaimdown.kf', '1hpaim.kf', '1hpaimup.kf', '1hpaimdown.kf'],
    '2hr': ['2hraim.kf', '2hraimup.kf', '2hraimdown.kf', '2hraimis.kf', '2hraimisup.kf', '2hraimisdown.kf'],
    '1hm': ['1hmaim.kf'] * 6,
}
# Per weapon-family handling (motion parameters in plans; weapon frame: x barrel, y up, z right)
GUN2 = dict(tilt=dict(roll=35, pitch=-8, wpos=(-5, 0, 5), lean=8, head=18),
            ltilt=dict(roll=45, pitch=-5, wpos=(-5, 0, 6), lean=10, head=20),
            mag=(6, -6, -2), below=(6, -11, -2), side=(0, 1, -6), back=(-6, 1, -6), port=(4, -5, 0),
            kick=dict(pitch=7, wpos=(0, -3, 1), lean=-2), grip=None)
GUN1 = dict(tilt=dict(roll=30, pitch=12, wpos=(-9, -20, -8), lean=6, head=15),
            ltilt=dict(roll=55, pitch=30, wpos=(-9, -20, -6), lean=6, head=18),
            mag=(-2, -8, -2), below=(-2, -13, -2), side=(5, 3, -3), back=(-3, 3, -3), port=(1, 1, -4),
            kick=dict(pitch=12, wpos=(0, -4, 2), lean=-1), grip=None)
HEAVY = dict(GUN2, kick=dict(pitch=3, wpos=(0, -2, 0), lean=-1))
LAUNCHER = dict(GUN2, kick=dict(pitch=14, wpos=(0, -6, 2), lean=-5))
HOLD = dict(wpos=(-8, -22, -10), pitch=30)            # grenade/mine held at the chest (from the 1HP aim)

# Every weapon type the creature gets: src = native type whose own files (aims, equip...) are reused,
# family = motion parameters for procedural attacks / reloads.
WEAPON_TYPES = {
    '1hp': dict(src='1hp', family=GUN1, ranged=True),
    '2hr': dict(src='2hr', family=GUN2, ranged=True),
    '2ha': dict(src='2hr', family=GUN2, ranged=True),
    '2hh': dict(src='2hr', family=HEAVY, ranged=True),
    # launcher meshes fire along their -Y (ProjectileNode) with +X up; rifles fire along +X with +Y up:
    # the Weapon node is re-oriented so the tube points where the Zetan's rifle barrel points
    '2hl': dict(src='2hr', family=LAUNCHER, ranged=True, weapon_rot=[[0, -1, 0], [1, 0, 0], [0, 0, 1]]),
    '2hm': dict(src='1hm', melee2=True, grip=(-9.0, 0.0, 0.0)),   # off hand on the handle below the weapon hand
    '1hm': dict(src='1hm', melee=True),
    '1gt': dict(src='1hp', thrown=True),
    '1md': dict(src='1hp', mine=True),
    '1lm': dict(src='1hp', mine=True),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
