"""Procedural creature reload/jam authoring on the creature's own skeleton and aim pose.

Pose model (per sample time):
  * base = the creature's own aim pose (static KF) for all upper-body bones
  * spine/head: extra pitch/roll (world axes of Bip01)
  * right arm: the Weapon node is driven to a target position + orientation expressed in the
    torso (Spine2) frame of the aim pose; wrist solved from the weapon offset, elbow by 2-bone IK
  * left arm: the grasp point (palm, ~10 units down the huge alien hand) is driven by 2-bone IK
    (forearm+hand rigid) to anchors in the weapon frame, torso frame or its own aim position
  * left fingers: optional curl
Only rotations are keyed; translations stay at the aim/bind values, so bone lengths never change.
"""
import struct, sys, numpy as np
sys.path.insert(0, '/home/claude/fnv')
from kf import Skeleton, KF, q2m, m2q
from nifedit import NifFile

A = '/home/claude/fnv/assets/meshes/dlc05/creatures/alien/'
SK = Skeleton(A + 'skeleton.nif')

UPPER = ['Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2', 'Bip01 Neck', 'Bip01 Neck1', 'Bip01 Head']
for side in 'RL':
    UPPER += [f'Bip01 {side} Clavicle', f'Bip01 {side} UpperArm', f'Bip01 {side} Forearm', f'Bip01 {side} Hand']
    UPPER += [f'Bip01 {side} Finger{a}{b}' for a in '012' for b in ('', '1', '2')]
UPPER += ['Weapon']

def rotm(axis, deg):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a); t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K

def align(u, v):
    """minimal rotation taking direction u to direction v"""
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    c = np.cross(u, v); s = np.linalg.norm(c); d = np.dot(u, v)
    if s < 1e-8: return np.eye(3) if d > 0 else rotm(np.cross(u, [1, 0, 0]) if abs(u[0]) < .9 else np.cross(u, [0, 1, 0]), 180)
    return rotm(c, np.degrees(np.arctan2(s, d)))

def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)

class Rig:
    def __init__(s, aimkf):
        P = KF(A + aimkf).static_pose()
        s.base = {}
        for nm in SK.order:
            t, R, _ = SK.local[nm]
            if nm in P:
                if P[nm][0] is not None: t = P[nm][0]
                if P[nm][1] is not None: R = P[nm][1]
            s.base[nm] = (np.array(t, float), np.array(R, float))
        s.W0 = s.fk(s.base)
        s.T0 = s.W0['Bip01 Spine2']
    def fk(s, loc):
        W = {}
        for nm in SK.order:
            t, R = loc[nm]; p = SK.parent[nm]
            if p is None: W[nm] = (t.copy(), R.copy())
            else:
                pp, pR = W[p]; W[nm] = (pp + pR @ t, pR @ R)
        return W
    # frame helpers: express/restore points & rotations in a frame (pos, R)
    @staticmethod
    def to_frame(F, p): return F[1].T @ (p - F[0])
    @staticmethod
    def from_frame(F, q): return F[0] + F[1] @ q
    def set_world_rot(s, loc, W, nm, Rw):
        pR = W[SK.parent[nm]][1]
        loc[nm] = (loc[nm][0], pR.T @ Rw)
    def ik(s, loc, side, target, end_local, pole_world):
        """2-bone IK. end_local = end effector in the Forearm frame (rigid forearm+hand).
        Rotates UpperArm and Forearm so the effector reaches target (clamped)."""
        ua, fa = f'Bip01 {side} UpperArm', f'Bip01 {side} Forearm'
        W = s.fk(loc)
        S = W[ua][0]; E = W[fa][0]; G = W[fa][0] + W[fa][1] @ end_local
        a = np.linalg.norm(E - S); b = np.linalg.norm(G - E)
        d = target - S; dist = np.linalg.norm(d)
        dist_c = np.clip(dist, abs(a - b) + 1e-3, (a + b) * 0.995)
        dn = d / dist
        # elbow position in the plane of (S, target, pole)
        cosA = (a * a + dist_c * dist_c - b * b) / (2 * a * dist_c)
        pv = pole_world - S; pv = pv - dn * np.dot(pv, dn)
        if np.linalg.norm(pv) < 1e-6: pv = np.cross(dn, [1, 0, 0])
        pv /= np.linalg.norm(pv)
        E_new = S + dn * (a * cosA) + pv * (a * np.sqrt(max(0.0, 1 - cosA * cosA)))
        # upper arm: rotate so S->E becomes S->E_new
        R1 = align(E - S, E_new - S)
        s.set_world_rot(loc, W, ua, R1 @ W[ua][1])
        W = s.fk(loc)
        E = W[fa][0]; G = W[fa][0] + W[fa][1] @ end_local
        tgt = S + dn * dist_c
        R2 = align(G - E, tgt - E)
        s.set_world_rot(loc, W, fa, R2 @ W[fa][1])
        return loc

