"""Robot animation sets for Playable Creatures: Protectron, Robobrain, Mister Handy / Gutsy, Sentry Bot.
usage: python3 -P build_robot.py <robot> <creature anim dir> <built Skeleton.nif> <human ref dir (ref_male)> <zetan ref dir> <out dir>
Built like the Securitron set (build_securitron.py; helpers in robotlib.py):
  * guns / thrown / mines: every group of the human set for the types in SRC_OF, from the robot's own motion of the
    mapped type (own file of that group when it has one; else attacks = its attack with Hit / Release aligned,
    reloads / jams = its reload (or aim) over the human length with the human sounds, other aims = its aim); the
    Weapon channel dropped and prn keys pointed at the type's projectile node (aims: one at 1/30 s), so the shot
    leaves that emitter;
  * H2H: the Zetan's group list, each from the robot's own file named in H2H;
  * lower body (root, pelvis, legs) of every weapon / H2H file at priority <= 26 (as the robots' own aims), so the
    locomotion (30) keeps the legs while moving - and a hovering protectron doesn't drop to the ground mid-attack;
  * locomotion per robot (LOCO); jumps from its idle with the Zetan's timing; every file also as a sneak copy;
  * 'Enum:' text keys (CREA sound types, silent on an NPC) -> 'Sound: <its SOUN>'.
Protectron:
  * Forward = its own walk (25 units/s, a 4.6 s stride) played 3.4x faster (~85 units/s, the human walk), Backward
    1.85x (~70), hurt walk 2x;
  * FastForward / FastBackward / FastLeft / FastRight and Left / Right (its own side steps barely move: 2 units/s) =
    hover: its idle lifted 14 units with a slow bob, the body leaning into the travel (forward 15 deg, sideways 12,
    back 10), thighs swung back 5 deg (20 with the lean), knees bent 50 deg, feet pointed 15 deg - knees folded back under the jet;
    speeds 340 / 260 / 300 forward / back / side, 95 for the walking strafes; jumps = the hover pose;
  * the back jet (skeleton node PCJet, Mister Handy's flame) is switched by scale keys: 1 in the hover files, 0.001 in
    the idle / walk / turns / hurt (a node no running sequence keys keeps its last value)."""
import os, re, shutil, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.append(HERE); sys.path.append(os.path.dirname(HERE))
from kf import KF, KFEval, Skeleton
from holster_fix import KFFile
from hip_spine_fix import drop_channel
import robotlib as RL

ROBOT, SRCDIR, SKEL, HREF, ZREF, OUT = sys.argv[1:7]
os.makedirs(OUT, exist_ok=True); os.makedirs(os.path.join(OUT, 'Locomotion', 'Hurt'), exist_ok=True)
made = []


def set_priority(path, names, prio, exact=False):
    """channels in `names` (None = all) to at most `prio` (exact: to `prio`)"""
    kf = KFFile(path); d = bytearray(kf.f.blocks[kf.seq])
    for o, n in kf.cb:
        if names is not None and n not in names: continue
        if exact or d[o + 8] > prio: d[o + 8] = prio
    kf.f.blocks[kf.seq] = bytes(d); kf.save(path)


def jet_keys(path, on):
    """PCJet scale switch (constant over the file)"""
    kf = KFFile(path)
    if 'PCJet' in [c for _, c in kf.cb]: drop_channel(kf, 'PCJet')
    L = KF(path).stop
    b = ctx_jet_bind
    RL.add_channel(kf, 'PCJet', [(0.0, 1.0 if on else 0.001), (L, 1.0 if on else 0.001)], tr=b[0], R=b[1])
    kf.save(path)


def speed(path):
    k = KFEval(path); a = k.sample(k.start)['Bip01'][0]; b = k.sample(k.stop)['Bip01'][0]
    return np.linalg.norm(np.array(b) - np.array(a)) / (k.stop - k.start)


def timescale(ctx, src, out, seq, factor):
    """its own cycle played `factor` x faster (same stride, cadence and root speed x factor)"""
    k = KF(src); L = (k.stop - k.start) / factor
    RL.resample(ctx, src, out, seq, L, k.cycle, [(t / factor, v) for t, v in k.textkeys], stretch=factor)


