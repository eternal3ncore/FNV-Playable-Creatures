"""Securitron animation set for Playable Creatures.
usage: python3 -P build_securitron.py <nvsecuritron anim dir> <human ref dir (ref_male)> <zetan ref dir> <out dir>
The securitron (Creatures\\NVSecuritron) rolls on one wheel and fires from its arms: right arm machine gun (its own
1HP), left arm gatling laser (2HR) and grenade launcher (2HL), shoulder missiles (2HH); its own H2H punches. Its weapon
is never drawn (ini HideWeapon); what matters is where a shot leaves from. The skeleton (build_skel_securitron) has a
ProjectileNode under Weapon, and every file of a weapon type re-parents Weapon onto that type's projectile node:
    1HP pistols, 2HA automatics -> machine gun arm (its 1HP motion)       prn ProjectileNode_MachineGun
    2HR rifles                  -> gatling laser arm (its 2HR motion)     prn ProjectileNode_GatlingLaser
    2HL launchers               -> grenade launcher arm (its 2HL motion)  prn ProjectileNode_Launcher
    2HH heavy weapons           -> shoulder missiles (its 2HH motion)     prn ProjectileNode_Missle
    1GT / 1MD / 1LM thrown, mines -> launcher arm (its 2HL motion)        prn ProjectileNode_Launcher
For each group the vanilla human set has for a type (ref_male; handgrip / jump / turn files excluded):
  * its own file of that group when it has one (aims, up / down, AttackLeft..., equip / unequip / holster, ReloadA),
    with prn keys pointed at the type's node and the Weapon channel dropped (Weapon then sits on the node);
  * else made from its own motion with the human file's name / length / cycle / text keys (reload / fire / throw
    sounds; prn / Enum keys dropped): attacks / throws / mine placing = its attack (Hit or Release aligned to its Hit),
    reloads / jams = its ReloadA stretched over the human length, other aims (IS...) = its aim (up / down variant);
    aims get a prn key at 0, so a game loaded with the weapon out still fires from the right arm.
H2H: its own aim / AttackLeft / Right / Power / ForwardPower / equip / unequip; the groups the Zetan set has and it
lacks are made from its own (Back / Left / Right power = its AttackPower upper body only - played while moving, up /
down = the swing, holster = its pistol one).
Locomotion: its own idle, walk, run, back, turns, hurt set; new: Left / Right / FastLeft / FastRight = walk / run with
the wheel fork turned 90 deg and the root travel turned 90 deg (the body keeps facing ahead), FastBackward = its
backward at twice the speed; jumps = its idle with the Zetan's timing. Every file also as a sneak copy (no crouch).
Text keys: 'Enum: Auxiliary1' (its CREA sound type 12) -> 'Sound: NPCSecuritronTelemetry'; other Enum keys dropped."""
import os, re, shutil, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from kf import KF, KFEval, Skeleton
from holster_fix import KFFile
from hip_spine_fix import drop_channel

SRC, HREF, ZREF, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True); os.makedirs(os.path.join(OUT, 'Locomotion', 'Hurt'), exist_ok=True)
BIND = Skeleton(os.path.join(SRC, 'skeleton.nif')).local
DROP = re.compile(r'^(prn:|enum:|m: |sound: pczetan|sound: npcdlc05alien)', re.I)
SRC_OF = {'1hp': '1hp', '2ha': '1hp', '2hr': '2hr', '2hh': '2hh', '2hl': '2hl', '1gt': '2hl', '1md': '2hl', '1lm': '2hl'}
PRN_OF = {'1hp': 'ProjectileNode_MachineGun', '2ha': 'ProjectileNode_MachineGun', '2hr': 'ProjectileNode_GatlingLaser',
          '2hh': 'ProjectileNode_Missle', '2hl': 'ProjectileNode_Launcher', '1gt': 'ProjectileNode_Launcher',
          '1md': 'ProjectileNode_Launcher', '1lm': 'ProjectileNode_Launcher'}
