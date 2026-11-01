"""Locomotion: sneak crouch with leg IK, and crab-run strafes, for creature-race players.

crouch_frames(cr, src, ...): the creature's own idle / locomotion with the pelvis lowered (fraction of the hip height),
  the torso leaning forward and the head kept level; each leg is re-solved with 2-bone IK so the foot keeps its
  original world position and orientation (no sliding, no sideways knees: the pole is in front of the knee). The root
  motion is untouched, so the engine's speed matching still works. Replaces sneak.py's fixed joint angles, which bent
  the legs sideways on the ghoul / super mutant skeletons.
crab_frames(cr, src, side, ...): FastLeft / FastRight from the creature's own run (FastForward): the root motion is
  turned 90 degrees to the side, the lower body yaws toward the motion and the spine twists back, so the legs run
  (nearly) along the travel direction and the upper body keeps facing forward. The engine plays a movement animation
  at (actor speed / animation speed); the creatures' own sidesteps move ~55-75 units/s, so a running player
  (~350-400) played them 5x fast.
"""
import numpy as np
from kf import KFEval
from rig import rotm, align

Z = np.array([0.0, 0.0, 1.0]); X = np.array([1.0, 0.0, 0.0])

def _fk(sk, loc):
    W = {}
    for nm in sk.order:
        t, R = loc[nm]; p = sk.parent[nm]
        if p is None: W[nm] = (t.copy(), R.copy())
        else: pp, pR = W[p]; W[nm] = (pp + pR @ t, pR @ R)
    return W

def _set_world_rot(sk, loc, W, nm, Rw):
    loc[nm] = (loc[nm][0], W[sk.parent[nm]][1].T @ Rw)

def _sample(cr, k, t):
    sk = cr.sk; smp = k.sample(t); loc = {}
    for nm in sk.order:
        tt, R, _ = sk.local[nm]
        if nm in smp:
            if smp[nm][0] is not None: tt = smp[nm][0]
            if smp[nm][1] is not None: R = smp[nm][1]
        loc[nm] = (np.array(tt, float), np.array(R, float))
    # the accum root's rotation is the actor's facing in game (identity in creature space); files that don't key it
    # (idles) would otherwise pick up the skeleton's bind yaw (90 degrees on the ghoul / super mutant)
    acc = cr.cfg.ACCUM_ROOT
    if not (acc in smp and smp[acc][1] is not None): loc[acc] = (loc[acc][0], np.eye(3))
    return loc

def _leg_ik(sk, loc, th, ca, ft, target, foot_rot, pole):
    W = _fk(sk, loc)
    S = W[th][0]; E = W[ca][0]; G = W[ft][0]
    a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
    d = target - S; dist = np.linalg.norm(d)
    dc = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.999)
    dn = d / dist
    cosA = (a * a + dc * dc - b * b) / (2 * a * dc)
    pv = pole - S; pv = pv - dn * np.dot(pv, dn)
    if np.linalg.norm(pv) < 1e-6: pv = np.cross(dn, X)
    pv /= np.linalg.norm(pv)
    En = S + dn * (a * cosA) + pv * (a * np.sqrt(max(0.0, 1 - cosA * cosA)))
    _set_world_rot(sk, loc, W, th, align(E - S, En - S) @ W[th][1])
    W = _fk(sk, loc)
    E = W[ca][0]; G = W[ft][0]
    _set_world_rot(sk, loc, W, ca, align(G - E, S + dn * dc - E) @ W[ca][1])
    W = _fk(sk, loc)
    _set_world_rot(sk, loc, W, ft, foot_rot)

def _bones(cr, k):
    b = cr.cfg.BONES
    bones = [(nm, pr) for nm, _, pr in k.blocks]
    have = {nm for nm, _ in bones}
    base = max([p for _, p in bones] or [30])
    for nm in [b['root'], b['pelvis']] + b['leg_L'] + b['leg_R'] + list(cr.spine) + b.get('neck', []) + [cr.head]:
        if nm not in have and nm in cr.sk.local: bones.append((nm, base)); have.add(nm)
    return bones

