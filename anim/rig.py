"""Creature rig: FK/IK posing on a creature's own skeleton + KF writer.  Creature-agnostic; everything
creature-specific (bone names, grasp point, source folder) comes from a creature config (creatures/*.py).

Pose model for procedural motions (per sample time u in 0..1, see Plan):
  * base = one of the creature's own static poses (usually an aim KF)
  * torso: lean / twist spread over the spine bones, head pitch
  * weapon arm: the weapon node is driven to a target position/orientation (offset from its base pose,
    following the torso); wrist from the weapon offset, elbow by 2-bone IK
  * off hand: palm point (cfg.GRASP in the hand frame) by 2-bone IK (forearm+hand rigid) to anchors in
    the weapon frame, the torso, or its own base position; optional finger curl
Only rotations are changed, so bone lengths are always the creature's own.
"""
import struct, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/claude/fnv')
from kf import Skeleton, KF, KFEval, q2m, m2q, slerp
from nifedit import NifFile

def rotm(axis, deg):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a); t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K

def align(u, v):
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    c = np.cross(u, v); s = np.linalg.norm(c); d = np.dot(u, v)
    if s < 1e-8:
        if d > 0: return np.eye(3)
        return rotm(np.cross(u, [1, 0, 0]) if abs(u[0]) < .9 else np.cross(u, [0, 1, 0]), 180)
    return rotm(c, np.degrees(np.arctan2(s, d)))

def orth(M):
    """nearest rotation. Sampled KF keys and skeleton binds can be slightly non-orthonormal (Hillfolk idle
    Spine det 0.994); set_world_rot's parent.T as inverse then amplified the error down the arm chain (Hillfolk weapon
    frame error 0.55: the synthetic rifle pointed sideways). Every base rotation is cleaned once here."""
    U, _, Vt = np.linalg.svd(M); R = U @ Vt
    if np.linalg.det(R) < 0: U[:, -1] *= -1; R = U @ Vt
    return R
def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def lerp(a, b, u): return a + (b - a) * u

class Creature:
    def __init__(s, cfg):
        s.cfg = cfg
        s.src = cfg.ANIM_SRC
        s.sk = Skeleton(cfg.SKELETON)
        b = cfg.BONES
        s.spine = b['spine']; s.head = b['head']; s.torso = b['torso']; s.weapon = b['weapon']
        s.arm = {side: b['arm_' + side] for side in ('R', 'L')}          # clavicle, upper, fore, hand
        s.fingers = {side: b['fingers_' + side] for side in ('R', 'L')}
        s.curl = b.get('curl_L', [])
        s.upper = list(s.spine) + b.get('neck', []) + [s.head]
        for side in ('R', 'L'): s.upper += list(s.arm[side]) + list(s.fingers[side])
        s.upper += [s.weapon]
        s.upper = [n for n in s.upper if n in s.sk.local]
        s.extra = {}                       # synthetic/generated files usable as sources (name -> path)
        s.mode = getattr(cfg, 'BASE_MODE', 'static')
        s._under = None
    def path(s, name): return s.extra.get(name) or os.path.join(s.src, name)
    def underlay(s):
        """standing pose (idle t=0) that upper-body-only animations are layered on (sample mode only)"""
        if s._under is None: s._under = KFEval(s.path(s.cfg.IDLE_KF)).sample(0)
        return s._under