# ------------------------------------------------------------------ protectron
def protectron_loco(ctx):
    S = ctx.find
    idle = S('mtidle.kf'); IL = KF(idle).stop
    for f in ('mtidle.kf', 'mtturnleft.kf', 'mtturnright.kf', 'talking.kf'):
        shutil.copyfile(S(f), os.path.join(OUT, f)); made.append(f)
    walk = S('mtforward.kf'); timescale(ctx, walk, os.path.join(OUT, 'mtforward.kf'), 'Forward', 85.0 / speed(walk)); made.append('mtforward.kf')
    back = S('mtbackward.kf'); timescale(ctx, back, os.path.join(OUT, 'mtbackward.kf'), 'Backward', 70.0 / speed(back)); made.append('mtbackward.kf')
    hurt = S(os.path.join('hurt', 'mtforward_hurt.kf'))
    timescale(ctx, hurt, os.path.join(OUT, 'Locomotion', 'Hurt', 'mtforward_hurt.kf'), KF(hurt).name, 2.0)
    sk = ctx.sk
    LEGS = {'Bip01 L Thigh': -5, 'Bip01 R Thigh': -5, 'Bip01 L Calf': -50, 'Bip01 R Calf': -50, 'Bip01 L Foot': -15, 'Bip01 R Foot': -15}
    X, Y = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])

    def hover(direction, v, lean_axis, lean_deg, L):
        cache = {}

        def xf(name, tr, R, t, smp):
            if t not in cache:
                pose = {n: ctx.fill(n, *vv) for n, vv in smp.items() if n in sk.local}
                cache[t] = sk.fk(pose)
            W = cache[t]
            if name == 'Bip01':
                bob = 2.0 * np.sin(2 * np.pi * 3 * t / L)
                return tr + np.asarray(direction, float) * v * t + np.array([0, 0, 14.0 + bob]), R
            if name == 'Bip01 NonAccum':
                Rp = W[sk.parent[name]][1]
                Rw = RL.rot_axis(X, -15 if lean_axis is None else 0)
                if lean_axis is not None: Rw = RL.rot_axis(lean_axis, lean_deg) @ RL.rot_axis(X, -6)
                return tr, (Rp.T @ Rw @ Rp) @ R
            if name in LEGS:
                Rp = W[sk.parent[name]][1]
                sway = 4.0 * np.sin(2 * np.pi * 3 * t / L + (0 if ' L ' in name else np.pi)) if 'Thigh' in name else 0.0
                Rw = RL.rot_axis(X, LEGS[name] + sway)
                return tr, (Rp.T @ Rw @ Rp) @ R
            return tr, R
        return xf

    for out, seq, d, v, ax, deg in (('mtfastforward.kf', 'FastForward', Y, 340, None, 0),
                                    ('mtfastbackward.kf', 'FastBackward', -Y, 260, X, 14),
                                    ('mtfastleft.kf', 'FastLeft', -X, 300, Y, -12), ('mtfastright.kf', 'FastRight', X, 300, Y, 12),
                                    ('mtleft.kf', 'Left', -X, 95, Y, -8), ('mtright.kf', 'Right', X, 95, Y, 8)):
        RL.resample(ctx, idle, os.path.join(OUT, out), seq, IL, 0, [(0.0, 'start'), (IL, 'end')], xform=hover(d, v, ax, deg, IL), loop_src=True)
        made.append(out); HOVER.add(out)
    for f in sorted(os.listdir(ZREF)):
        if re.match(r'^mtjump.*\.kf$', f):
            z = KF(os.path.join(ZREF, f))
            RL.resample(ctx, idle, os.path.join(OUT, f), z.name, z.stop, z.cycle, RL.clean(z.textkeys), xform=hover(Y, 0, None, 0, IL), loop_src=True)
            made.append(f); HOVER.add(f)
    for f in made:
        if f.startswith('mt'): jet_keys(os.path.join(OUT, f), f in HOVER)
        if f in HOVER: set_priority(os.path.join(OUT, f), None, 30, exact=True)   # locomotion priority (the idle's is 20)
    jet_keys(os.path.join(OUT, 'Locomotion', 'Hurt', 'mtforward_hurt.kf'), False)


# ------------------------------------------------------------------ gliding robots (tracks, wheels, jets)
def glide_loco(ctx, L):
    """L: dict(copy=[own files copied as they are], make={out: (src, seq, factor, turn, time)}, hurt=factor or None)
    - own cycles with the root travel scaled / turned (strafes = forward travel turned 90 deg, the body facing
    ahead: no feet to slide); jumps = its idle with the Zetan's timing"""
    S = ctx.find
    for f in L['copy']:
        shutil.copyfile(S(f), os.path.join(OUT, f)); made.append(f)
    for out, (src, seq, factor, turn, time) in L['make'].items():
        RL.travel(ctx, S(src), os.path.join(OUT, out), seq, factor, turn, time); made.append(out)
        print('   %-18s %-14s %6.1f units/s (skeleton units)' % (out, seq, RL.speed(os.path.join(OUT, out))))
    hd = S('hurt')
    if L.get('hurt') and hd and os.path.isdir(hd):
        for f in sorted(os.listdir(hd)):
            RL.travel(ctx, os.path.join(hd, f), os.path.join(OUT, 'Locomotion', 'Hurt', f), KF(os.path.join(hd, f)).name, L['hurt'])
    idle = S('mtidle.kf')
    for f in sorted(os.listdir(ZREF)):
        if re.match(r'^mtjump.*\.kf$', f):
            z = KF(os.path.join(ZREF, f))
            RL.resample(ctx, idle, os.path.join(OUT, f), z.name, z.stop, z.cycle, RL.clean(z.textkeys), loop_src=True); made.append(f)
            set_priority(os.path.join(OUT, f), None, 30, exact=True)


