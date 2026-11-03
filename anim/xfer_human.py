"""Human weapon animations onto a human-proportioned creature skeleton that keeps its own (hunched) torso.
usage: python3 xfer_human.py <creature cfg> <prefix, e.g. 1hp> <out dir>

For every human <prefix>*.kf in the creature's HUMAN_REF (aims, attacks, reloads, jams, equips; not jumps / turns):
  * torso, neck, head, legs: the creature's own pose (its idle, accum root at the origin) - the hunch stays;
  * each hand is placed where the human hand is relative to the human shoulder (UpperArm), measured from the
    creature's shoulder, with the human hand's world orientation; arms by 2-bone IK with the human elbow as the pole;
    for iron-sight files the right hand is placed relative to the head instead, so the sights stay at the eyes;
  * fingers, the Weapon node and any weapon-part tracks follow the human file (local transforms);
  * bones the human file doesn't key come from the human aim (or iron-sight aim) pose, as the engine layers them;
  * aim up / down variants (<group>up / <group>down): the human bends its spine to point the gun up / down; that bend
    (the human Spine2's world rotation against the level file at the same time) is spread over the creature's spine,
    so the shoulders follow the gun - kept upright, the arms folded into the chest to point it down (Ghost 2HR
    down: left elbow 1-4 units from the spine).
Text keys, length, cycle and per-bone priorities are the human file's, so sounds, fire / reload events and the
engine's timing are vanilla. Written with the human file's name; the caller copies sneak variants."""
import sys, os, re, importlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Creature, Rig, write_kf, align
from kf import KFEval, Skeleton

HUMAN_SKEL = '/home/claude/fnv/ref_weap/skeleton.nif'
ONE_HANDED = {'1hp'}               # aims / attacks keep the left hand off the gun

def human_fk(sk, smp, base):
    W = {}
    for nm in sk.order:
        t, R, _ = sk.local[nm]
        for src in (base, smp):
            if src is not None and nm in src:
                if src[nm][0] is not None: t = src[nm][0]
                if src[nm][1] is not None: R = src[nm][1]
        if nm == 'Bip01': R = np.eye(3)
        t = np.array(t, float); R = np.array(R, float); p = sk.parent[nm]
        W[nm] = (t, R) if p is None else (W[p][0] + W[p][1] @ t, W[p][1] @ R)
    return W

def human_local(sk, smp, base, nm):
    t, R, _ = sk.local[nm]
    for src in (base, smp):
        if src is not None and nm in src:
            if src[nm][0] is not None: t = src[nm][0]
            if src[nm][1] is not None: R = src[nm][1]
    return np.array(t, float), np.array(R, float)

_HIP_IS = {}
def hip_from_is(cr, ref, pre):
    """XFER_HIP_FROM_IS (cfg, world units at the level aim: x right, y forward, z up): the two-handed hip hold is the
    creature's own iron-sight hold moved by that much (a hunched creature's human-placed hip rifle hung out to the right
    of its chest; its iron-sight hold sits right). Returns the right hand's offset and turn from the hip aim to that
    hold, both in Spine2's frame, so up / down variants carry them with the bent chest."""
    key = (cr.cfg.__name__, pre)
    if key not in _HIP_IS:
        sp = cr.cfg.BONES['torso']; hand = cr.arm['R'][3]
        res = []
        for f, base in ((f'{pre}aim.kf', f'{pre}aim.kf'), (f'{pre}aimis.kf', f'{pre}aimis.kf')):
            fr = transfer(cr, os.path.join(ref, f), os.path.join(ref, base), twist=True, _hip_is=False)[0]
            res.append(Rig(cr, base_kf=cr.cfg.IDLE_KF).fk(fr[0][1]))
        Wh_, Wi = res; S0 = Wh_[sp][1]; wp = cr.weapon
        # the turn that brings the hip gun onto the sight gun, and the hand offset that then puts the gun where the
        # sight gun is (the Weapon node's own local transform differs between the hip and the sight files)
        Rc = Wi[wp][1] @ Wh_[wp][1].T
        off = (Wi[wp][0] + np.array(cr.cfg.XFER_HIP_FROM_IS, float)) - Rc @ (Wh_[wp][0] - Wh_[hand][0]) - Wh_[hand][0]
        _HIP_IS[key] = (S0.T @ off, S0.T @ Rc @ S0)
    return _HIP_IS[key]

