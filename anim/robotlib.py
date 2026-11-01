"""Shared helpers for the robot animation sets (Playable Creatures).
Generalised from build_securitron.py / build_eyebot.py: resampling a creature's own motion under a human group's
name / length / cycle / text keys, prn (projectile node) re-parenting, extra channels (scale-keyed FX nodes),
world-axis pose edits."""
import os, re, shutil, struct
import numpy as np
from kf import KF, KFEval, Skeleton
from holster_fix import KFFile
from hip_spine_fix import drop_channel, retarget_channel

DROP = re.compile(r'^(prn:|enum:|m: |sound: pczetan|sound: npcdlc05alien|-global)', re.I)


class Ctx:
    def __init__(s, src_dirs, skel):
        s.dirs = src_dirs
        sk = Skeleton(skel); s.sk = sk; s.BIND = sk.local

    def find(s, name):
        for d in s.dirs:
            p = os.path.join(d, name)
            if os.path.exists(p): return p
        return None

    def fill(s, name, tr, R):
        b = s.BIND.get(name)
        tr = (np.array(b[0], float) if b else np.zeros(3)) if tr is None else np.array(tr, float)
        R = (np.array(b[1], float) if b else np.eye(3)) if R is None else np.array(R, float)
        return tr, R


def hit_time(textkeys, keys=('hit',)):
    for key in keys:
        h = [t for t, v in textkeys if v.strip().lower() == key]
        if h: return h[0]
    return None


def clean(tks): return [(t, v) for t, v in tks if not DROP.match(v.strip())]


def set_meta(kf, seq=None, length=None, cycle=None, textkeys=None):
    f = kf.f; d = bytearray(f.blocks[kf.seq])
    nm, ncb, _ = struct.unpack_from('<iII', d, 0)
    if seq is not None: struct.pack_into('<i', d, 0, f.str_index(seq))
    off = 12 + 29 * ncb
    w, tk, cyc, freq, st, sp = struct.unpack_from('<fiIfff', d, off)
    if cycle is not None: cyc = cycle
    if length is not None: st, sp = 0.0, length
    struct.pack_into('<fiIfff', d, off, w, tk, cyc, freq, st, sp)
    f.blocks[kf.seq] = bytes(d)
    if textkeys is not None:
        tkn, = struct.unpack_from('<i', f.blocks[tk], 0)
        # 'start' first, 'end' last at equal times (a prn key before 'start' crashes the group parser)
        rank = lambda v: -1 if v.strip().lower() == 'start' else (1 if v.strip().lower() == 'end' else 0)
        tks = list(textkeys)
        if not any(v.strip().lower() == 'start' for _, v in tks): tks.append((0.0, 'start'))
        if not any(v.strip().lower() == 'end' for _, v in tks): tks.append((sp, 'end'))
        ent = sorted(((min(max(t, 0.0), sp), v) for t, v in tks), key=lambda e: (e[0], rank(e[1])))
        f.blocks[tk] = struct.pack('<iI', tkn, len(ent)) + b''.join(struct.pack('<fi', t, f.str_index(v)) for t, v in ent)


def add_channel(kf, name, scale_keys=None, tr=None, R=None):
    """append a controlled block for node `name` (NiTransformController): static transform (tr, R) + optional scale
    keys [(t, s)] (the FX on/off switch: scale ~0 hides a node)"""
    f = kf.f; d = f.blocks[kf.seq]
    nm, ncb, sz = struct.unpack_from('<iII', d, 0)
    proto = bytearray(d[12:12 + 29])
    data = -1
    if scale_keys:
        body = struct.pack('<I', 0) + struct.pack('<I', 0) + struct.pack('<II', len(scale_keys), 1) + \
            b''.join(struct.pack('<ff', t, v) for t, v in scale_keys)
        data = f.add_block('NiTransformData', body)
    q = m2q(np.eye(3) if R is None else R)
    t0 = np.zeros(3) if tr is None else tr
    s0 = scale_keys[0][1] if scale_keys else 1.0
    interp = f.add_block('NiTransformInterpolator', struct.pack('<3f4ffi', *t0, *q, s0, data))
    struct.pack_into('<i', proto, 0, interp); struct.pack_into('<i', proto, 4, -1)
    struct.pack_into('<i', proto, 9, f.str_index(name))
    f.blocks[kf.seq] = struct.pack('<iII', nm, ncb + 1, sz) + d[12:12 + 29 * ncb] + bytes(proto) + d[12 + 29 * ncb:]
    kf.cb.append((12 + 29 * ncb, name))
    kf.tk_block = struct.unpack_from('<i', f.blocks[kf.seq], 12 + 29 * (ncb + 1) + 4)[0]


def m2q(m):
    m = np.asarray(m, float); tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1) * 2; w = .25 * s; x = (m[2, 1] - m[1, 2]) / s; y = (m[0, 2] - m[2, 0]) / s; z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; w = (m[2, 1] - m[1, 2]) / s; x = .25 * s; y = (m[0, 1] + m[1, 0]) / s; z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; w = (m[0, 2] - m[2, 0]) / s; x = (m[0, 1] + m[1, 0]) / s; y = .25 * s; z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; w = (m[1, 0] - m[0, 1]) / s; x = (m[0, 2] + m[2, 0]) / s; y = (m[1, 2] + m[2, 1]) / s; z = .25 * s
    q = np.array([w, x, y, z]); return q / np.linalg.norm(q)