def claw_retarget(ctx, files):
    """Mister Gutsy's melee with its claw. Its three arms hang on the hub Bip01 Spine 01 as copies turned ~120 deg
    about the hub's X axis (claw = R Thigh Front chain, gun arm = R Thigh chain, flamer = L Thigh chain); the Handy's
    swings move the gun (buzzsaw) arm. Here the hub turns by M (claw socket -> gun socket) and the claw takes the gun
    arm's motion (root: M^T @ its transform, below it the same local rotations - cloned chains); the gun arm keeps its
    idle pose (carried round to the next socket), so the claw strikes where the buzzsaw would."""
    F = ['Bip01 R Thigh Front', 'Bip01 R Thigh Front01', 'Bip01 R Calf front', 'Bip01 R Calf front01', 'Bip01 R FootFront',
         'Bip01 R FootFront 01', 'Bip01 R Toe 1 Front']
    R = ['Bip01 R Thigh', 'Bip01 R Thigh01', 'Bip01 R Calf', 'Bip01 R Calf 01', 'Bip01 R Foot', 'Bip01 R Foot 01', 'Bip01 R Toe']
    HUB = 'Bip01 Spine 01'
    B = ctx.BIND
    M = B[R[0]][1] @ B[F[0]][1].T
    U, _, Vt = np.linalg.svd(M); M = U @ Vt                          # nearest rotation
    ang = np.degrees(np.arctan2(M[2, 1], M[1, 1]))
    rest = {n: ctx.fill(n, *v) for n, v in KFEval(ctx.find('mtidle.kf')).sample(0.0).items() if n in R + ['Bip01 R Toe 02', 'Bip01 R Toe 01']}
    for f in files:
        p = os.path.join(OUT, f); k = KF(p)

        def xf(name, tr, R_, t, smp):
            if name == HUB: return tr, R_ @ M
            if name in F:
                i = F.index(name); st, sr = ctx.fill(R[i], *smp[R[i]])
                if i == 0: return M.T @ st, M.T @ sr
                return tr, sr
            if name in rest: return rest[name]
            return tr, R_
        RL.resample(ctx, p, p, k.name, k.stop - k.start, k.cycle, k.textkeys, xform=xf)
    print('  claw retarget: %d files, hub turned %.1f deg about its X' % (len(files), ang))