OWN_ATTACK = {'1hp': 'attackleft', '2hr': 'attackleft', '2hl': 'attackleft', '2hh': 'attackright'}
S = lambda n: os.path.join(SRC, n)
made = []


def fill(name, tr, R):
    b = BIND.get(name)
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
    """sequence name / stop time / cycle type / text keys of an open KFFile"""
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
        # 'start' first and 'end' last at equal times: the engine's group parser (0x5F38D0) creates the group at 'start';
        # a 'prn:' key before it is written into a null group (crash 0x5F4BBD aims with prn at 0)
        rank = lambda v: -1 if v.strip().lower() == 'start' else (1 if v.strip().lower() == 'end' else 0)
        ent = sorted(((min(max(t, 0.0), sp), v) for t, v in textkeys), key=lambda e: (e[0], rank(e[1])))
        f.blocks[tk] = struct.pack('<iI', tkn, len(ent)) + b''.join(struct.pack('<fi', t, f.str_index(v)) for t, v in ent)


def resample(src, out, seq, length, cycle, textkeys, shift=0.0, stretch=1.0, fps=30, xform=None):
    """channels of `src` sampled at source time t * stretch + shift (clamped) over [0, length]"""
    k = KFEval(src); kf = KFFile(src)
    n = max(2, int(round(length * fps)) + 1)
    ts = [length * i / (n - 1) for i in range(n)]
    samples = [k.sample(min(max(t * stretch + shift, k.start), k.stop)) for t in ts]     # once per frame
    have = {c for _, c in kf.cb}
    for name in list(k.chan):
        if name not in have: continue
        keys = []
        for t, smp in zip(ts, samples):
            tr, R = fill(name, *smp[name])
            if xform: tr, R = xform(name, tr, R)
            keys.append((t, tr, R))
        kf.set_channel(name, keys)
    set_meta(kf, seq, length, cycle, textkeys)
    kf.save(out)


def gun_fix(path, P, aim=False):
    """Weapon channel dropped; prn keys -> the type's projectile node (aims: one at 0)"""
    kf = KFFile(path)
    if 'Weapon' in [c for _, c in kf.cb]: drop_channel(kf, 'Weapon')
    k = KF(path); tks = [(t, v) for t, v in k.textkeys if not v.strip().lower().startswith('prn:')]
    had = [t for t, v in k.textkeys if v.strip().lower().startswith('prn:')]
    tks += [(t, 'prn: ' + PRN_OF[P]) for t in had]
    if aim and not had: tks.append((1 / 30, 'prn: ' + PRN_OF[P]))          # as the human aims (0.0333, after 'start')
    set_meta(kf, textkeys=tks); kf.save(path)


def variant(g):
    return 'up' if re.search(r'up(_[a-z])?$', g) else ('down' if re.search(r'down(_[a-z])?$', g) else '')