def lerp(a, b, u): return a + (b - a) * u

class Plan:
    """keys: list of (u, dict). Params (all optional, carried forward):
       lean (deg forward), twist (deg, + turns toward the weapon side), head (deg down),
       wpos (world-axis offset of the Weapon node from its aim position; follows the torso),
       roll (deg about the barrel), pitch (deg muzzle up), yaw (deg muzzle inward),
       lhand: ('aim',) | ('weapon', offset xyz in weapon frame) | ('torso', world-axis offset from the aim Spine2 position; follows the torso)
       curl (0..1 left finger curl)"""
    DEF = dict(lean=0.0, twist=0.0, head=0.0, wpos=np.zeros(3), roll=0.0, pitch=0.0, yaw=0.0,
               lhand=('aim',), curl=0.0)
    def __init__(s, keys):
        s.keys = []
        cur = dict(s.DEF)
        for u, kv in keys:
            cur = dict(cur); cur.update({k: (np.array(v, float) if k == 'wpos' else v) for k, v in kv.items()})
            s.keys.append((u, cur))
    def at(s, u):
        ks = s.keys
        if u <= ks[0][0]: return ks[0][1], ks[0][1], 0.0
        for (u0, a), (u1, b) in zip(ks, ks[1:]):
            if u <= u1: return a, b, smooth((u - u0) / (u1 - u0))
        return ks[-1][1], ks[-1][1], 0.0

GRASP = np.array([10.0, 0.0, 0.0])      # palm point in the hand frame (alien hands are ~13.5 long)

def pose(rig, plan, u):
    a, b, w = plan.at(u)
    P = {k: (lerp(np.asarray(a[k], float), np.asarray(b[k], float), w) if k != 'lhand' else None) for k in a}
    loc = dict(rig.base)
    W0 = rig.W0
    up = np.array([0, 0, 1.0]); lat = np.array([1.0, 0, 0])
    # --- torso ---
    W = rig.fk(loc)
    Rl = rotm(lat, -P['lean'] * 0.5) @ rotm(up, -P['twist'] * 0.5)
    for nm in ('Bip01 Spine1', 'Bip01 Spine2'):
        W = rig.fk(loc); rig.set_world_rot(loc, W, nm, Rl @ W[nm][1])
    W = rig.fk(loc); rig.set_world_rot(loc, W, 'Bip01 Head', rotm(lat, -P['head']) @ W['Bip01 Head'][1])
    W = rig.fk(loc)
    T = W['Bip01 Spine2']
    # frame mapping aim-torso -> current torso
    Tmap = lambda p: rig.from_frame(T, rig.to_frame(rig.T0, p))
    Rmap = T[1] @ rig.T0[1].T
    # --- right arm / weapon ---
    wp0, wR0 = W0['Weapon']
    barrel, wup = wR0[:, 0], wR0[:, 1]
    side = np.cross(barrel, wup)
    Rt = rotm(barrel, P['roll']) @ rotm(side, P['pitch']) @ rotm(wup, P['yaw'])
    wR = Rmap @ Rt @ wR0
    wpos = Tmap(wp0 + P['wpos'])
    tw, tR = loc['Weapon']
    handR = wR @ tR.T
    wrist = wpos - handR @ tw
    elbow0 = Tmap(W0['Bip01 R Forearm'][0])
    rig.ik(loc, 'R', wrist, loc['Bip01 R Hand'][0], elbow0 + np.array([6, -4, -4.0]))
    W = rig.fk(loc); rig.set_world_rot(loc, W, 'Bip01 R Hand', handR)
    W = rig.fk(loc)
    # --- left arm ---
    def ltarget(spec):
        if spec[0] == 'aim':
            h0 = W0['Bip01 L Hand']; return Tmap(h0[0] + h0[1] @ GRASP)
        if spec[0] == 'weapon':
            wp, wr = W['Weapon']; return wp + wr @ np.asarray(spec[1], float)
        if spec[0] == 'torso':
            return Tmap(W0['Bip01 Spine2'][0] + np.asarray(spec[1], float))
        raise ValueError(spec)
    tgt = lerp(ltarget(a['lhand']), ltarget(b['lhand']), w)
    fa_t, fa_R = loc['Bip01 L Hand']
    end_local = fa_t + fa_R @ GRASP
    elbowL = Tmap(W0['Bip01 L Forearm'][0])
    rig.ik(loc, 'L', tgt, end_local, elbowL + np.array([-8, 0, -6.0]))
    # finger curl (bend each finger joint about its local z)
    if P['curl'] > 1e-3:
        for f in '12':
            for seg in ('', '1', '2'):
                nm = f'Bip01 L Finger{f}{seg}'
                t, R = loc[nm]; loc[nm] = (t, R @ rotm([0, 0, 1], -35 * P['curl']))
    return loc

