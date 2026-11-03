"""Assembles the Mirelurk skeleton folder (meshes\\PlayableCreatures\\Mirelurk\\): its own KFs (root + Locomotion +
Locomotion\\Hurt; its own IdleAnims stay in the vanilla Creatures\\Mirelurk folder the get-up idles point at),
DeathPoses.psa, the generated weapon sets (build_creature.py), the backward / side runs + crouched sneak movement
(gen_loco_ttw.py mirelurk ... crouch), furniture IdleAnims (mirelurk_sit.py: it settles its shell onto the seat), Skeleton.nif
(build_skel_creature.py). Guns fire from its mouth with its own 2HL lunge, claws raised (mouth_fire.py mirelurk: gun
and melee weapons hidden, ProjectileNode added to the skeleton). Blocks = both pincers raised before its face
(mirelurk_guard.py -> own_block via post_build). Its idle loop's own vox key (Enum: Idle) is dropped by the enum map.
Then Enum text keys -> Sound keys (enum_keys 'mirelurk'), then mouth_fire, mirelurk_guard + post_build (blocks), fill_updown,
sneak_fix (sneak copies of the groups without one), power_fill (the back power), power_legs, mouth_fire --hide.
usage: python3 assemble_mirelurk.py <deploy root>"""
import sys, os, shutil, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enum_keys as EK
SRC = '/home/claude/fnv/creature_src_lurk/meshes/creatures/mirelurk'
B = '/home/claude/fnv/build/mirelurk'
def cp(a, b):
    os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copyfile(a, b)
root = sys.argv[1]
D = os.path.join(root, 'meshes', 'PlayableCreatures', 'Mirelurk')
if os.path.isdir(D): shutil.rmtree(D)
n0 = 0
for f in glob.glob(SRC + '/*.kf'): cp(f, os.path.join(D, os.path.basename(f))); n0 += 1
for f in glob.glob(SRC + '/locomotion/*.kf'): cp(f, os.path.join(D, 'Locomotion', os.path.basename(f))); n0 += 1
for f in glob.glob(SRC + '/locomotion/hurt/*.kf'): cp(f, os.path.join(D, 'Locomotion', 'Hurt', os.path.basename(f))); n0 += 1
cp(SRC + '/deathposes.psa', os.path.join(D, 'DeathPoses.psa'))
n1 = 0
for f in os.listdir(B + '/anims'):
    if f.endswith('.kf'): cp(f'{B}/anims/{f}', os.path.join(D, f)); n1 += 1
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
        r = EK.convert(os.path.join(d, f), EK.MAPS['mirelurk'])
        if not r: continue
        nf, s = r; open(os.path.join(d, f), 'wb').write(nf.to_bytes()); nk += 1
        for k, v in s.items(): st[k] = st.get(k, 0) + v
print(f'Mirelurk: own {n0}, sets {n1}, loco {n2}, furniture {n3}, enum-converted {nk} {st}, total files {sum(len(fs) for _, _, fs in os.walk(D))}')
H = os.path.dirname(os.path.abspath(__file__))
def py(*a):
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True, cwd=H)
    if r.returncode: sys.exit(r.stderr)
    print(' ', os.path.basename(a[0]), ' | '.join(r.stdout.strip().splitlines()[-4:]))
py(os.path.join(H, 'mouth_fire.py'), 'mirelurk', D, os.path.join(D, 'Skeleton.nif'))
py(os.path.join(H, 'mirelurk_guard.py'), D)
py(os.path.join(H, 'post_build.py'), D, 'Mirelurk')
for f in ('_guard.kf', 'sneak_guard.kf'): os.remove(os.path.join(D, f))
py(os.path.join(H, 'fill_updown.py'), D)
py(os.path.join(H, 'sneak_fix.py'), D, '--apply')
# the forward power lunge (root 512) keeps its standing legs in sneak (a crouched lower body would slide)
for T in ('h2h', '1hm', '2hm'): shutil.copyfile(os.path.join(D, T + 'attackforwardpower.kf'), os.path.join(D, 'sneak' + T + 'attackforwardpower.kf'))
py(os.path.join(H, 'power_fill.py'), os.path.dirname(D), '--apply')
py(os.path.join(H, 'power_legs.py'), D, '--apply')
py(os.path.join(H, 'mouth_fire.py'), 'mirelurk', D, os.path.join(D, 'Skeleton.nif'), '--hide')
print('files', sum(len(fs) for _, _, fs in os.walk(D)))