def rot_axis(a, deg):
    a = np.asarray(a, float); a = a / np.linalg.norm(a); x, y, z = a
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg)); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def resample(ctx, src, out, seq, length, cycle, textkeys, shift=0.0, stretch=1.0, fps=30, xform=None, loop_src=False):
    """channels of `src` sampled at source time t * stretch + shift (clamped, or wrapped with loop_src) over
    [0, length]; xform(name, tr, R, t, pose) may edit a channel (pose = the full filled sample at that time)"""
    k = KFEval(src); kf = KFFile(src)
    n = max(2, int(round(length * fps)) + 1)
    ts = [length * i / (n - 1) for i in range(n)]
    span = k.stop - k.start

    def st(t):
        u = t * stretch + shift
        if loop_src and span > 0: return k.start + ((u - k.start) % span)
        return min(max(u, k.start), k.stop)
    samples = [k.sample(st(t)) for t in ts]
    have = {c for _, c in kf.cb}
    for name in list(k.chan):
        if name not in have: continue
        keys = []
        for t, smp in zip(ts, samples):
            tr, R = ctx.fill(name, *smp[name])
            if xform: tr, R = xform(name, tr, R, t, smp)
            keys.append((t, tr, R))
        kf.set_channel(name, keys)
    set_meta(kf, seq, length, cycle, textkeys)
    kf.save(out)
    return out


def gun_fix(path, prn, aim=False):
    """Weapon channel dropped; prn keys -> the type's projectile node (aims: one at 1/30 s); prn None (melee on the
    robot's own Weapon node): prn keys removed, Weapon channel kept"""
    kf = KFFile(path)
    if prn and 'Weapon' in [c for _, c in kf.cb]: drop_channel(kf, 'Weapon')
    k = KF(path); tks = [(t, v) for t, v in k.textkeys if not v.strip().lower().startswith('prn:')]
    had = [t for t, v in k.textkeys if v.strip().lower().startswith('prn:')]
    if prn:
        tks += [(t, 'prn: ' + prn) for t in had]
        if aim and not had: tks.append((1 / 30, 'prn: ' + prn))
    set_meta(kf, textkeys=tks); kf.save(path)


def variant(g):
    return 'up' if re.search(r'up(_[a-z])?$', g) else ('down' if re.search(r'down(_[a-z])?$', g) else '')


def enum_to_sound(path, ENUM):
    k = KF(path)
    if not any(v.strip().lower().startswith('enum:') for t, v in k.textkeys): return
    tks = []
    for t, v in k.textkeys:
        if v.strip().lower().startswith('enum:'):
            e = v.split(':', 1)[1].strip().lower()
            if e in ENUM: tks.append((t, ENUM[e]))
        else: tks.append((t, v))
    kf = KFFile(path); set_meta(kf, textkeys=tks); kf.save(path)