HOVER = set()
RB = 1 / 0.33          # robobrain: race height 0.33 (CREA base scale), so its skeleton units are 3x the world's
CFG = {
    'protectron': dict(
        dirs=['', 'specialanims', 'locomotion'],
        SRC_OF={'1hp': '1hp', '2ha': '1hp', '2hr': '1hp', '2hh': '1hp', '2hl': '2hl', '1gt': '1hp', '1md': '1hp', '1lm': '1hp'},
        PRN_OF={'1hp': 'ProjectileNode_RHandLaser', '2ha': 'ProjectileNode_RHandLaser', '2hr': 'ProjectileNode_RHandLaser',
                '2hh': 'ProjectileNode_RHandLaser', '2hl': 'ProjectileNode_HeadLaser', '1gt': 'ProjectileNode_RHandLaser',
                '1md': 'ProjectileNode_RHandLaser', '1lm': 'ProjectileNode_RHandLaser'},
        OWN_ATTACK={'1hp': 'attackright', '2hl': 'attackright'},
        H2H={'aim': 'h2haim.kf', 'aimup': 'h2haimup.kf', 'aimdown': 'h2haimdown.kf',
             'attackleft': 'h2hattackleft_chop.kf', 'attackright': 'h2hattackright_chop.kf',
             'attackpower': 'h2hattackright_slash.kf', 'attackforwardpower': 'h2hattackleft_slash.kf',
             'attackbackpower': 'h2hattackright_slash.kf', 'attackleftpower': 'h2hattackleft_slash.kf',
             'attackrightpower': 'h2hattackright_slash.kf',
             'equip': 'h2hequip.kf', 'unequip': 'h2hunequip.kf', 'holster': '1hpholster.kf'},
        LOWER=('Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis', 'Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot', 'Bip01 L Toe0',
               'Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot', 'Bip01 R Toe0'),
        ENUM={'left': 'Sound: NPCRobotProtectronFootLeft', 'right': 'Sound: NPCRobotProtectronFootRight'},
        loco=protectron_loco, jet=True),
    # Robobrain: laser right arm (1HP -> every gun / thrown type, ProjectileNode_Right); the mesmetron beam from the
    # head for launchers (its 2HL: 2hl_aim / 2hl_attackright, a two-arm cast; mesm_equip / unequip); H2H = its two arm
    # swings. Tracks: speeds set for the 0.33 race scale (in-game walk 90, run 280, back 80 / 200, strafes 90 / 250).
    'robobrain': dict(
        dirs=['', 'locomotion'],
        SRC_OF={'1hp': '1hp', '2ha': '1hp', '2hr': '1hp', '2hh': '1hp', '2hl': '2hl_', '1gt': '1hp', '1md': '1hp', '1lm': '1hp'},
        PRN_OF={'1hp': 'ProjectileNode_Right', '2ha': 'ProjectileNode_Right', '2hr': 'ProjectileNode_Right',
                '2hh': 'ProjectileNode_Right', '2hl': 'ProjectileNode_HeadLaser', '1gt': 'ProjectileNode_Right',
                '1md': 'ProjectileNode_Right', '1lm': 'ProjectileNode_Right'},
        OWN_ATTACK={'1hp': 'attackright', '2hl_': 'attackright'},
        ALIAS={'2hl_equip.kf': 'mesm_equip.kf', '2hl_unequip.kf': 'mesm_unequip.kf', '2hl_holster.kf': '1hpholster.kf'},
        # H2H = its 1HP
        # laser: aim = 1hpaim, every attack = 1hpattackright (0.6 s, Hit at 0.2)
        H2H={'aim': '1hpaim.kf', 'attackleft': '1hpattackright.kf', 'attackright': '1hpattackright.kf',
             'attackpower': '1hpattackright.kf', 'attackforwardpower': '1hpattackright.kf', 'attackbackpower': '1hpattackright.kf',
             'attackleftpower': '1hpattackright.kf', 'attackrightpower': '1hpattackright.kf',
             'equip': '1hpequip.kf', 'unequip': '1hpunequip.kf', 'holster': '1hpholster.kf'},
        LOWER=('Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis', 'Bip01 L Thigh', 'Bip01 L Foot', 'Bip01 R Thigh', 'Bip01 R Foot'),
        ENUM={'auxiliary1': 'Sound: NPCRobotRobobrainArmMvmt'},
        loco=lambda ctx: glide_loco(ctx, dict(
            copy=['mtidle.kf', 'mtturnleft.kf', 'mtturnright.kf', 'talking.kf'],
            make={'mtforward.kf': ('mtforward.kf', 'Forward', 90 * RB / 103.7, 0, 1),
                  'mtfastforward.kf': ('mtfastforward.kf', 'FastForward', 280 * RB / 207.4, 0, 1),
                  'mtbackward.kf': ('mtbackward.kf', 'Backward', 80 * RB / 107.3, 0, 1),
                  'mtfastbackward.kf': ('mtbackward.kf', 'FastBackward', 200 * RB / 107.3, 0, 1),
                  'mtleft.kf': ('mtforward.kf', 'Left', 90 * RB / 103.7, 90, 1), 'mtright.kf': ('mtforward.kf', 'Right', 90 * RB / 103.7, -90, 1),
                  'mtfastleft.kf': ('mtfastforward.kf', 'FastLeft', 250 * RB / 207.4, 90, 1),
                  'mtfastright.kf': ('mtfastforward.kf', 'FastRight', 250 * RB / 207.4, -90, 1)},
            hurt=2.0))),
    # Mister Handy / Mister Gutsy: right arm (plasma gun / buzzsaw: its 1HP, ProjectileNode_HeadLaser01) for pistols,
    # rifles, automatics, thrown and mines; left arm flamer (its 2HL spin, ProjectileNode_HeadLaser) for launchers and
    # heavy weapons (the player's flamer is 2HH); one-hand melee = its own claw / saw set (1HM, Weapon on its Dummy01);
    # H2H = the same claw swings. Hovers: its own cycles, travel sped up (walk 87, run 300, back 80 / 250, strafes 85 / 300).
    'misterhandy': dict(
        dirs=['', 'specialanims'],
        SRC_OF={'1hp': '1hp', '2ha': '1hp', '2hr': '1hp', '2hh': '2hl', '2hl': '2hl', '1gt': '1hp', '1md': '1hp', '1lm': '1hp', '1hm': '1hm'},
        PRN_OF={'1hp': 'ProjectileNode_HeadLaser01', '2ha': 'ProjectileNode_HeadLaser01', '2hr': 'ProjectileNode_HeadLaser01',
                '2hh': 'ProjectileNode_HeadLaser', '2hl': 'ProjectileNode_HeadLaser', '1gt': 'ProjectileNode_HeadLaser01',
                '1md': 'ProjectileNode_HeadLaser01', '1lm': 'ProjectileNode_HeadLaser01', '1hm': None},
        OWN_ATTACK={'1hp': 'attackright', '2hl': 'attackspin', '1hm': 'attackright_chop'},
        level_attacks=('2hh', '2hl'),                                    # flamer: no straight up / down spins
        pin=('Bip01 Pelvis', 'Bip01 Spine', 'Bip01 Neck1'),               # keyed in every file
        ALIAS={'1hmattackleft_a.kf': '1hmattackleft_chop.kf', '1hmattackleft_b.kf': '1hmattackleft_chop.kf',
               '1hmattackright_a.kf': '1hmattackright_chop.kf', '1hmattackright_b.kf': '1hmattackright_stab.kf',
               '1hmattackpower.kf': '1hmattackright_stab.kf', '1hmattackforwardpower.kf': '1hmattackright_uppercut.kf'},
        H2H={'aim': '1hmaim.kf', 'attackleft': '1hmattackleft_chop.kf', 'attackright': '1hmattackright_chop.kf',
             'attackpower': '1hmattackright_stab.kf', 'attackforwardpower': '1hmattackright_uppercut.kf',
             'attackbackpower': '1hmattackright_stab.kf', 'attackleftpower': '1hmattackleft_chop.kf',
             'attackrightpower': '1hmattackright_chop.kf', 'equip': '1hmequip.kf', 'unequip': '1hmunequip.kf', 'holster': '1hmholster.kf'},
        LOWER=('Bip01', 'Bip01 NonAccum', 'Bip01 Pelvis'),
        ENUM={},
        loco=lambda ctx: glide_loco(ctx, dict(
            copy=['mtidle.kf', 'mtturnleft.kf', 'mtturnright.kf', 'mtfastforward.kf'],
            make={'mtforward.kf': ('mtforward.kf', 'Forward', 87 / 78.9, 0, 1),
                  'mtbackward.kf': ('mtbackward.kf', 'Backward', 80 / 50.0, 0, 1),
                  'mtfastbackward.kf': ('mtbackward.kf', 'FastBackward', 250 / 50.0, 0, 1),
                  'mtleft.kf': ('mtleft.kf', 'Left', 85 / 21.4, 0, 1), 'mtright.kf': ('mtright.kf', 'Right', 85 / 21.4, 0, 1),
                  'mtfastleft.kf': ('mtleft.kf', 'FastLeft', 300 / 21.4, 0, 1), 'mtfastright.kf': ('mtright.kf', 'FastRight', 300 / 21.4, 0, 1)},
            hurt=None))),
    # Sentry Bot: gatling arm (ProjectileNode_RGatling) for every gun - its 2HH gatling-laser loop for heavy weapons,
    # its 2HR minigun spin for rifles / automatics / pistols; missile pod (PCMissileEmitter on the pod) for launchers,
    # thrown and mines (its 2HL); H2H = its missile-arm swing (2HL AttackLeft). Wheels: its own cycles (walk 96, run
    # 384, back 96 / 384), strafes = forward / run travel turned 90 deg (96 / 300).
    'sentrybot': dict(
        dirs=['', 'locomotion'],
        SRC_OF={'1hp': '2hr', '2ha': '2hr', '2hr': '2hr', '2hh': '2hh', '2hl': '2hl', '1gt': '2hl', '1md': '2hl', '1lm': '2hl'},
        PRN_OF={'1hp': 'ProjectileNode_RGatling', '2ha': 'ProjectileNode_RGatling', '2hr': 'ProjectileNode_RGatling',
                '2hh': 'ProjectileNode_RGatling', '2hl': 'PCMissileEmitter', '1gt': 'PCMissileEmitter',
                '1md': 'PCMissileEmitter', '1lm': 'PCMissileEmitter'},
        OWN_ATTACK={'2hr': 'attackspin', '2hh': 'attackloop', '2hl': 'attackleft'}, keep_spin=True,
        ALIAS={'2hrjama.kf': '2hhjama.kf'},
        H2H={'aim': '2hlaim.kf', 'attackleft': '2hlattackleft.kf', 'attackright': '2hlattackleft.kf',
             'attackpower': '2hlattackleft.kf', 'attackforwardpower': '2hlattackleft.kf', 'attackbackpower': '2hlattackleft.kf',
             'attackleftpower': '2hlattackleft.kf', 'attackrightpower': '2hlattackleft.kf',
             'equip': '2hlequip.kf', 'unequip': '2hlunequip.kf', 'holster': '2hlholster.kf'},
        LOWER=('Bip01', 'Bip01 NonAccum'),
        ENUM={},
        loco=lambda ctx: glide_loco(ctx, dict(
            copy=['mtidle.kf', 'mtturnleft.kf', 'mtturnright.kf', 'mtforward.kf', 'mtfastforward.kf', 'mtbackward.kf', 'mtfastbackward.kf'],
            make={'mtleft.kf': ('mtforward.kf', 'Left', 1.0, 90, 1), 'mtright.kf': ('mtforward.kf', 'Right', 1.0, -90, 1),
                  'mtfastleft.kf': ('mtfastforward.kf', 'FastLeft', 0.8, 90, 1), 'mtfastright.kf': ('mtfastforward.kf', 'FastRight', 0.8, -90, 1)},
            hurt=1.0))),
}
# Mister Gutsy = Mister Handy's set, but its H2H / one-hand melee files move the front claw (R Thigh Front
# chain, a clone of the buzzsaw arm's R Thigh chain: same bone lengths) with the buzzsaw arm's swing, while the plasma
# arm holds its idle pose.
CFG['mistergutsy'] = dict(CFG['misterhandy'], claw=True)
# Mister Gutsy: heavy weapons (2HH) on its flamer arm, every other gun / launcher / thrown / mine on its plasma arm. The
# player's weapon model is never drawn (HideWeapon), so every shot leaves the skeleton's ProjectileNode (on the flamer
# tip, for the Flame projectile): the plasma-arm files key ProjectileNode onto the plasma emitter
# (ProjectileNode_HeadLaser01) frame by frame, the 2HH files key it back at its bind on the flamer tip (projnode).
CFG['mistergutsy'] = dict(CFG['mistergutsy'],
                          SRC_OF=dict(CFG['mistergutsy']['SRC_OF'], **{'2hl': '1hp'}),
                          PRN_OF=dict(CFG['mistergutsy']['PRN_OF'], **{'2hl': 'ProjectileNode_HeadLaser01'}),
                          level_attacks=('2hh',),
                          projnode=('ProjectileNode_HeadLaser01', ('1hp', '2ha', '2hr', '2hl', '1gt', '1md', '1lm'), ('2hh',)))
