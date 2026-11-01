"""Procedural motion plans (normalized time u in 0..1). c = weapon family params, cr = creature config."""
from rig import Plan
W = lambda *o: ('weapon', o)
TOR = lambda *o: ('torso', o)
AIM = dict(roll=0, pitch=0, yaw=0, wpos=(0, 0, 0), lean=0, head=0, twist=0, lhand=('base',), curl=0, jit=0)

def magazine(c, cr):
    P = TOR(*cr.POUCH)
    return Plan([
        (0.00, {}),
        (0.15, dict(c['tilt'], lhand=W(c['mag'][0], c['mag'][1] - 3, c['mag'][2] - 2), curl=.4)),
        (0.27, dict(lhand=W(*c['mag']), curl=1)),
        (0.45, dict(lhand=P, curl=1)),
        (0.61, dict(lhand=W(*c['below']))),
        (0.69, dict(lhand=W(*c['mag']))),
        (0.79, dict(lhand=W(*c['side']), curl=.3, roll=c['tilt']['roll'] * .45)),
        (0.87, dict(lhand=W(*c['back']), curl=.8)),
        (1.00, AIM)])

def loop_start(c, cr):
    return Plan([(0.00, {}), (0.55, dict(c['ltilt'], lhand=W(*c['port']), curl=.3)), (1.00, dict(lhand=TOR(*cr.POUCH), curl=1))])

def loop_step(c, cr, h):
    P = TOR(*cr.POUCH)
    k = [(0.00, dict(c['ltilt'], lhand=P, curl=1)),
         (h * 0.50, dict(lhand=W(c['port'][0], c['port'][1] - 3, c['port'][2]), curl=1)),
         (h * 0.80, dict(lhand=W(*c['port']), curl=.6)),
         (h, dict(lhand=P, curl=1))]
    if h < 0.97:
        k += [(h + (1 - h) * 0.45, dict(lhand=W(*c['side']), curl=.3, roll=c['ltilt']['roll'] * .3, pitch=0)), (1.00, AIM)]
    return Plan(k)

def jam(c, cr):
    return Plan([
        (0.00, {}),
        (0.18, dict(c['tilt'], lhand=W(*c['side']), curl=.3)),
        (0.32, dict(lhand=W(*c['back']), curl=.9)),
        (0.44, dict(lhand=W(*c['side']), curl=.3)),
        (0.58, dict(lhand=W(*c['back']), curl=.9)),
        (0.72, dict(lhand=W(*c['side']), curl=.3, roll=c['tilt']['roll'] * .3)),
        (1.00, AIM)])

def recoil(c, cr, hit):
    """single shot: kick at `hit` (normalized), recover by ~hit+0.45"""
    k = c['kick']; h = max(0.0, min(hit, 0.6))
    return Plan([(0.0, {}), (h, {}), (min(h + 0.08, 0.95), dict(k)), (min(h + 0.5, 1.0), AIM), (1.0, AIM)])

def fire_loop(c, cr):
    """automatic fire loop: small kick per cycle, first == last frame (seamless loop)"""
    k = c['kick']
    return Plan([(0.0, AIM), (0.3, dict(pitch=k['pitch'] * .45, wpos=tuple(x * .45 for x in k['wpos']))), (1.0, AIM)])

def spin(c, cr, fire):
    """spin-up / wind-up: steady, brace, weapon vibration after `fire`"""
    return Plan([(0.0, {}), (max(fire - .1, .05), dict(lean=3)), (fire, dict(jit=1.2)), (1.0, dict(jit=1.2, lean=3))])

def hold(cr):
    return Plan([(0.0, dict(cr.HOLD)), (1.0, dict(cr.HOLD))])

def throw(cr, hold_u, rel_u):
    """wind up behind the shoulder (held at 'Hold'), throw forward, release at 'Release', follow through"""
    H = cr.HOLD
    T = getattr(cr, 'THROW', {})
    wind = T.get('wind', dict(wpos=(2, -60, 20), pitch=60, lean=-8, twist=25, head=-5))
    rel = T.get('rel', dict(wpos=(-4, -16, 12), pitch=10, lean=12, twist=-15, head=5))
    follow = T.get('follow', dict(wpos=(-16, -14, -16), pitch=-20, lean=16, twist=-25, head=8))
    return Plan([(0.0, dict(H)), (max(hold_u * .85, .05), wind), (hold_u, wind),
                 (rel_u, rel), (min(rel_u + (1 - rel_u) * .3, .98), follow), (1.0, dict(H, lean=0, twist=0, head=0))])

def place(cr, rel_u):
    """bend over and set the item down in front, release, stand back up"""
    H = cr.HOLD
    down = getattr(cr, 'PLACE', dict(wpos=(-10, -18, -34), pitch=-40, lean=40, head=25))
    return Plan([(0.0, dict(H)), (rel_u * .8, down), (rel_u, dict(down, wpos=(-10, -16, -38))),
                 (min(rel_u + (1 - rel_u) * .5, .98), dict(H, lean=10)), (1.0, dict(H))])