class Rig:
    def __init__(s, cr, base_kf=None, base_pose=None):
        s.cr = cr; sk = cr.sk
        if cr.mode == 'sample':
            P = dict(cr.underlay())
            src = base_pose if base_pose is not None else KFEval(cr.path(base_kf)).sample(0)
            P.update({k: v for k, v in src.items() if k != cr.cfg.ACCUM_ROOT})
        else:
            P = base_pose if base_pose is not None else KF(cr.path(base_kf)).static_pose()
        s.base = {}
        for nm in sk.order:
            t, R, _ = sk.local[nm]
            if nm in P:
                if P[nm][0] is not None: t = P[nm][0]
                if P[nm][1] is not None: R = P[nm][1]
            s.base[nm] = (np.array(t, float), orth(np.array(R, float)))
        if cr.mode == 'sample':                       # accum root sits at the actor origin in game
            s.base[cr.cfg.ACCUM_ROOT] = (np.zeros(3), np.eye(3))
        s.W0 = s.fk(s.base)
        s.T0 = s.W0[cr.torso]
        # cfg.WEAPON_OFFSET (weapon frame: +X barrel, +Y up, +Z right): the gun sits that far from where the hand's
        # Weapon node would put it (deathclaw: its claws run along the barrel and swallowed the gun). The hold keeps the
        # gun where W0 says; the hand moves the other way.
        # (only on a pose sampled from a file: a base_pose made by pose() already carries them)
        off = getattr(cr.cfg, 'WEAPON_OFFSET', None) if base_pose is None else None
        if off is not None:
            t, R = s.base[cr.weapon]; s.base[cr.weapon] = (t + R @ np.asarray(off, float), R)
        # cfg.WEAPON_GRIP_ROT (deg about the weapon's Z, then Y, then X): the hand turned on the grip, so the gun keeps its
        # aim and the hand / claws hold it at another angle (deathclaw: claws down and to the side, forearm behind)
        gr = getattr(cr.cfg, 'WEAPON_GRIP_ROT', None) if base_pose is None else None
        if gr is not None:
            t, R = s.base[cr.weapon]
            s.base[cr.weapon] = (t, R @ rotm([0, 0, 1.0], gr[0]) @ rotm([0, 1.0, 0], gr[1]) @ rotm([1.0, 0, 0], gr[2]))
    def fk(s, loc):
        sk = s.cr.sk; W = {}
        for nm in sk.order:
            t, R = loc[nm]; p = sk.parent[nm]
            if p is None: W[nm] = (t.copy(), R.copy())
            else:
                pp, pR = W[p]; W[nm] = (pp + pR @ t, pR @ R)
        return W
    @staticmethod
    def to_frame(F, p): return F[1].T @ (p - F[0])
    @staticmethod
    def from_frame(F, q): return F[0] + F[1] @ q
    def set_world_rot(s, loc, W, nm, Rw):
        loc[nm] = (loc[nm][0], W[s.cr.sk.parent[nm]][1].T @ Rw)
    def ik(s, loc, side, target, end_local, pole_world):
        _, ua, fa, _ = s.cr.arm[side]
        W = s.fk(loc)
        S = W[ua][0]; E = W[fa][0]; G = W[fa][0] + W[fa][1] @ end_local
        a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
        d = target - S; dist = np.linalg.norm(d)
        dist_c = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.995)
        dn = d / dist
        cosA = (a * a + dist_c * dist_c - b * b) / (2 * a * dist_c)
        pv = pole_world - S; pv = pv - dn * np.dot(pv, dn)
        if np.linalg.norm(pv) < 1e-6: pv = np.cross(dn, [1, 0, 0])
        pv /= np.linalg.norm(pv)
        E_new = S + dn * (a * cosA) + pv * (a * np.sqrt(max(0.0, 1 - cosA * cosA)))
        s.set_world_rot(loc, W, ua, align(E - S, E_new - S) @ W[ua][1])
        W = s.fk(loc)
        E = W[fa][0]; G = W[fa][0] + W[fa][1] @ end_local
        s.set_world_rot(loc, W, fa, align(G - E, S + dn * dist_c - E) @ W[fa][1])
        return loc
    def offhand_end(s, loc):
        _, _, fa, hand = s.cr.arm['L']
        t, R = loc[hand]
        return t + R @ np.asarray(s.cr.cfg.GRASP, float)

class Plan:
    """keys: list of (u, dict).  Params (carried forward between keys, eased with smoothstep):
       lean (deg, forward +), twist (deg, torso turns toward the weapon side +), head (deg down +),
       wpos (world-axis offset of the weapon node from its base position; follows the torso),
       roll (deg about the barrel), pitch (deg muzzle up +), yaw (deg),
       lhand: ('base',) | ('weapon', xyz in weapon frame) | ('torso', world-axis offset from base torso),
       curl (0..1 off-hand finger curl), jit (deg of weapon jitter amplitude)"""
    DEF = dict(lean=0.0, twist=0.0, head=0.0, wpos=np.zeros(3), roll=0.0, pitch=0.0, yaw=0.0,
               lhand=('base',), curl=0.0, jit=0.0)
    def __init__(s, keys):
        s.keys = []; cur = dict(s.DEF)
        for u, kv in keys:
            cur = dict(cur); cur.update({k: (np.array(v, float) if k == 'wpos' else v) for k, v in kv.items()})
            s.keys.append((u, cur))
    def at(s, u):
        ks = s.keys
        if u <= ks[0][0]: return ks[0][1], ks[0][1], 0.0
        for (u0, a), (u1, b) in zip(ks, ks[1:]):
            if u <= u1: return a, b, smooth((u - u0) / (u1 - u0)) if u1 > u0 else 1.0
        return ks[-1][1], ks[-1][1], 0.0