# Mister Handy has no gun arm (right arm = buzzsaw): every gun, thrown weapon and mine is fired / thrown with its flamer
# arm (its 2HL spin motion, aims / attacks level), from the flamer tip. The player's weapon model is never drawn
# (HideWeapon), so the shot leaves the skeleton's ProjectileNode - on the flamer tip since skeleton v3 - while the
# buzzsaw arm did the aiming (shots ~45 deg off to the side).
_R = ('1hp', '2ha', '2hr', '1gt', '1md', '1lm')
CFG['misterhandy'] = dict(CFG['misterhandy'],
                          SRC_OF=dict(CFG['misterhandy']['SRC_OF'], **{t: '2hl' for t in _R}),
                          PRN_OF=dict(CFG['misterhandy']['PRN_OF'], **{t: 'ProjectileNode_HeadLaser' for t in _R}),
                          level_attacks=('2hh', '2hl') + _R, weapon_follow=True)
CFG['mistergutsy'] = dict(CFG['mistergutsy'], weapon_follow=True)
C = CFG[ROBOT]
ctx = RL.Ctx([os.path.join(SRCDIR, d) for d in C['dirs']] + [os.path.join(SRCDIR, 'locomotion')], SKEL)
if C.get('jet'):
    j = Skeleton(SKEL).local['PCJet']; ctx_jet_bind = (j[0], j[1])

