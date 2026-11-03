"""Assembles the Capital super mutants' own skeleton folder (meshes\\PlayableCreatures\\SuperMutantDC\\, TTW): the finished
New Vegas Super Mutant folder with Fallout 3's own animations wherever they differ from New Vegas' (user request: the
TTW super mutants use their TTW animations). The two games' super mutant skeletons are identical bone for bone; 52 of
the files Fallout 3 shares with New Vegas are the same motion, ~60 differ only by New Vegas' Spine re-posed 5-7 deg
(kept: the New Vegas set's generated reloads / jams / throws are built on those poses), and the rest are Fallout 3's own
motion (differ by more than DIFF_DEG or in length): its idle, walk / run / strafes / backward + hurt, unarmed and
two-handed melee attacks and power attacks, grenade aim / throw, rifle reload A / jam A, plus 49 gun files only Fallout 3
has (2HR / 2HA AttackLeft / Right, 2HR Attack4 / 5, 2HH AttackLeft / AttackSpin2, 2HL AttackLeft / Attack3, reloads /
jams B-F, I). Those replace the New Vegas files; then the files derived from them are rebuilt:
  sneak movement  gen_loco2.py supermutantdc (its idle / locomotion crouched, crab runs from its run)
  side runs       Locomotion\\mtfastleft / right = those crab runs
  sneak copies    of every other replaced file, crouched by sneak_fix
  throws          throws_native (AttackThrow2-8 = renamed copies of its own throw)
  power attacks   the New Vegas fills dropped and redone: H2H AttackPower / Back (power_fill), 2HM side powers = its
                  standing power when its own are charges (as the New Vegas set), power_legs
  text keys       enum_keys 'supermutant'; priorities prio_fix (walk cap)
Skeleton.nif = the New Vegas one with its marker renamed PCSkeleton:SuperMutantDC; DeathPoses.psa = Fallout 3's.
usage: python3 assemble_smdc.py <New Vegas SuperMutant folder> <deploy root>"""
import sys, os, re, shutil, glob, subprocess, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kf import KFEval
from nifedit import NifFile
import enum_keys as EK
DC = '/home/claude/fnv/creature_src_ttw/smspinebreakerdc'
DIFF_DEG = 10.0
NV_SRC = '/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/smspinebreaker'
H = os.path.dirname(os.path.abspath(__file__))
nvd, root = sys.argv[1], sys.argv[2]
D = os.path.join(root, 'meshes', 'PlayableCreatures', 'SuperMutantDC')
if os.path.isdir(D): shutil.rmtree(D)
shutil.copytree(nvd, D)


def py(*a):
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True, cwd=H)
    if r.returncode: sys.exit(r.stderr)
    print(' ', os.path.basename(a[0]), ' | '.join(r.stdout.strip().splitlines()[-3:])[:600])


def differs(a_path, b_path):
    a, b = KFEval(a_path), KFEval(b_path)
    if abs(a.stop - b.stop) > 0.02: return True
    bones = {x[0] for x in a.blocks} & {x[0] for x in b.blocks}
    for t in np.linspace(a.start, a.stop, 9):
        sa, sb = a.sample(t), b.sample(t)
        for n in bones:
            if sa.get(n) is None or sb.get(n) is None or sa[n][1] is None or sb[n][1] is None: continue
            R = np.array(sa[n][1]).T @ np.array(sb[n][1])
            if np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))) > DIFF_DEG: return True
    return False