def guns(ctx, HREF, OUT, SRC_OF, PRN_OF, OWN_ATTACK, made, own_reload=None, ALIAS=None, keep_spin=True, level_attacks=()):
    """every gun / thrown / mine (/ one-hand melee) group of the human set, from the creature's own type motion
    (build_securitron); ALIAS: own file name -> the robot's file that stands for it (e.g. 2hl_equip -> mesm_equip)"""
    ALIAS = ALIAS or {}
    for f in sorted(os.listdir(HREF)):
        m = re.match(r'^(1hp|2ha|2hr|2hh|2hl|1gt|1md|1lm|1hm)(.*)\.kf$', f)
        if not m or m.group(1) not in SRC_OF or re.search(r'handgrip|jump|turn', f): continue
        P, g = m.group(1), m.group(2); Sp = SRC_OF[P]
        out = os.path.join(OUT, f); ref = KF(os.path.join(HREF, f)); tks = clean(ref.textkeys)
        own = ctx.find(ALIAS.get(Sp + g + '.kf', Sp + g + '.kf'))
        is_attack = g.startswith('attack') or g.startswith('placemine') or g.startswith('power')
        # level_attacks: types whose attack up / down variants are the level attack (Mister Handy / Gutsy flamer:
        # its spin up / down files point the arm straight up / down with the arm ring turned another way - blended
        # by the look pitch they bent the robot over and flamed the ground)
        if is_attack and P in level_attacks and variant(g): own = None
        # an own attack
        # file is no longer copied as it is (the Gutsy's AttackRight fires at 0.9 s of 1.33): every attack takes the
        # human group's length / cycle / Hit time, its own motion shifted so its Hit lands there; only an own
        # AttackSpin (minigun-type spin-up, human Fire at 0.97 s) is kept
        # an own AttackSpin is kept only where it works as the player's spin-up (sentry bot, keep_spin); the Handy /
        # Gutsy flamer's (clamped, lower-case fire / loop keys) left the arms stuck in its pose after holstering
        if own and not g.startswith('reload') and not g.startswith('jam') and (not is_attack or (keep_spin and g.startswith('attackspin'))):
            shutil.copyfile(own, out)
            kf = KFFile(out); set_meta(kf, seq=ref.name, textkeys=clean(KF(own).textkeys) + [(t, v) for t, v in KF(own).textkeys if v.strip().lower().startswith('prn:')]); kf.save(out)
        elif is_attack:
            v = '' if P in level_attacks else variant(g); a = OWN_ATTACK[Sp]
            src = own or ctx.find(Sp + a + v + '.kf') or ctx.find(Sp + a + '.kf')
            sh = hit_time(KF(src).textkeys, ('hit', 'fire')); rh = hit_time(tks, ('hit', 'release'))   # a spin's Fire
            shift = (sh - rh) if (sh is not None and rh is not None) else 0.0
            # (a load-order kNVSE folder - Titans of the New West's TNW_MinigunFire_*, condition
            #no form - replaced the player's 2HH AttackSpin with the human minigun spin and turned
            # the whole robot over; the robot flamers now use AttackLoop like the vanilla Incinerator / Gatling Laser)
            # a hit-less attack loop (human 2HH AttackLoop: 0.2 s, no Hit) of a level-attack type is the source's own
            # firing loop - its spin from the 'loop' key on - not the arm still coming up at the spin's start
            if rh is None and P in level_attacks and g.startswith('attackloop'):
                sl = hit_time(KF(src).textkeys, ('loop',))
                if sl is not None: shift = sl
            resample(ctx, src, out, ref.name, ref.stop, ref.cycle, tks, shift=shift)
        elif g.startswith('reload') or g.startswith('jam'):
            src = ctx.find(Sp + 'reloada.kf') or (own_reload and ctx.find(own_reload(Sp))) or ctx.find(Sp + 'aim.kf')
            L = KF(src).stop
            resample(ctx, src, out, ref.name, ref.stop, ref.cycle, tks, stretch=L / ref.stop)
        else:
            v = variant(g)
            src = ctx.find(Sp + 'aim' + v + '.kf') or ctx.find(Sp + 'aim.kf')
            if ref.cycle == 0:
                # (Mister Handy's melee idle) a looping group (aim up / down, idle,
                # block idle) made from its aim keeps the aim's whole cycle: a human-length slice of a longer aim
                # (Handy 1HM: 3.1 / 0.33 s of 6.67) popped at every loop and drifted against the aim it blends with
                ks = KF(src); resample(ctx, src, out, ref.name, ks.stop - ks.start, ks.cycle, [(0.0, 'start')])
            else:
                resample(ctx, src, out, ref.name, ref.stop, ref.cycle, tks)
        gun_fix(out, PRN_OF[P], aim=g.startswith('aim'))
        made.append(f)


def h2h(ctx, ZREF, OUT, H2H, made, upper_only=(), lower=()):
    """H2H groups of the Zetan's list, each from a source file of the creature (H2H map: group -> own file)"""
    for f in sorted(os.listdir(ZREF)):
        if not re.match(r'^h2h.*\.kf$', f) or re.match(r'^h2h(backward|left|right)\.kf$', f): continue
        g = f[3:-3]
        src = H2H.get(g)
        if src is None:
            base = re.sub(r'(up|down)$', '', g)
            src = H2H.get(base)
        if src is None: continue
        z = KF(os.path.join(ZREF, f)); p = ctx.find(src); kk = KF(p); out = os.path.join(OUT, f)
        resample(ctx, p, out, z.name, kk.stop - kk.start, kk.cycle, clean(kk.textkeys))
        if g in upper_only:
            kf = KFFile(out)
            for c in [c for _, c in kf.cb if c in lower]: drop_channel(kf, c)
            kf.save(out)
        made.append(f)


def sneak_copies(OUT, made):
    for f in list(made):
        shutil.copyfile(os.path.join(OUT, f), os.path.join(OUT, 'sneak' + f))


def travel(ctx, src, out, seq, factor=1.0, turn=0.0, time=1.0):
    """its own locomotion cycle with the root travel scaled by `factor` and turned `turn` deg about +Z (the body keeps
    facing ahead: hover / tracked / wheeled robots glide), played `time` x faster"""
    k = KFEval(src); t0 = k.sample(k.start).get('Bip01', (None, None))[0]
    t0 = np.zeros(3) if t0 is None else np.array(t0, float)
    Rz = rot_axis([0, 0, 1.0], turn)

    def xf(name, tr, R, t, smp):
        if name == 'Bip01': return t0 + Rz @ ((tr - t0) * factor), R
        return tr, R
    L = (k.stop - k.start) / time
    return resample(ctx, src, out, seq, L, k.cycle, [(tt / time, v) for tt, v in k.textkeys], stretch=time, xform=xf)


def speed(path):
    k = KFEval(path); a = k.sample(k.start)['Bip01'][0]; b = k.sample(k.stop)['Bip01'][0]
    return np.linalg.norm(np.array(b) - np.array(a)) / (k.stop - k.start)