RL.guns(ctx, HREF, OUT, C['SRC_OF'], C['PRN_OF'], C['OWN_ATTACK'], made, ALIAS=C.get('ALIAS'),
        keep_spin=C.get('keep_spin', False), level_attacks=C.get('level_attacks', ()))
RL.h2h(ctx, ZREF, OUT, C['H2H'], made)
for f in list(made):
    set_priority(os.path.join(OUT, f), set(C['LOWER']), 26)
if C.get('claw'): claw_retarget(ctx, [f for f in made if f.startswith('1hm') or f.startswith('h2h')])
C['loco'](ctx)
# every locomotion group slower than the human male's (vanilla characters\_male\locomotion\male, world
# units/s, measured) gets its root travel scaled up to it; skeleton units = world / race height (robobrain 0.33)
HUMAN = {'mtforward.kf': 85.3, 'mtfastforward.kf': 353.9, 'mtbackward.kf': 67.4, 'mtfastbackward.kf': 282.5,
         'mtleft.kf': 86.5, 'mtright.kf': 85.7, 'mtfastleft.kf': 353.7, 'mtfastright.kf': 353.7}
HEIGHT = {'robobrain': 0.33}.get(ROBOT, 1.0)
for f, hv in HUMAN.items():
    p = os.path.join(OUT, f)
    if not os.path.exists(p): continue
    cur = RL.speed(p); target = hv / HEIGHT
    if cur <= 0 or cur >= target - 0.5: continue
    fac = target / cur; k = KFEval(p); kf = KFFile(p)
    t0 = np.array(k.sample(k.start)['Bip01'][0], float)
    n = max(2, int(round((k.stop - k.start) * 30)) + 1); keys = []
    for i in range(n):
        tt = k.start + (k.stop - k.start) * i / (n - 1); tr, R = k.sample(tt)['Bip01']
        tr = np.array(tr, float); d = tr - t0; d[:2] *= fac; keys.append((tt, t0 + d, np.array(R, float)))
    kf.set_channel('Bip01', keys); kf.save(p)
    print('   speed match %-18s %6.1f -> %6.1f units/s (skeleton; human %.1f world)' % (f, cur, RL.speed(p), hv))