def transfer(cr, hpath, base_path, fps=30, head_is=6.0, free_left=None, twist=False, _hip_is=True):
    """free_left: path of a human file whose left arm (t=0) replaces the file's own in aims / attacks (one-handed
    pistol aim - the creature's left hand doesn't take the two-handed iron-sight grip; reloads / jams / equips keep it)"""
    hs = Skeleton(HUMAN_SKEL)
    k = KFEval(hpath); kb = KFEval(base_path)
    base_h = kb.sample(0)
    name = os.path.basename(hpath).lower()
    iron = bool(re.search(r'is(up|down)?\.kf$', name))
    handwork = bool(re.search(r'reload|jam|equip|holster|grip', name))
    lvl = re.sub(r'(up|down)\.kf$', '.kf', name)
    lvl_path = os.path.join(os.path.dirname(hpath), lvl) if lvl != name else None
    kl = KFEval(lvl_path) if lvl_path and os.path.exists(lvl_path) else None
    Wfree = None
    if free_left and not handwork:
        kf_ = KFEval(free_left); Wfree = human_fk(hs, kf_.sample(0), None); smp_free = kf_.sample(0)
    rig = Rig(cr, base_kf=cr.cfg.IDLE_KF)
    b = cr.cfg.BONES
    hip = None
    if (_hip_is and twist and not iron and hasattr(cr.cfg, 'XFER_HIP_FROM_IS') and Wfree is None
            and not re.search(r'equip|holster|death', name)
            and os.path.exists(os.path.join(os.path.dirname(hpath), name[:3] + 'aimis.kf'))):   # (heavy weapons: no sights)
        hip = hip_from_is(cr, os.path.dirname(hpath), name[:3])
    L = k.stop; n = max(2, int(round(L * fps)) + 1)
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        smp = k.sample(t)
        Wh = human_fk(hs, smp, base_h)
        loc = {nm: (v[0].copy(), v[1].copy()) for nm, v in rig.base.items()}
        if iron:                                                   # look down the sights a little
            W = rig.fk(loc); rig.set_world_rot(loc, W, cr.head, align(np.array([0, 1.0, 0]), np.array([0, 1.0, -np.tan(np.radians(head_is))])) @ W[cr.head][1])
        W = rig.fk(loc)
        def bend():
            nonlocal W
            if kl is None: return
            Wl = human_fk(hs, kl.sample(min(t, kl.stop)), base_h)
            D = Wh['Bip01 Spine2'][1] @ Wl['Bip01 Spine2'][1].T
            ang = np.arccos(np.clip((np.trace(D) - 1) / 2, -1, 1))
            if ang > 1e-4:
                ax = np.array([D[2, 1] - D[1, 2], D[0, 2] - D[2, 0], D[1, 0] - D[0, 1]]) / (2 * np.sin(ang))
                a = ang / len(cr.spine); K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
                Rs = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
                for sp in cr.spine:
                    rig.set_world_rot(loc, W, sp, Rs @ W[sp][1]); W = rig.fk(loc)
        spine_twist = getattr(cr.cfg, 'XFER_TWIST_AXIS', 'world') == 'spine'
        if not spine_twist: bend()
        if twist and Wfree is None:
            # two-handed stances turn the human
            # torso ~40 deg (left shoulder forward); the creature kept its idle's shoulder line, its left shoulder 25
            # units further back, so the fore-end was out of reach (52 vs a 35.5 arm) and the off hand hung under the
            # magazine. The spine is turned about world Z (spread over its bones) until the shoulder line's heading
            # matches the human's; neck / head keep their world rotation (the face still looks down the sights).
            uaL, uaR = cr.arm['L'][1], cr.arm['R'][1]
            hd = lambda v: np.arctan2(v[1], v[0])
            d = hd(Wh[uaL][0] - Wh[uaR][0]) - hd(W[uaL][0] - W[uaR][0]); d = (d + np.pi) % (2 * np.pi) - np.pi
            clav_par = {cr.sk.parent[cr.arm[s_][0]] for s_ in ('L', 'R')}            # (the clavicles hang off Bip01 Neck)
            keep = {nm: W[nm][1].copy() for nm in (cr.cfg.BONES.get('neck', []) + [cr.head]) if nm in W and nm not in clav_par}
            if getattr(cr.cfg, 'XFER_TWIST_AXIS', 'world') == 'spine':
                # a hunched trunk turned about world Z swings the chest and head sideways (Ghost: head 16 units right
                # of the pelvis, rifle held far out to the right); turned about its own line (first spine bone ->
                # neck) the chest stays over the hips. The line is tilted, so the turn is repeated until the shoulder
                # heading matches.
                top = cr.cfg.BONES.get('neck', [cr.head])[0]
                for _ in range(4):
                    ax = W[top][0] - W[cr.spine[0]][0]; ax = ax / np.linalg.norm(ax)
                    a = d / len(cr.spine); K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
                    Ra = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
                    for sp in cr.spine:
                        rig.set_world_rot(loc, W, sp, Ra @ W[sp][1]); W = rig.fk(loc)
                    d = hd(Wh[uaL][0] - Wh[uaR][0]) - hd(W[uaL][0] - W[uaR][0]); d = (d + np.pi) % (2 * np.pi) - np.pi
                    if abs(d) < np.radians(0.5): break
            else:
                c, s = np.cos(d / len(cr.spine)), np.sin(d / len(cr.spine)); Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
                for sp in cr.spine:
                    rig.set_world_rot(loc, W, sp, Rz @ W[sp][1]); W = rig.fk(loc)
            for nm, Rk in keep.items():
                rig.set_world_rot(loc, W, nm, Rk); W = rig.fk(loc)
        if spine_twist: bend()      # turned about the upright trunk first, then bent up / down
        for side in ('R', 'L'):
            cl, ua, fa, hand = cr.arm[side]
            if side == 'L' and Wfree is not None:                 # one-handed: left arm from the hip aim
                Sg = W[ua][0]; Sh = Wfree[ua][0]
                loc = rig.ik(loc, side, Sg + (Wfree[hand][0] - Sh), loc[hand][0], Sg + (Wfree[fa][0] - Sh) * 2.0)
                W = rig.fk(loc); rig.set_world_rot(loc, W, hand, Wfree[hand][1]); W = rig.fk(loc)
                continue
            Sg = W[ua][0]; Sh = Wh[ua][0]
            if iron and side == 'R':
                # XFER_IS_SHIFT (cfg, world units): a muzzle / jaw that sticks out further than a human face
                # (Feral Ghoul,: the stock went through the jaw) pushes the iron-sight hold forward
                tgt = W[cr.head][0] + (Wh[hand][0] - Wh[cr.head][0]) + np.array(getattr(cr.cfg, 'XFER_IS_SHIFT', (0, 0, 0)), float)
            else:
                tgt = Sg + (Wh[hand][0] - Sh)
                if twist and not iron and hip is None and _hip_is and not re.search(r'equip|holster|death', name):
                    # XFER_HIP_SHIFT (cfg, world units): the hip hold moved toward the middle (a hunched trunk that
                    # stays over the hips leaves a human-placed hip rifle hanging out to the right of the chest);
                    # types with iron sights use XFER_HIP_FROM_IS instead when the cfg has it
                    tgt = tgt + np.array(getattr(cr.cfg, 'XFER_HIP_SHIFT', (0, 0, 0)), float)
            pole = Sg + (Wh[fa][0] - Sh) * 2.0
            Rhand = Wh[hand][1]
            if hip is not None:                                    # hip hold = the creature's iron-sight hold, moved
                S = W[b['torso']][1]; off = S @ hip[0]; Rc = S @ hip[1] @ S.T
                tgt = tgt + off; pole = pole + off; Rhand = Rc @ Rhand
            loc = rig.ik(loc, side, tgt, loc[hand][0], pole)
            W = rig.fk(loc)
            rig.set_world_rot(loc, W, hand, Rhand)
            W = rig.fk(loc)
        # the left hand follows the weapon when the human's does (two-handed grips): re-solve it in the weapon frame
        for nm in cr.fingers['R'] + cr.fingers['L'] + [cr.weapon]:
            if nm in hs.local and nm in loc:
                loc[nm] = human_local(hs, smp_free, None, nm) if (Wfree is not None and nm in cr.fingers['L']) else human_local(hs, smp, base_h, nm)
        W = rig.fk(loc)
        dist_h = np.linalg.norm(Wh[cr.arm['L'][3]][0] - Wh[cr.weapon][0])
        if dist_h < (24.0 if twist else 18.0) and Wfree is None:    # human left hand on the gun (two-handed: 24 - the human 2HA hip aim holds the fore-end at 18.3)
            rel = Wh[cr.weapon][1].T @ (Wh[cr.arm['L'][3]][0] - Wh[cr.weapon][0])
            relR = Wh[cr.weapon][1].T @ Wh[cr.arm['L'][3]][1]
            Wg = W[cr.weapon]
            tgt = Wg[0] + Wg[1] @ rel
            cl, ua, fa, hand = cr.arm['L']
            loc = rig.ik(loc, 'L', tgt, loc[hand][0], W[ua][0] + (Wh[fa][0] - Wh[ua][0]) * 2.0)
            W = rig.fk(loc); rig.set_world_rot(loc, W, hand, Wg[1] @ relR)
        frames.append((t, loc))
    # bones: creature upper body + spine/head (held at its own pose); priorities from the human file
    pr = {nm: p for nm, _, p in k.blocks}
    top = max(pr.values()) if pr else 65
    names = list(cr.spine) + b.get('neck', []) + [cr.head]
    for side in ('R', 'L'): names += list(cr.arm[side]) + list(cr.fingers[side])
    names.append(cr.weapon)
    bones = []
    for nm in names:
        if nm in cr.sk.local: bones.append((nm, pr.get(nm, top)))
    return frames, bones, L, list(k.textkeys), k.cycle, k.name

if __name__ == '__main__':
    cfg = importlib.import_module('creatures.' + sys.argv[1]); pre = sys.argv[2]; out = sys.argv[3]
    cr = Creature(cfg); ref = cfg.HUMAN_REF
    os.makedirs(out, exist_ok=True)
    files = sorted(f for f in os.listdir(ref) if f.lower().startswith(pre) and f.endswith('.kf')
                   and not re.search(r'jump|turn', f.lower()))
    for f in files:
        base = os.path.join(ref, f'{pre}aimis.kf' if re.search(r'is(up|down)?\.kf$', f.lower()) else f'{pre}aim.kf')
        free = os.path.join(ref, f'{pre}aim.kf') if pre in ONE_HANDED else None
        fr, bones, L, keys, cyc, seq = transfer(cr, os.path.join(ref, f), base, free_left=free, twist=pre not in ONE_HANDED)
        write_kf(cr, os.path.join(out, f), seq, L, keys, fr, bones=bones, cycle=cyc)
    print(len(files), 'files ->', out)