# 1. Fallout 3's own files where they differ (IdleAnims stay: the furniture set is New Vegas-built, get-ups / hit
#    reactions are read from Creatures\SMSpineBreakerDC\IdleAnims by the idle tree)
replaced = []
for f in sorted(glob.glob(DC + '/**/*.kf', recursive=True)):
    rel = os.path.relpath(f, DC).replace('\\', '/').lower()
    if rel.startswith('idleanims/'): continue
    nv = os.path.join(NV_SRC, rel)
    if os.path.exists(nv) and not differs(f, nv): continue
    parts = rel.split('/'); dst = os.path.join(D, *[('Locomotion' if p == 'locomotion' else 'Hurt' if p == 'hurt' else p) for p in parts])
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(f, dst); replaced.append(rel)
print('Fallout 3 files in', len(replaced))
# 2. their derived files: sneak movement + side runs regenerated; sneak copies of the rest
tmp = os.path.join(root, '_smdc_loco'); shutil.rmtree(tmp, ignore_errors=True)
py(os.path.join(H, 'gen_loco2.py'), 'supermutantdc', tmp)
for d, _, fs in os.walk(tmp):
    for fn in fs: shutil.copyfile(os.path.join(d, fn), os.path.join(D, os.path.relpath(os.path.join(d, fn), tmp)))
shutil.rmtree(tmp)
ns = 0
for rel in replaced:
    base = os.path.basename(rel)
    if rel.startswith('locomotion/') or base == 'mtidle.kf' or base.startswith('swim') or 'death' in base: continue
    shutil.copyfile(os.path.join(D, base), os.path.join(D, 'sneak' + base)); ns += 1
print('sneak copies', ns)
# 3. the New Vegas power fills / throws built from New Vegas files: dropped, redone below from Fallout 3's
for fn in ('h2hattackpower.kf', 'h2hattackbackpower.kf', 'sneakh2hattackpower.kf', 'sneakh2hattackbackpower.kf'):
    p = os.path.join(D, fn)
    if os.path.exists(p): os.remove(p)
# 2HM side powers: Fallout 3's are charges too (checked below) -> renamed copies of its standing power, as in New Vegas
def seq_rename(src, dst, seq):
    f = NifFile(src); bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = bytearray(f.blocks[bi]); struct.pack_into('<i', b, 0, f.str_index(seq)); f.blocks[bi] = bytes(b)
    open(dst, 'wb').write(f.to_bytes())
for side in ('left', 'right'):
    k = KFEval(os.path.join(DC, f'2hmattack{side}power.kf'))
    a = k.sample(k.start).get('Bip01'); b = k.sample(k.stop - 1e-4).get('Bip01')
    travel = np.linalg.norm(np.array(b[0]) - np.array(a[0])) if a and b and a[0] is not None and b[0] is not None else 0.0
    print('  2hm', side, 'power root travel %.0f' % travel)
    if travel >= 60:
        for sn in ('', 'sneak'):
            seq_rename(os.path.join(D, sn + '2hmattackpower.kf'), os.path.join(D, f'{sn}2hmattack{side}power.kf'),
                       'AttackLeftPower' if side == 'left' else 'AttackRightPower')
# 4. text keys, then the passes
nk = 0
for d, _, fs in os.walk(D):
    for fn in fs:
        if not fn.endswith('.kf'): continue
        r = EK.convert(os.path.join(d, fn), EK.MAPS['supermutant'])
        if r: open(os.path.join(d, fn), 'wb').write(r[0].to_bytes()); nk += 1
print('enum-converted', nk)
py(os.path.join(H, 'throws_native.py'), D, DC)
py(os.path.join(H, 'sneak_fix.py'), D, '--apply')
py(os.path.join(H, 'power_fill.py'), os.path.dirname(D), '--apply')
py(os.path.join(H, 'power_legs.py'), D, '--apply')
py(os.path.join(H, 'prio_fix.py'), D, '--loco', 'auto')
# 5. skeleton marker + death poses
f = NifFile(os.path.join(D, 'Skeleton.nif')); i = f.find('PCSkeleton:SuperMutant'); assert i is not None
r = f.node(i); r['name'] = f.str_index('PCSkeleton:SuperMutantDC'); f.set_node(i, r); open(os.path.join(D, 'Skeleton.nif'), 'wb').write(f.to_bytes())
shutil.copyfile(os.path.join(DC, 'deathposes.psa'), os.path.join(D, 'DeathPoses.psa'))
print('files', sum(len(fs) for _, _, fs in os.walk(D)))