# ---------------- guns, thrown weapons, mines ----------------
for f in sorted(os.listdir(HREF)):
    m = re.match(r'^(1hp|2ha|2hr|2hh|2hl|1gt|1md|1lm)(.*)\.kf$', f)
    if not m or re.search(r'handgrip|jump|turn', f): continue
    P, g = m.group(1), m.group(2); Sp = SRC_OF[P]
    out = os.path.join(OUT, f); ref = KF(os.path.join(HREF, f)); tks = clean(ref.textkeys)
    own = S(Sp + g + '.kf')
    # its own
    # attacks (machine gun AttackLeft: a 0.17 s burst) were copied for hipfire, but the aimed (IS) variants had no own
    # file and took the human IS length (0.67 s) -> the automatic SMG fired at a quarter of the rate while aiming. An
    # aimed attack now uses its own attack of the same aim variant, renamed to the IS group.
    mi = re.match(r'^(attack.*?)is(up|down)?$', g)
    own_hip = S(Sp + mi.group(1) + (mi.group(2) or '') + '.kf') if mi else None
    if os.path.exists(own):
        shutil.copyfile(own, out)
    elif own_hip and os.path.exists(own_hip):
        shutil.copyfile(own_hip, out)
        kf = KFFile(out); set_meta(kf, seq=ref.name); kf.save(out)
    elif g.startswith('attack') or g.startswith('placemine'):
        v = variant(g); a = OWN_ATTACK[Sp]
        src = S(Sp + a + v + '.kf') if os.path.exists(S(Sp + a + v + '.kf')) else S(Sp + a + '.kf')
        sh = hit_time(KF(src).textkeys); rh = hit_time(tks, ('hit', 'release'))
        resample(src, out, ref.name, ref.stop, ref.cycle, tks, shift=(sh - rh) if (sh is not None and rh is not None) else 0.0)
    elif g.startswith('reload') or g.startswith('jam'):
        src = S(Sp + 'reloada.kf'); L = KF(src).stop
        resample(src, out, ref.name, ref.stop, ref.cycle, tks, stretch=L / ref.stop)
    else:                                                          # aims (IS, ...), anything else: its aim pose
        v = variant(g)
        src = S(Sp + 'aim' + v + '.kf') if os.path.exists(S(Sp + 'aim' + v + '.kf')) else S(Sp + 'aim.kf')
        resample(src, out, ref.name, ref.stop, ref.cycle, tks)
    gun_fix(out, P, aim=g.startswith('aim'))
    made.append(f)

# ---------------- H2H ----------------
own_h2h = {f for f in os.listdir(SRC) if f.startswith('h2h') and f.endswith('.kf') and 'death' not in f}
for f in sorted(own_h2h): shutil.copyfile(S(f), os.path.join(OUT, f)); made.append(f)
for f in sorted(os.listdir(ZREF)):
    if not re.match(r'^h2h.*\.kf$', f) or f in own_h2h or re.match(r'^h2h(backward|left|right)\.kf$', f): continue
    z = KF(os.path.join(ZREF, f)); g = f[3:-3]; out = os.path.join(OUT, f)
    if g.startswith('attack') and g.endswith('power'):             # Back / Left / Right power = its standing power
        src = S('h2hattackpower.kf'); kk = KF(src)
        resample(src, out, z.name, kk.stop, kk.cycle, kk.textkeys)
    elif g.startswith('attack'):                                  # up / down variants = the same swing
        base = re.sub(r'(up|down)$', '', g); src = S('h2h' + base + '.kf'); kk = KF(src)
        resample(src, out, z.name, kk.stop, kk.cycle, kk.textkeys)
    elif g.startswith('aim'):
        src = S('h2haim.kf'); kk = KF(src); resample(src, out, z.name, kk.stop, kk.cycle, kk.textkeys)
    elif g == 'holster':                                          # its own (pistol) holster, Weapon stays in the hand
        shutil.copyfile(S('1hpholster.kf'), out)
    else: continue
    made.append(f)

# Back / Left / Right power are played while moving (a side power attack while strafing): they key only the upper
# body, so the wheel / fork / root come from the movement and it doesn't slide (power_legs)
LOWER = ('Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis', 'Bip01 WheelFork', 'Bip01 Wheel', 'Bip01 WheeDeform01',
         'Bip01 WheeDeform02', 'Bip01 WheeDeform03', 'Bip01 WheeDeform04')
for f in ('h2hattackbackpower.kf', 'h2hattackleftpower.kf', 'h2hattackrightpower.kf'):
    p = os.path.join(OUT, f); kf = KFFile(p)
    for c in [c for _, c in kf.cb if c in LOWER]: drop_channel(kf, c)
    kf.save(p)

# ---------------- locomotion ----------------
for f in ('mtidle.kf', 'mtturnleft.kf', 'mtturnright.kf', 'talking.kf'):
    shutil.copyfile(S(f), os.path.join(OUT, f)); made.append(f)