def pose(rig, plan, u, t_abs=0.0):
    cr = rig.cr; a, b, w = plan.at(u)
    P = {k: lerp(np.asarray(a[k], float), np.asarray(b[k], float), w) for k in a if k != 'lhand'}
    loc = dict(rig.base); W0 = rig.W0
    up = np.array([0, 0, 1.0]); lat = np.array([1.0, 0, 0])
    # torso
    n = max(1, len(cr.spine) - 1)
    Rl = rotm(lat, -P['lean'] / n) @ rotm(up, -P['twist'] / n)
    for nm in cr.spine[1:]:
        W = rig.fk(loc); rig.set_world_rot(loc, W, nm, Rl @ W[nm][1])
    W = rig.fk(loc); rig.set_world_rot(loc, W, cr.head, rotm(lat, -P['head']) @ W[cr.head][1])
    W = rig.fk(loc); T = W[cr.torso]
    Tmap = lambda p: rig.from_frame(T, rig.to_frame(rig.T0, p))
    Rmap = T[1] @ rig.T0[1].T
    # weapon arm
    wp0, wR0 = W0[cr.weapon]
    barrel, wup = wR0[:, 0], wR0[:, 1]; side = np.cross(barrel, wup)
    jit = P['jit']
    jr = jit * np.sin(t_abs * 97.0) if jit else 0.0; jp = jit * np.sin(t_abs * 71.0 + 1.3) if jit else 0.0
    Rt = rotm(barrel, P['roll'] + jr) @ rotm(side, P['pitch'] + jp) @ rotm(wup, P['yaw'])
    wR = Rmap @ Rt @ wR0
    wpos = Tmap(wp0 + P['wpos'])
    tw, tR = loc[cr.weapon]
    handR = wR @ tR.T
    wrist = wpos - handR @ tw
    _, _, rfa, rhand = cr.arm['R']
    rig.ik(loc, 'R', wrist, loc[rhand][0], Tmap(W0[rfa][0]) + np.asarray(cr.cfg.POLE_R, float))
    W = rig.fk(loc); rig.set_world_rot(loc, W, rhand, handR)
    W = rig.fk(loc)
    # off hand
    _, _, lfa, lhand = cr.arm['L']
    def ltarget(spec):
        if spec[0] == 'base':
            h0 = W0[lhand]; return Tmap(h0[0] + h0[1] @ np.asarray(cr.cfg.GRASP, float))
        if spec[0] == 'weapon':
            wp, wr = W[cr.weapon]; return wp + wr @ np.asarray(spec[1], float)
        if spec[0] == 'torso':
            return Tmap(W0[cr.torso][0] + np.asarray(spec[1], float))
        raise ValueError(spec)
    tgt = lerp(ltarget(a['lhand']), ltarget(b['lhand']), w)
    rig.ik(loc, 'L', tgt, rig.offhand_end(loc), Tmap(W0[lfa][0]) + np.asarray(cr.cfg.POLE_L, float))
    if P['curl'] > 1e-3:
        for nm in cr.curl:
            # +Z flexes the fingers toward the palm on every creature (was -35: bent them backwards)
            t, R = loc[nm]; loc[nm] = (t, R @ rotm(cr.cfg.CURL_AXIS, 35 * P['curl']))
    return loc

def sample(rig, plan, length, fps=30):
    n = max(2, int(round(length * fps)) + 1)
    return [(length * i / (n - 1), pose(rig, plan, i / (n - 1), length * i / (n - 1))) for i in range(n)]

# ---------------- overlay: creature's own keyed KF + off-hand IK onto the weapon ----------------
def offhand_overlay(cr, src_kf, grip, fps=30, blend_in=None):
    """Samples one of the creature's own animations and pins the off-hand palm to `grip` (weapon frame)
    every frame. blend_in: optional (t0, t1) over which the IK weight ramps 0->1 (e.g. after Attach)."""
    k = KFEval(cr.path(src_kf))
    L = k.stop; n = max(2, int(round(L * fps)) + 1)
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        smp = k.sample(t)
        rig = Rig(cr, base_pose=smp)
        loc = dict(rig.base)
        W = rig.fk(loc); wp, wr = W[cr.weapon]
        tgt_grip = wp + wr @ np.asarray(grip, float)
        _, _, lfa, lhand = cr.arm['L']
        wgt = 1.0
        if blend_in: wgt = smooth((t - blend_in[0]) / max(1e-6, blend_in[1] - blend_in[0]))
        if wgt > 0:
            free = W[lhand][0] + W[lhand][1] @ np.asarray(cr.cfg.GRASP, float)
            tgt = lerp(free, tgt_grip, wgt)
            pole = W[lfa][0] + np.asarray(cr.cfg.POLE_L, float)
            rig.ik(loc, 'L', tgt, rig.offhand_end(loc), pole)
        frames.append((t, loc))
    bones = [(nm, pr) for nm, _, pr in k.blocks]
    return frames, bones, k

