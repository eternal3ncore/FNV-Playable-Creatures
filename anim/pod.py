"""Pod furniture (Tranquility Lane / Vault 112, marker 16) and placeholder seating for robots without a seated pose.
  PodEnter.kf  the human pod entry's length, keys (pod lid sound 0.5, sit sound 2.13) and root path: standing idle, then
               the race's own Chair_RightEnter (the pod files are the human right-side chair set) rising LIFT onto the
               pod seat, the trunk reclining RECLINE deg (spine to head) as it settles
  PodIdle.kf   its seated loop (DynamicIdle_ChairSit / the Zetan's alien sit) on the pod seat, reclined
  PodExit.kf   the human pod exit's length, keys (lid sound 0.23) and root path: sits up, Chair_RightExit stepping down
  --robot      every chair / stool file the furniture tree names = the robot's own idle (enter / exit 1.73 / 1.53 s,
               loops as long as its idle, relax specials 4 s): it floats into the seat and out again
Segments are cross-faded over 0.2 s.
usage: python3 pod.py <folder name> <race folder: mtidle.kf + Skeleton.nif> <chair files dir> <out IdleAnims dir>
       python3 pod.py --robot <folder name> <race folder> <out IdleAnims dir>"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.append(os.path.dirname(HERE))
from kf import KF, KFEval, m2q, q2m, slerp
import rig
from act_idles import Shim, wrot, rotx, chain_of, ease
from hand_xfer import local_pose

POD = '/home/claude/fnv/ref_act/pod/bsa/meshes/characters/_male/idleanims/'
ALIEN_SIT = '/home/claude/fnv/ref_act/pod/bsa/meshes/dlc05/creatures/alien/idleanims/dynamicidle_alienssit.kf'
RECLINE = 18.0
LIFT = 69.8          # pod seat above a chair seat: human pod idle NonAccum z 106.6 - chair sit 36.8
PRIO = 45


def blend(A, B, w):
    if w <= 0: return A
    if w >= 1: return B
    return {n: (A[n][0] * (1 - w) + B[n][0] * w, q2m(slerp(m2q(A[n][1]), m2q(B[n][1]), w))) for n in A}


def recline(sk, loc, ch, a):
    for nm in ch:
        pR = wrot(sk, loc, sk.parent[nm]); R = pR @ loc[nm][1]
        loc[nm] = (loc[nm][0], pR.T @ rotx(a / len(ch)) @ R)
    return loc


def pose_of(sk, ev, t):
    return local_pose(sk, ev.sample(min(max(t, ev.start), ev.stop)))


def build_pod(name, folder, chairs, out_dir):
    """the vanilla pod files are its Chair_Right set raised onto the pod seat: the human pelvis ends LIFT above its chair
    height, the root (Bip01) walks the pod's own path. The engine turns the actor between entry / seated / exit (the
    entry ends turned, the seated loop is authored facing forward again), so each file keeps its own frame: the entry
    holds its last frame, the exit starts on its first."""
    os.makedirs(out_dir, exist_ok=True)
    skel = os.path.join(folder, 'Skeleton.nif'); cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    idle = KFEval(os.path.join(folder, 'mtidle.kf'))
    enter = KFEval(os.path.join(chairs, 'Chair_RightEnter.kf')); ek = KF(os.path.join(chairs, 'Chair_RightEnter.kf'))
    exit_ = KFEval(os.path.join(chairs, 'Chair_RightExit.kf'))
    lp = ALIEN_SIT if name == 'Zetan' else os.path.join(chairs, 'DynamicIdle_ChairSit.kf'); loop = KFEval(lp); lk = KF(lp)
    ch = chain_of(sk); rec = np.radians(RECLINE)
    keyed = list(dict.fromkeys([b[0] for ev in (idle, enter, exit_, loop) for b in ev.blocks if b[0] in sk.local and b[0] != 'Bip01'] + ch))
    def lift(P, z):
        t, R = P['Bip01 NonAccum']; P['Bip01 NonAccum'] = (t + np.array([0, 0, z]), R); return P
    def root(P, ev, t):
        b = ev.sample(min(max(t, ev.start), ev.stop)).get('Bip01')
        if b is not None and b[0] is not None: P['Bip01'] = (np.array(b[0], float), np.eye(3))
        return P
    # enter: idle, then the right-side chair entry (its sit sound on the pod file's), lifted onto the seat
    he = KFEval(POD + 'sittranquilitychairenter.kf'); h = KF(POD + 'sittranquilitychairenter.kf'); L = h.stop; n = int(round(L * 30)) + 1
    sit_h = next(t for t, v in h.textkeys if 'SitChairDown' in v)
    sit_c = next((t for t, v in ek.textkeys if 'SitChairDown' in v), 0.27)
    t0 = max(0.6, sit_h - sit_c - 0.6); t1 = t0 + (enter.stop - enter.start)
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        P = blend(local_pose(sk, idle.sample(t % idle.stop)), pose_of(sk, enter, enter.start + t - t0), ease((t - (t0 - 0.2)) / 0.2))
        P = lift(P, LIFT * ease((t - t0) / (t1 - t0)))
        P = recline(sk, P, ch, rec * ease((t - (t1 - 0.3)) / max(L - t1, 0.2)))
        frames.append((t, root(P, he, t)))
    rig.write_kf(cr, os.path.join(out_dir, 'PodEnter.kf'), 'SpecialIdle_Chair_PodEnter', L, [(t, v.strip()) for t, v in h.textkeys],
                 frames, bones=[(b, PRIO) for b in ['Bip01'] + keyed], cycle=2)
    # seated: the chair loop on the pod seat, reclined
    L = loop.stop - loop.start; n = int(round(L * 30)) + 1
    frames = [(L * i / (n - 1), recline(sk, lift(pose_of(sk, loop, loop.start + L * i / (n - 1)), LIFT), ch, rec)) for i in range(n)]
    rig.write_kf(cr, os.path.join(out_dir, 'PodIdle.kf'), 'DynamicIdle_ChairPod', L, [(0.0, 'start'), (L, 'end')],
                 frames, bones=[(b, PRIO) for b in keyed], cycle=lk.cycle)
    # exit: sits up, the right-side chair exit stepping down, holds its last frame
    hx = KFEval(POD + 'sittranquilitychairexit.kf'); h = KF(POD + 'sittranquilitychairexit.kf'); L = h.stop; n = int(round(L * 30)) + 1
    t0 = 0.8; t1 = t0 + (exit_.stop - exit_.start)
    frames = []
    for i in range(n):
        t = L * i / (n - 1)
        P = pose_of(sk, exit_, exit_.start + t - t0)
        P = lift(P, LIFT * (1 - ease((t - t0) / (t1 - t0))))
        P = recline(sk, P, ch, rec * (1 - ease(t / t0)))
        frames.append((t, root(P, hx, t)))
    rig.write_kf(cr, os.path.join(out_dir, 'PodExit.kf'), 'SpecialIdle_Chair_PodExit', L, [(t, v.strip()) for t, v in h.textkeys],
                 frames, bones=[(b, PRIO) for b in ['Bip01'] + keyed], cycle=2)


def build_robot(name, folder, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    skel = os.path.join(folder, 'Skeleton.nif'); cr = Shim(skel, os.path.join(folder, 'mtidle.kf')); sk = cr.sk
    idle = KFEval(os.path.join(folder, 'mtidle.kf')); keyed = [b[0] for b in idle.blocks if b[0] != 'Bip01' and b[0] in sk.local]
    def write(fn, seq, L, cycle, keys):
        n = max(2, int(round(L * 30)) + 1); frames = []
        for i in range(n):
            t = L * i / (n - 1); s = idle.sample(t % idle.stop); loc = local_pose(sk, s)
            frames.append((t, loc))
        rig.write_kf(cr, os.path.join(out_dir, fn), seq, L, keys, frames, bones=[(b, PRIO) for b in keyed], cycle=cycle)
    for side in ('Left', 'Right', 'Back', 'Forward'):
        write(f'Chair_{side}Enter.kf', f'SpecialIdle_Chair_{side}Enter', 1.73, 2, [(0.0, 'start'), (0.5, 'Blend:15'), (1.73, 'end')])
        write(f'Chair_{side}Exit.kf', f'SpecialIdle_Chair_{side}Exit', 1.53, 2, [(0.0, 'start'), (0.6, 'Blend:15'), (1.53, 'end')])
    write('StoolEnter.kf', 'SpecialIdle_StoolEnter', 1.73, 2, [(0.0, 'start'), (0.5, 'Blend:15'), (1.73, 'end')])
    write('StoolExit.kf', 'SpecialIdle_StoolExit', 1.53, 2, [(0.0, 'start'), (0.6, 'Blend:15'), (1.53, 'end')])
    write('DynamicIdle_ChairSit.kf', 'DynamicIdle_ChairSit', idle.stop, 0, [(0.0, 'start'), (idle.stop, 'end')])
    write('DynamicIdle_SitStool.kf', 'DynamicIdle_SitStool', idle.stop, 0, [(0.0, 'start'), (idle.stop, 'end')])
    for x in 'ABC':
        write(f'SitChairRelax{x}.kf', f'SpecialIdle_SitChairRelax{x}', 4.0, 2, [(0.0, 'start'), (4.0, 'end')])


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == '--robot': build_robot(*a[1:4])
    else: build_pod(*a[:4])
    print('ok', a)
