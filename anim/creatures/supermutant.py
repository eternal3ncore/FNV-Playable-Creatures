"""Super Mutant (and Nightkin, same skeleton) - creature config for the procedural weapon-set builder.
Vanilla Creatures\\SMSpineBreaker\\skeleton.nif: Bip01 biped ~1.3x human, hunched; hands ~2x human.
Own animation set: H2H, 2HM, 2HR, 2HA, 2HH, 2HL, 1GT (aims +-, attacks, some reloads / jams, equips), locomotion,
swim, deaths. Missing: 1HP (synthetic hold), 1HM (its own 2HM set with the off arm free), 1MD / 1LM (from 1GT),
and the attack / reload / jam groups each gun type lacks (procedural, vanilla timing and sounds)."""
NAME = 'Super Mutant'
ANIM_SRC = '/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/smspinebreaker'
SKELETON = ANIM_SRC + '/skeleton.nif'
TEMPLATE_KF = 'mtidle.kf'
ACCUM_ROOT = 'Bip01'
BASE_MODE = 'sample'
IDLE_KF = 'mtidle.kf'
HUMAN_REF = '/home/claude/fnv/ref_male'
_F = lambda side: [f'Bip01 {side} Finger0{b}' for b in ('', '1', '2')] + \
                  [f'Bip01 {side} Finger{a}{b}' for a in '1234' for b in ('', '1', '2')]
BONES = dict(
    spine=['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2'], torso='Bip01 Spine2',
    neck=['Bip01 Neck'], head='Bip01 Head', weapon='Weapon',
    arm_R=['Bip01 R Clavicle', 'Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand'],
    arm_L=['Bip01 L Clavicle', 'Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand'],
    fingers_R=_F('R'), fingers_L=_F('L'),
    curl_L=[f'Bip01 L Finger{a}{b}' for a in '1234' for b in ('', '1', '2')],
    root='Bip01 NonAccum', pelvis='Bip01 Pelvis',
    leg_R=['Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot', 'Bip01 R Toe0'],
    leg_L=['Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot', 'Bip01 L Toe0'],
)
S = 1.3                                 # body scale vs the human-sized configs
sc = lambda v: tuple(round(x * S, 2) for x in v)
GRASP = (12.0, 0.0, 0.0)                # big hand: palm point ~ between hand and finger roots
CURL_AXIS = (0, 0, 1)
POLE_R = sc((8, -4, -8))
POLE_L = sc((-6, 0, -10))
POUCH = sc((-10, 6, -18))
HOLD = {}
THROW = dict(wind=dict(wpos=sc((-6, -26, 34)), pitch=50, lean=-8, twist=20, head=-5),
             rel=dict(wpos=sc((-14, 14, 32)), pitch=10, lean=12, twist=-12, head=5),
             follow=dict(wpos=sc((-26, 16, 6)), pitch=-20, lean=16, twist=-20, head=8))
PLACE = dict(wpos=sc((-12, 10, -26)), pitch=-40, lean=35, head=25)

V3 = lambda p: [f'{p}aim.kf', f'{p}aimup.kf', f'{p}aimdown.kf'] * 2
NATIVE = {'h2h': V3('h2h'), '2hm': V3('2hm'), '2hr': V3('2hr'), '2ha': V3('2ha'), '2hh': V3('2hh'), '2hl': V3('2hl'),
          '1gt': V3('1gt')}
_UP = dict(pitch=30, wpos=sc((0, -2, 9)), lean=-6, head=-18)
_DN = dict(pitch=-30, wpos=sc((-2, -4, -2)), lean=8, head=18)
def _v(IS):
    b = dict(wpos=(0, 0, 0))
    out = [dict(b), dict(_UP), dict(_DN)]
    for d in out[:3]:
        e = dict(d); w = e.get('wpos', (0, 0, 0)); e['wpos'] = tuple(a + c for a, c in zip(w, IS['wpos']))
        e['head'] = e.get('head', 0) + IS.get('head', 0); out.append(e)
    return out
SYN1HP = dict(base='mtidle.kf', wpos=sc((8, 34, 2)), grip=None, variants=_v(dict(wpos=sc((-8, -6, 8)), head=6)))

GUN2 = dict(tilt=dict(roll=35, pitch=-8, wpos=(-5, 0, 5), lean=8, head=18),
            ltilt=dict(roll=45, pitch=-5, wpos=(-5, 0, 6), lean=10, head=20),
            mag=(7, -6, -2), below=(7, -12, -2), side=(0, 1, -6), back=(-6, 1, -6), port=(5, -5, 0),
            kick=dict(pitch=7, wpos=(0, -3, 1), lean=-2))
GUN1 = dict(tilt=dict(roll=30, pitch=12, wpos=sc((-10, -20, -8)), lean=6, head=15),
            ltilt=dict(roll=55, pitch=30, wpos=sc((-10, -20, -6)), lean=6, head=18),
            mag=(-2, -7, -2), below=(-2, -12, -2), side=(5, 3, -3), back=(-3, 3, -3), port=(1, 1, -4),
            kick=dict(pitch=12, wpos=(0, -4, 2), lean=-1))
HEAVY = dict(GUN2, kick=dict(pitch=3, wpos=(0, -2, 0), lean=-1))
LAUNCHER = dict(GUN2, kick=dict(pitch=14, wpos=(0, -6, 2), lean=-5))

WEAPON_TYPES = {
    'h2h': dict(),
    '2hm': dict(power_src='2hmattackpower.kf'),
    '1gt': dict(thrown=True),
    '1hm': dict(release_from='2hm', equip_from='2hm', power_src='1hmattackpower.kf'),
    '1hp': dict(synth=SYN1HP, equip_from='1gt', family=GUN1, ranged=True),
    '2hr': dict(family=GUN2, ranged=True),
    '2ha': dict(family=GUN2, ranged=True),
    '2hh': dict(family=HEAVY, ranged=True),
    '2hl': dict(family=LAUNCHER, ranged=True),        # own launcher anims already orient the tube
    '1md': dict(src='1gt', mine=True, reuse_aims=True),
    '1lm': dict(src='1gt', mine=True, reuse_aims=True),
}
INI_WEAPON_ANIMS = 'H2H,1HM,2HM,1HP,2HR,2HA,2HH,2HL,1GT,1MD,1LM'