def offhand_release(cr, src_kf, fps=30):
    """samples one of the creature's own two-handed animations and lets the off arm hang in the
    standing pose (local rotations of the off arm + fingers from the idle), for one-handed use. The accum root keeps
    the source's keys: the Rig puts it at the origin, which took the travel out of the lunges (the Ghost's 1HM
    directional power attacks stood in place, and power_legs then dropped their legs)"""
    k = KFEval(cr.path(src_kf)); L = k.stop; n = max(2, int(round(L * fps)) + 1)
    idle = Rig(cr, base_kf=cr.cfg.IDLE_KF).base
    free = list(cr.arm['L']) + list(cr.fingers['L'])
    AR = cr.cfg.ACCUM_ROOT
    frames = []
    for i in range(n):
        t = L * i / (n - 1); smp = k.sample(t)
        rig = Rig(cr, base_pose=smp); loc = dict(rig.base)
        for nm in free:
            if nm in idle: loc[nm] = idle[nm]
        if AR in smp and AR in loc:
            p, R = smp[AR]
            loc[AR] = (np.array(p, float) if p is not None else loc[AR][0], np.array(R, float) if R is not None else loc[AR][1])
        frames.append((t, loc))
    return frames, [(nm, pr) for nm, _, pr in k.blocks], k

# ---------------- KF writer ----------------
def write_kf(cr, path, seqname, length, textkeys, frames, bones=None, priority=65, cycle=2):
    """frames: [(time, loc)]. bones: [(name, priority)] (default: creature upper body at `priority`).
    Writes rotation keys (linear) and translation keys where translation changes."""
    if bones is None: bones = [(nm, priority) for nm in cr.upper]
    seen = set(); bl = []
    for nm, pr in bones:
        if nm in seen or nm not in cr.sk.local: continue
        seen.add(nm); bl.append((nm, pr))
    f = NifFile(cr.path(cr.cfg.TEMPLATE_KF))
    f.types = []; f.btype = []; f.blocks = []; f.strings = []
    si = f.str_index
    si(cr.cfg.ACCUM_ROOT); si('NiTransformController')
    seq_i = f.add_block('NiControllerSequence', b'')
    tk = struct.pack('<iI', -1, len(textkeys)) + b''.join(struct.pack('<fi', t, si(s)) for t, s in textkeys)
    tk_i = f.add_block('NiTextKeyExtraData', tk)
    cbs = []
    for nm, pr in bl:
        qs = []; ts = []; prev = None
        for t, loc in frames:
            q = m2q(loc[nm][1])
            if prev is not None and np.dot(q, prev) < 0: q = -q
            qs.append((t, q)); prev = q; ts.append((t, loc[nm][0]))
        rstatic = all(np.allclose(q, qs[0][1], atol=1e-5) for _, q in qs)
        tstatic = all(np.allclose(p, ts[0][1], atol=1e-4) for _, p in ts)
        data = -1
        if not (rstatic and tstatic):
            body = b''
            if rstatic: body += struct.pack('<I', 0)
            else: body += struct.pack('<II', len(qs), 1) + b''.join(struct.pack('<f4f', t, *q) for t, q in qs)
            if tstatic: body += struct.pack('<I', 0)
            else: body += struct.pack('<II', len(ts), 1) + b''.join(struct.pack('<f3f', t, *p) for t, p in ts)
            body += struct.pack('<I', 0)
            data = f.add_block('NiTransformData', body)
        interp = struct.pack('<3f4ffi', *ts[0][1], *qs[0][1], 1.0, data)
        ii = f.add_block('NiTransformInterpolator', interp)
        cbs.append(struct.pack('<iiBiiiii', ii, -1, pr, si(nm), -1, si('NiTransformController'), -1, -1))
    seq = struct.pack('<iII', si(seqname), len(cbs), 1) + b''.join(cbs)
    seq += struct.pack('<fiIfffii', 1.0, tk_i, cycle, 1.0, 0.0, length, -1, si(cr.cfg.ACCUM_ROOT)) + struct.pack('<H', 0)
    f.blocks[seq_i] = seq
    f.footer = struct.pack('<Ii', 1, 0)
    open(path, 'wb').write(f.to_bytes())
