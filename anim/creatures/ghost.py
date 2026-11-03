"""Ghost People (Dead Money) - creature config for the procedural weapon-set builder.
Human-proportioned Bip01 skeleton (NVDLC01\\Creatures\\Ghosts\\skeleton.nif). Own animation set:
H2H, 2HM (spear), 1GT (gas bomb / throwing spear) + unarmed locomotion. Everything else is derived."""
NAME = 'Ghost People'
ANIM_SRC = '/home/claude/fnv/ghost_src/meshes/nvdlc01/creatures/ghosts'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'               # layer aims on the idle's root/legs, accum root at the origin
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
_F = lambda side: [f'Bip01 {side} Thumb1{b}' for b in ('', '1', '2')] + \
                  [f'Bip01 {side} Finger{a}{b}' for a in '1234' for b in ('', '1', '2')]
BONES = dict(
    spine=['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], torso='Bip01 Spine2',
    neck=['Bip01 Neck', 'Bip01 Neck1'], head='Bip01 Head', weapon='Weapon',
    arm_R=['Bip01 R Clavicle', 'Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand'],
    arm_L=['Bip01 L Clavicle', 'Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand'],
    fingers_R=_F('R'), fingers_L=_F('L'),
    curl_L=[f'Bip01 L Finger{a}{b}' for a in '1234' for b in ('', '1', '2')],
    root='Bip01 NonAccum', pelvis='Bip01 Pelvis',
    leg_R=['Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot', 'Bip01 R Toe0'],
    leg_L=['Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot', 'Bip01 L Toe0'],
)
XFER_HIP_SHIFT = (-8.0, 10.0, 0.0)   # xfer_human: two-handed hip holds (not iron sights / equips / deaths) 8 units toward the middle, 10 forward (stock clear of the belly)
XFER_TWIST_AXIS = 'spine'          # xfer_human: two-handed torso turn about the trunk line (the hunch stays over the hips)
GRASP = (6.0, 0.0, 0.0)            # palm point in the hand frame (human-size hand)
CURL_AXIS = (0, 0, 1)
POLE_R = (8, -4, -8)
POLE_L = (-6, 0, -10)
POUCH = (-10, 6, -18)
HOLD = {}                          # grenades/mines: the ghost's own 1GT hold
THROW = dict(wind=dict(wpos=(-6, -26, 34), pitch=50, lean=-8, twist=20, head=-5),
             rel=dict(wpos=(-14, 14, 32), pitch=10, lean=12, twist=-12, head=5),
             follow=dict(wpos=(-26, 16, 6), pitch=-20, lean=16, twist=-20, head=8))
PLACE = dict(wpos=(-12, 10, -26), pitch=-40, lean=35, head=25)

NATIVE = {
    '2hm': ['2hmaim.kf', '2hmaimup.kf', '2hmaimdown.kf', '2hmaim.kf', '2hmaimup.kf', '2hmaimdown.kf'],
    '1gt': ['1gtaim.kf'] * 6,
    'h2h': ['h2haim.kf', 'h2haimup.kf', 'h2haimdown.kf'] * 2,
}
# aim variants for synthetic holds: plain, Up, Down, IS, ISUp, ISDown
_UP = dict(pitch=30, wpos=(0, -2, 9), lean=-6, head=-18)
_DN = dict(pitch=-30, wpos=(-2, -4, -2), lean=8, head=18)
def _v(IS):
    b = dict(wpos=(0, 0, 0))
    out = [dict(b), dict(_UP), dict(_DN)]
    for d in out[:3]:
        e = dict(d); w = e.get('wpos', (0, 0, 0)); e['wpos'] = tuple(a + c for a, c in zip(w, IS['wpos']))
        e['head'] = e.get('head', 0) + IS.get('head', 0); out.append(e)
    return out
# rifle held well out in front: the stock (~18 units behind the grip) must clear the hunched chest
SYN2HR = dict(base='mtidle.kf', wpos=(4, 30, -1), grip=(11.0, -2.0, 0.0), curl=0.6,
              variants=_v(dict(wpos=(-3, -2, 12), head=8)))
SYN1HP = dict(base='mtidle.kf', wpos=(8, 34, 2), grip=None,
              variants=_v(dict(wpos=(-8, -6, 8), head=6)))

GUN2 = dict(tilt=dict(roll=35, pitch=-8, wpos=(-5, 0, 5), lean=8, head=18),
            ltilt=dict(roll=45, pitch=-5, wpos=(-5, 0, 6), lean=10, head=20),
            mag=(7, -6, -2), below=(7, -12, -2), side=(0, 1, -6), back=(-6, 1, -6), port=(5, -5, 0),
            kick=dict(pitch=7, wpos=(0, -3, 1), lean=-2))
GUN1 = dict(tilt=dict(roll=30, pitch=12, wpos=(-10, -20, -8), lean=6, head=15),
            ltilt=dict(roll=55, pitch=30, wpos=(-10, -20, -6), lean=6, head=18),
            mag=(-2, -7, -2), below=(-2, -12, -2), side=(5, 3, -3), back=(-3, 3, -3), port=(1, 1, -4),
            kick=dict(pitch=12, wpos=(0, -4, 2), lean=-1))
HEAVY = dict(GUN2, kick=dict(pitch=3, wpos=(0, -2, 0), lean=-1))
LAUNCHER = dict(GUN2, kick=dict(pitch=14, wpos=(0, -6, 2), lean=-5))

WEAPON_TYPES = {
    'h2h': dict(),                                               # own
    '2hm': dict(power_src='2hmattackrightpower.kf'),             # own + missing power groups
    '1gt': dict(thrown=True),                                    # own hold/throws + missing throws
    '1hm': dict(release_from='2hm', equip_from='2hm', power_src='1hmattackrightpower.kf'),
    '1hp': dict(synth=SYN1HP, equip_from='1gt', family=GUN1, ranged=True),
    '2hr': dict(synth=SYN2HR, equip_from='2hm', family=GUN2, ranged=True),
    '2ha': dict(src='2hr', family=GUN2, ranged=True),
    '2hh': dict(src='2hr', family=HEAVY, ranged=True),
    '2hl': dict(src='2hr', family=LAUNCHER, ranged=True, weapon_rot=[[0, -1, 0], [1, 0, 0], [0, 0, 1]]),
    '1md': dict(src='1gt', mine=True, reuse_aims=True),
    '1lm': dict(src='1gt', mine=True, reuse_aims=True),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