if C.get('pin'):
    # (with the flamer out the Mister Handy / Gutsy body sphere (Bip01 Spine) and jets (Pelvis) bend
    # over and stay bent; a plasma shot straightens them) those bones are keyed only by some weapon files (its idle,
    # locomotion and 2HH aims never key them; the 2HH attacks at priority 0), so whatever moves them after the
    # animation update is never undone. Every file now keys them - static at the bind pose, priority 20 (the 1HP
    # files, which straighten the robot, key them so).
    B = ctx.BIND; ROOT0 = []
    for f in made + [os.path.join('Locomotion', 'Hurt', x) for x in os.listdir(os.path.join(OUT, 'Locomotion', 'Hurt'))]:
        p = os.path.join(OUT, f); kf = KFFile(p); have = [c for _, c in kf.cb]
        for n in C['pin']:
            if n not in have: RL.add_channel(kf, n, tr=np.array(B[n][0], float), R=np.array(B[n][1], float))
        kf.save(p)
        set_priority(p, set(C['pin']), 20, exact=True)
        # (firing the flamer still turns the whole robot over) the root channels of its 2HH / 2HL attack
        # files kept the vanilla spin's priority 0 - the only robot files with Bip01 / NonAccum at 0 (its 1HP attacks
        # 19, every other robot's 2HH attacks 26, all upright); raised to 26 like the other robots' attacks
        kf = KFFile(p); d = bytearray(kf.f.blocks[kf.seq]); n0 = 0
        for o, n in kf.cb:
            if n in ('Bip01', 'Bip01 NonAccum') and d[o + 8] == 0: d[o + 8] = 26; n0 += 1
        if n0: kf.f.blocks[kf.seq] = bytes(d); kf.save(p); ROOT0.append(f)
    print('  pinned', C['pin'], 'in', len(made), 'files; root priority 0 -> 26 in', len(ROOT0))
for f in made + [os.path.join('Locomotion', 'Hurt', x) for x in os.listdir(os.path.join(OUT, 'Locomotion', 'Hurt'))]:
    RL.enum_to_sound(os.path.join(OUT, f), C['ENUM'])
if C.get('projnode'):
    TGT, FOLLOW, BIND = C['projnode']; SK = Skeleton(SKEL); nf = 0
    PAR = SK.parent['ProjectileNode']; b0 = SK.local['ProjectileNode']
    for f in made:
        m = re.match(r'^(1hp|2ha|2hr|2hh|2hl|1gt|1md|1lm)', f)
        if not m or m.group(1) not in FOLLOW + BIND: continue
        p = os.path.join(OUT, f); kf = KFFile(p)
        if 'ProjectileNode' in [c for _, c in kf.cb]: drop_channel(kf, 'ProjectileNode')
        RL.add_channel(kf, 'ProjectileNode', tr=np.array(b0[0], float), R=np.array(b0[1], float))
        if m.group(1) in FOLLOW:
            k = KFEval(p); n = max(2, int(round((k.stop - k.start) * 30)) + 1); keys = []
            for i in range(n):
                tt = k.start + (k.stop - k.start) * i / (n - 1); smp = k.sample(tt); loc = {}
                for nm in SK.order:
                    tr, R, _ = SK.local[nm]
                    if nm in smp:
                        if smp[nm][0] is not None: tr = smp[nm][0]
                        if smp[nm][1] is not None: R = smp[nm][1]
                    loc[nm] = (np.array(tr, float), np.array(R, float))
                W = SK.fk(loc); pp, pR = W[PAR][0], W[PAR][1]; tp, tR = W[TGT][0], W[TGT][1]
                keys.append((tt, pR.T @ (tp - pp), pR.T @ tR))
            kf.set_channel('ProjectileNode', keys)
        kf.save(p); set_priority(p, {'ProjectileNode'}, 60, exact=True); nf += 1
    print('  ProjectileNode keyed in', nf, 'files (follows', TGT, 'in', FOLLOW, '; bind in', BIND, ')')
