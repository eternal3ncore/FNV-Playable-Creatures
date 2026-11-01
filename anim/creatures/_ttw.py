"""Shared pieces of the TTW creature configs (Point Lookout swampfolk, The Pitt trogs)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kf import Skeleton
SRC = '/home/claude/fnv/creature_src_ttw'
def bones(skel, spine, neck):
    have = set(Skeleton(skel).local)
    f = lambda side, digits: [n for n in [f'Bip01 {side} Finger{a}{b}' for a in digits for b in ('', '1', '2')] if n in have]
    return dict(
        spine=[n for n in spine if n in have], torso=[n for n in spine if n in have][-1],
        neck=[n for n in neck if n in have], head='Bip01 Head', weapon='Weapon',
        arm_R=['Bip01 R Clavicle', 'Bip01 R UpperArm', 'Bip01 R Forearm', 'Bip01 R Hand'],
        arm_L=['Bip01 L Clavicle', 'Bip01 L UpperArm', 'Bip01 L Forearm', 'Bip01 L Hand'],
        fingers_R=f('R', '01234'), fingers_L=f('L', '01234'), curl_L=f('L', '1234'),
        root='Bip01 NonAccum', pelvis='Bip01 Pelvis',
        leg_R=['Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot', 'Bip01 R Toe0'],
        leg_L=['Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot', 'Bip01 L Toe0'])
def sc(v, S): return tuple(round(x * S, 2) for x in v)
_UP = dict(pitch=30, wpos=(0, -2, 9), lean=-6, head=-18)
_DN = dict(pitch=-30, wpos=(-2, -4, -2), lean=8, head=18)
def variants(IS, S=1.0):
    up = dict(_UP, wpos=sc(_UP['wpos'], S)); dn = dict(_DN, wpos=sc(_DN['wpos'], S))
    out = [dict(wpos=(0, 0, 0)), up, dn]
    for d in out[:3]:
        e = dict(d); w = e.get('wpos', (0, 0, 0)); e['wpos'] = tuple(a + c for a, c in zip(w, sc(IS['wpos'], S)))
        e['head'] = e.get('head', 0) + IS.get('head', 0); out.append(e)
    return out
def families(S=1.0):
    GUN2 = dict(tilt=dict(roll=35, pitch=-8, wpos=sc((-5, 0, 5), S), lean=8, head=18),
                ltilt=dict(roll=45, pitch=-5, wpos=sc((-5, 0, 6), S), lean=10, head=20),
                mag=(7, -6, -2), below=(7, -12, -2), side=(0, 1, -6), back=(-6, 1, -6), port=(5, -5, 0),
                kick=dict(pitch=7, wpos=(0, -3, 1), lean=-2))
    GUN1 = dict(tilt=dict(roll=30, pitch=12, wpos=sc((-10, -20, -8), S), lean=6, head=15),
                ltilt=dict(roll=55, pitch=30, wpos=sc((-10, -20, -6), S), lean=6, head=18),
                mag=(-2, -7, -2), below=(-2, -12, -2), side=(5, 3, -3), back=(-3, 3, -3), port=(1, 1, -4),
                kick=dict(pitch=12, wpos=(0, -4, 2), lean=-1))
    HEAVY = dict(GUN2, kick=dict(pitch=3, wpos=(0, -2, 0), lean=-1))
    LAUNCHER = dict(GUN2, kick=dict(pitch=14, wpos=(0, -6, 2), lean=-5))
    return GUN1, GUN2, HEAVY, LAUNCHER
LAUNCHER_ROT = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
