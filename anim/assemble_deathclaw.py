"""Assembles the Deathclaw skeleton folder (meshes\\PlayableCreatures\\Deathclaw\\): its own KFs (root + Locomotion +
Locomotion\\Hurt; its own IdleAnims stay in the vanilla folder the get-up idles point at), the generated weapon sets
(build_creature.py), locomotion completion + crouched sneak (gen_loco_ttw.py ... crouch), furniture IdleAnims
(retarget_idle_creature.py), Skeleton.nif (build_skel_creature.py) + DeathPoses.psa; then Enum text keys -> Sound
keys (enum_keys 'deathclaw'), then the post passes, in order: deathclaw_mouth (guns fire from the mouth, gun and melee
weapons hidden, ProjectileNode added to the skeleton), post_build (blocks: own guard), fill_updown, sneak_fix
(sneak attacks / aims / blocks / equips crouched like its sneak), the forward power lunge's sneak copies back to the
standing lunge (a crouched lower body would slide 572 units), power_fill (AttackPower / AttackBackPower from its side
power swings), power_legs (side / back powers leave the legs to the movement), deathclaw_mouth --hide again (block hits).
usage: python3 assemble_deathclaw.py <deploy root>"""
import sys, os, shutil, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enum_keys as EK
SRC = '/home/claude/fnv/creature_src/Fallout - Meshes/meshes/creatures/deathclaw'
B = '/home/claude/fnv/build/deathclaw'
def cp(a, b):
    os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copyfile(a, b)
root = sys.argv[1]
D = os.path.join(root, 'meshes', 'PlayableCreatures', 'Deathclaw')
if os.path.isdir(D): shutil.rmtree(D)
n0 = 0
for f in glob.glob(SRC + '/*.kf'): cp(f, os.path.join(D, os.path.basename(f))); n0 += 1
for f in glob.glob(SRC + '/locomotion/*.kf'): cp(f, os.path.join(D, 'Locomotion', os.path.basename(f))); n0 += 1
for f in glob.glob(SRC + '/locomotion/hurt/*.kf'): cp(f, os.path.join(D, 'Locomotion', 'Hurt', os.path.basename(f))); n0 += 1
cp(SRC + '/deathposes.psa', os.path.join(D, 'DeathPoses.psa'))
n1 = 0
for f in os.listdir(B + '/anims'): cp(f'{B}/anims/{f}', os.path.join(D, f)); n1 += 1
n2 = 0
for d, _, fs in os.walk(B + '/loco'):
    for f in fs: cp(os.path.join(d, f), os.path.join(D, os.path.relpath(os.path.join(d, f), B + '/loco'))); n2 += 1
n3 = 0
for f in os.listdir(B + '/idle'): cp(f'{B}/idle/{f}', os.path.join(D, 'IdleAnims', f)); n3 += 1
cp(B + '/Skeleton.nif', os.path.join(D, 'Skeleton.nif'))
st = {}; nk = 0
for d, _, fs in os.walk(D):
    for f in fs:
        if not f.endswith('.kf'): continue
        r = EK.convert(os.path.join(d, f), EK.MAPS['deathclaw'])
        if not r: continue
        nf, s = r; open(os.path.join(d, f), 'wb').write(nf.to_bytes()); nk += 1
        for k, v in s.items(): st[k] = st.get(k, 0) + v
total = sum(len(fs) for _, _, fs in os.walk(D))
print(f'Deathclaw: own {n0}, sets {n1}, loco/sneak {n2}, furniture {n3}, enum-converted {nk} {st}, total files {total}')

import subprocess
H = os.path.dirname(os.path.abspath(__file__))
def py(*a):
    # run from this folder without -P, as each pass is run by hand (power_fill / power_legs import numpy after putting
    # the parent folder, which has a dis.py, first on the path)
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True, cwd=H)
    if r.returncode: sys.exit(r.stderr)
    print(' ', os.path.basename(a[0]), (r.stdout.strip().splitlines() or [''])[-1])
py(os.path.join(H, 'deathclaw_mouth.py'), D, os.path.join(D, 'Skeleton.nif'))
py(os.path.join(H, 'post_build.py'), D, 'Deathclaw')
py(os.path.join(H, 'fill_updown.py'), D)
py(os.path.join(H, 'sneak_fix.py'), D, '--apply')
for T in ('h2h', '1hm', '2hm'): shutil.copyfile(os.path.join(D, T + 'attackforwardpower.kf'), os.path.join(D, 'sneak' + T + 'attackforwardpower.kf'))
py(os.path.join(H, 'power_fill.py'), os.path.dirname(D), '--apply')
py(os.path.join(H, 'power_legs.py'), D, '--apply')
py(os.path.join(H, 'deathclaw_mouth.py'), D, os.path.join(D, 'Skeleton.nif'), '--hide')   # weapon hidden in the files added since
print('files', sum(len(fs) for _, _, fs in os.walk(D)))
