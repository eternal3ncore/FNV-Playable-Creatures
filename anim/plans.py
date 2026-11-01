"""Reload / jam motion plans per weapon type (normalized time u in 0..1)."""
from author import Plan
W = lambda *o: ('weapon', o)
TOR = lambda *o: ('torso', o)
AIM = dict(roll=0, pitch=0, yaw=0, wpos=(0, 0, 0), lean=0, head=0, lhand=('aim',), curl=0)
POUCH = TOR(-10, 8, -16)

CFG = {
    # tilt: gun presented to the left hand; mag: magazine well / loading port (weapon frame: x barrel, y up, z right)
    '2hr': dict(tilt=dict(roll=35, pitch=-8, wpos=(-5, 0, 5), lean=8, head=18),
                ltilt=dict(roll=45, pitch=-5, wpos=(-5, 0, 6), lean=10, head=20),
                mag=(6, -6, -2), below=(6, -11, -2), side=(0, 1, -6), back=(-6, 1, -6), port=(4, -5, 0)),
    '1hp': dict(tilt=dict(roll=30, pitch=12, wpos=(-9, -20, -8), lean=6, head=15),
                ltilt=dict(roll=55, pitch=30, wpos=(-9, -20, -6), lean=6, head=18),
                mag=(-2, -8, -2), below=(-2, -13, -2), side=(5, 3, -3), back=(-3, 3, -3), port=(1, 1, -4)),
}

def magazine(c):
    return Plan([
        (0.00, {}),
        (0.15, dict(c['tilt'], lhand=W(c['mag'][0], c['mag'][1] - 3, c['mag'][2] - 2), curl=.4)),
        (0.27, dict(lhand=W(*c['mag']), curl=1)),
        (0.45, dict(lhand=POUCH, curl=1)),
        (0.61, dict(lhand=W(*c['below']))),
        (0.69, dict(lhand=W(*c['mag']))),
        (0.79, dict(lhand=W(*c['side']), curl=.3, roll=c['tilt']['roll'] * .45)),
        (0.87, dict(lhand=W(*c['back']), curl=.8)),
        (1.00, AIM),
    ])

def loop_start(c):
    return Plan([
        (0.00, {}),
        (0.55, dict(c['ltilt'], lhand=W(*c['port']), curl=.3)),
        (1.00, dict(lhand=POUCH, curl=1)),
    ])

def loop_step(c, h):
    """[0,h]: pouch -> port (insert) -> pouch, pose at h == pose at 0 so a [0,Hit] loop is seamless;
       [h,1]: close up and return to the aim pose."""
    k = [(0.00, dict(c['ltilt'], lhand=POUCH, curl=1)),
         (h * 0.50, dict(lhand=W(c['port'][0], c['port'][1] - 3, c['port'][2]), curl=1)),
         (h * 0.80, dict(lhand=W(*c['port']), curl=.6)),
         (h, dict(lhand=POUCH, curl=1))]
    if h < 0.97:
        m = h + (1 - h) * 0.45
        k += [(m, dict(lhand=W(*c['side']), curl=.3, roll=c['ltilt']['roll'] * .3, pitch=0)), (1.00, AIM)]
    return Plan(k)

def jam(c):
    return Plan([
        (0.00, {}),
        (0.18, dict(c['tilt'], lhand=W(*c['side']), curl=.3)),
        (0.32, dict(lhand=W(*c['back']), curl=.9)),
        (0.44, dict(lhand=W(*c['side']), curl=.3)),
        (0.58, dict(lhand=W(*c['back']), curl=.9)),
        (0.72, dict(lhand=W(*c['side']), curl=.3, roll=c['tilt']['roll'] * .3)),
        (1.00, AIM),
    ])