def crouch_frames(cr, src, drop=0.20, lean=16.0, timescale=1.0, fps=30):
    """drop: pelvis drop as a fraction of the standing hip height (own idle, t=0)"""
    sk = cr.sk; b = cr.cfg.BONES
    k = KFEval(cr.path(src))
    idle = _fk(sk, _sample(cr, KFEval(cr.path(cr.cfg.IDLE_KF)), 0.0))
    hip = idle[b['pelvis']][0][2] - min(idle[b['leg_L'][2]][0][2], idle[b['leg_R'][2]][0][2])
    fwd_local = idle[b['root']][1].T @ np.array([0, 1.0, 0])    # NonAccum's local axis for creature-forward (+y)
    dz = drop * hip
    L = k.stop / timescale; n = max(2, int(round(L * fps)) + 1)
    sp = [nm for nm in cr.spine if nm in sk.local]
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        loc = _sample(cr, k, t * timescale)
        W0 = _fk(sk, loc)
        feet = {}
        for s in 'LR':
            th, ca, ft, toe = b['leg_' + s][:4]
            knee_p, foot_p = W0[ca][0], W0[ft][0]
            # knees bend the way the toes point (horizontal foot direction) - also for the yawed crab-run legs
            fdir = W0[toe][0] - foot_p if toe in W0 else np.array([0, 1.0, 0])
            fdir = np.array([fdir[0], fdir[1], 0.0])
            if np.linalg.norm(fdir) < 1e-3: fdir = np.array([0, 1.0, 0])
            # half toward the body's facing (NonAccum's creature-forward axis; also follows the crab-run yaw),
            # so splayed feet don't throw the knees outward
            body = W0[b['root']][1] @ fwd_local; body = np.array([body[0], body[1], 0.0]); body /= max(np.linalg.norm(body), 1e-6)
            pdir = body                                   # knees along the body facing (toe direction splays: unused)
            feet[s] = (foot_p.copy(), W0[ft][1].copy(), knee_p + pdir / max(np.linalg.norm(pdir), 1e-6) * 40.0)
        head0 = W0[cr.head][1].copy()
        # lower the body: NonAccum translation, expressed in its parent's frame
        rt, rR = loc[b['root']]
        pR = W0[sk.parent[b['root']]][1]
        loc[b['root']] = (rt - pR.T @ np.array([0, 0, dz]), rR)
        # lean the torso forward (about the body's lateral axis), spread over the spine
        lat = X                                    # creature space: +y forward, x lateral (accum root unrotated)
        for nm in sp:
            W = _fk(sk, loc); _set_world_rot(sk, loc, W, nm, rotm(lat, -lean / len(sp)) @ W[nm][1])
        W = _fk(sk, loc); _set_world_rot(sk, loc, W, cr.head, head0)            # head keeps looking ahead
        # legs: feet stay where they were, knees forward
        for s in 'LR':
            th, ca, ft = b['leg_' + s][:3]
            pos, rot, pole = feet[s]
            _leg_ik(sk, loc, th, ca, ft, pos, rot, pole + np.array([0, 0, -dz]))
        frames.append((t, loc))
    keys = [(min(tk / timescale, L), s) for tk, s in k.textkeys]
    return frames, _bones(cr, k), L, keys, k.cycle, k.name

def crab_frames(cr, src, side, yaw=70.0, fps=30):
    """side 'L' or 'R'. yaw: lower-body turn toward the motion (the spine twists the same amount back)"""
    sk = cr.sk; b = cr.cfg.BONES; acc = cr.cfg.ACCUM_ROOT
    k = KFEval(cr.path(src))
    sgn = 1.0 if side == 'L' else -1.0
    Rturn = rotm(Z, 90.0 * sgn)                  # forward travel (+y) -> left (-x) / right (+x)
    Ryaw = rotm(Z, yaw * sgn)
    L = k.stop; n = max(2, int(round(L * fps)) + 1)
    sp = [nm for nm in cr.spine if nm in sk.local]
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        loc = _sample(cr, k, t)
        at, aR = loc[acc]
        loc[acc] = (Rturn @ at, aR)                                            # travel sideways
        W = _fk(sk, loc)                                                       # body yaws toward the motion
        P = W[sk.parent[b['root']]][1]; rt, rR = loc[b['root']]
        loc[b['root']] = (P.T @ Ryaw @ P @ rt, P.T @ Ryaw @ P @ rR)
        for nm in sp:                                                          # upper body twists back to face ahead
            W = _fk(sk, loc)
            _set_world_rot(sk, loc, W, nm, rotm(Z, -yaw * sgn / len(sp)) @ W[nm][1])
        frames.append((t, loc))
    keys = list(k.textkeys)
    return frames, _bones(cr, k), L, keys, k.cycle, ('FastLeft' if side == 'L' else 'FastRight')