for f in ('mtforward.kf', 'mtfastforward.kf', 'mtbackward.kf'):
    shutil.copyfile(S(os.path.join('locomotion', f)), os.path.join(OUT, f)); made.append(f)
for f in os.listdir(S(os.path.join('locomotion', 'hurt'))):
    shutil.copyfile(S(os.path.join('locomotion', 'hurt', f)), os.path.join(OUT, 'Locomotion', 'Hurt', f))
# wheel fork turned about the vertical (in its parent's frame, from the idle's pose) for the strafes
sk = Skeleton(os.path.join(SRC, 'skeleton.nif'))
idle = KFEval(S('mtidle.kf')).sample(0)
W = sk.fk({n: fill(n, *v) for n, v in idle.items() if n in sk.local})
fork_parent = sk.parent['Bip01 WheelFork']
up_in_parent = W[fork_parent][1].T @ np.array([0, 0, 1.0])


def rot_axis(a, deg):
    a = a / np.linalg.norm(a); x, y, z = a; c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg)); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def strafe(sign):
    Rf = rot_axis(up_in_parent, 90 * sign); Rz = rot_axis(np.array([0, 0, 1.0]), 90 * sign)
    def xf(name, tr, R):
        if name == 'Bip01': return Rz @ tr, R
        if name == 'Bip01 WheelFork': return tr, Rf @ R
        return tr, R
    return xf


for out, src, seq, sign in (('mtleft.kf', 'mtforward.kf', 'Left', 1), ('mtright.kf', 'mtforward.kf', 'Right', -1),
                            ('mtfastleft.kf', 'mtfastforward.kf', 'FastLeft', 1), ('mtfastright.kf', 'mtfastforward.kf', 'FastRight', -1)):
    p = S(os.path.join('locomotion', src)); kk = KF(p)
    resample(p, os.path.join(OUT, out), seq, kk.stop, kk.cycle, kk.textkeys, xform=strafe(sign)); made.append(out)
p = S(os.path.join('locomotion', 'mtbackward.kf')); kk = KF(p)
resample(p, os.path.join(OUT, 'mtfastbackward.kf'), 'FastBackward', kk.stop / 2, kk.cycle,
         [(t / 2, v) for t, v in kk.textkeys], stretch=2.0); made.append('mtfastbackward.kf')
for f in sorted(os.listdir(ZREF)):
    if re.match(r'^mtjump.*\.kf$', f):
        z = KF(os.path.join(ZREF, f))
        resample(S('mtidle.kf'), os.path.join(OUT, f), z.name, z.stop, z.cycle, clean(z.textkeys)); made.append(f)

# ---------------- text keys: CREA sound enums ----------------
ENUM = {'auxiliary1': 'Sound: NPCSecuritronTelemetry'}
for f in made + [os.path.join('Locomotion', 'Hurt', x) for x in os.listdir(os.path.join(OUT, 'Locomotion', 'Hurt'))]:
    p = os.path.join(OUT, f); k = KF(p)
    if not any(v.strip().lower().startswith('enum:') for t, v in k.textkeys): continue
    tks = []
    for t, v in k.textkeys:
        if v.strip().lower().startswith('enum:'):
            e = v.split(':', 1)[1].strip().lower()
            if e in ENUM: tks.append((t, ENUM[e]))
        else: tks.append((t, v))
    kf = KFFile(p); set_meta(kf, textkeys=tks); kf.save(p)

# ---------------- sneak copies ----------------
for f in list(made):
    shutil.copyfile(os.path.join(OUT, f), os.path.join(OUT, 'sneak' + f))
print(len(made), 'groups +', len(made), 'sneak copies (+ hurt locomotion) ->', OUT)
import robot_melee; robot_melee.run(OUT)          # 1HM / 2HM = its H2H moves (weapon_hide.py --race hides the weapon)