if C.get('weapon_follow'):
    # (the player's gun was drawn on the Mister Handy - HideWeapon notwithstanding - turned to the side and firing that
    # way: a prn key moves the skeleton's Weapon node (and the model on it) under the named bone with its bind transform
    # from under the claw's Dummy01) every gun / thrown / mine file keeps Weapon under its own parent (prn keys -> that
    # parent) and keys it, scale 0.001, onto the type's emitter (PRN_OF) frame by frame, +X along the emitter's +Y (level
    # forward), +Y up: the model is unseen and its own ProjectileNode is on the emitter, pointing ahead; equips /
    # unequips / holsters hold it at its bind, unseen
    SK = Skeleton(SKEL); WP = SK.parent['Weapon']; wb = SK.local['Weapon']; nf = 0
    for f in made:
        m = re.match(r'^(1hp|2ha|2hr|2hh|2hl|1gt|1md|1lm)(.*)\.kf$', f)
        if not m or m.group(1) not in C['PRN_OF']: continue
        EM = C['PRN_OF'][m.group(1)]; p = os.path.join(OUT, f); kf = KFFile(p)
        d = bytearray(kf.f.blocks[kf.tk_block]); n, = struct.unpack_from('<I', d, 4)
        for j in range(n):
            t, si = struct.unpack_from('<fi', d, 8 + 8 * j)
            if kf.f.strings[si].lower().startswith('prn:'): struct.pack_into('<i', d, 8 + 8 * j + 4, kf.f.str_index('prn: ' + WP))
        kf.f.blocks[kf.tk_block] = bytes(d)
        if 'Weapon' in [c for _, c in kf.cb]: drop_channel(kf, 'Weapon')
        RL.add_channel(kf, 'Weapon', tr=np.array(wb[0], float), R=np.array(wb[1], float))
        if re.match(r'^(equip|unequip|holster)', m.group(2)):
            keys = [(0.0, np.array(wb[0], float), np.array(wb[1], float))]
        else:
            k = KFEval(p); nk = max(2, int(round((k.stop - k.start) * 30)) + 1); keys = []
            for i in range(nk):
                tt = k.start + (k.stop - k.start) * i / (nk - 1); smp = k.sample(tt); loc = {}
                for nm in SK.order:
                    tr, R, _ = SK.local[nm]
                    if nm in smp:
                        if smp[nm][0] is not None: tr = smp[nm][0]
                        if smp[nm][1] is not None: R = smp[nm][1]
                    loc[nm] = (np.array(tr, float), np.array(R, float))
                W = SK.fk(loc); pp, pR = W[WP][0], W[WP][1]; ep, eR = W[EM][0], W[EM][1]
                ps = W[WP][2] if len(W[WP]) > 2 else 1.0
                Rw = np.column_stack([eR[:, 1], eR[:, 2], np.cross(eR[:, 1], eR[:, 2])])
                keys.append((tt, pR.T @ (ep - pp) / ps, pR.T @ Rw))
        kf.set_channel('Weapon', keys)
        ent = [o for o, c in kf.cb if c == 'Weapon'][0]
        ii = struct.unpack_from('<i', kf.f.blocks[kf.seq], ent)[0]
        b = bytearray(kf.f.blocks[ii]); struct.pack_into('<f', b, 28, 0.001); kf.f.blocks[ii] = bytes(b)
        di = struct.unpack_from('<i', b, 32)[0]
        if di >= 0:                                   # keyed: a scale key too (the data's own scale track, not only the static value)
            db = kf.f.blocks[di]; assert db[-4:] == b'\0\0\0\0'
            kf.f.blocks[di] = db[:-4] + struct.pack('<IIff', 1, 1, keys[0][0], 0.001)
        kf.save(p); set_priority(p, {'Weapon'}, 55, exact=True); nf += 1
    print('  Weapon on the emitter (scale 0.001, prn ->', WP + ') in', nf, 'files')
RL.sneak_copies(OUT, made)
print(ROBOT, len(made), 'groups +', len(made), 'sneak copies (+ hurt) ->', OUT, '| hover:', sorted(HOVER))