# ---------------- KF writer ----------------
def write_kf(path, seqname, length, textkeys, frames, fps=30, priority=65, cycle=2):
    """frames: list of (time, loc dict). Writes UPPER bones: rotation keys (linear), static translation."""
    f = NifFile(A + '2hraim.kf')
    f.types = []; f.btype = []; f.blocks = []; f.strings = []
    si = f.str_index
    si('Bip01'); si('NiTransformController')
    seq_i = f.add_block('NiControllerSequence', b'')      # placeholder, filled last
    tk = struct.pack('<iI', -1, len(textkeys)) + b''.join(struct.pack('<fi', t, si(s)) for t, s in textkeys)
    tk_i = f.add_block('NiTextKeyExtraData', tk)
    cbs = []
    for nm in UPPER:
        t0 = frames[0][1][nm][0]
        qs = []
        prev = None
        for t, loc in frames:
            q = m2q(loc[nm][1])
            if prev is not None and np.dot(q, prev) < 0: q = -q
            qs.append((t, q)); prev = q
        static = all(np.allclose(q, qs[0][1], atol=1e-5) for _, q in qs)
        if static:
            q0 = qs[0][1]
            data = -1
        else:
            body = struct.pack('<II', len(qs), 1) + b''.join(struct.pack('<f4f', t, *q) for t, q in qs)
            body += struct.pack('<I', 0) + struct.pack('<I', 0)      # no translation / scale keys
            data = f.add_block('NiTransformData', body)
            q0 = qs[0][1]
        interp = struct.pack('<3f4ffi', *t0, *q0, 1.0, data)
        ii = f.add_block('NiTransformInterpolator', interp)
        cbs.append(struct.pack('<iiBiiiii', ii, -1, priority, si(nm), -1, si('NiTransformController'), -1, -1))
    seq = struct.pack('<iII', si(seqname), len(cbs), 1) + b''.join(cbs)
    seq += struct.pack('<fiIfffii', 1.0, tk_i, cycle, 1.0, 0.0, length, -1, si('Bip01')) + struct.pack('<H', 0)
    f.blocks[seq_i] = seq
    f.footer = struct.pack('<Ii', 1, 0)
    open(path, 'wb').write(f.to_bytes())

def sample(rig, plan, length, fps=30):
    n = max(2, int(round(length * fps)) + 1)
    return [(length * i / (n - 1), pose(rig, plan, i / (n - 1))) for i in range(n)]
