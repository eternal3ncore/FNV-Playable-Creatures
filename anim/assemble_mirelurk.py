"""Assembles the Mirelurk skeleton folder (meshes\\PlayableCreatures\\Mirelurk\\): its own KFs (root + Locomotion +
Locomotion\\Hurt; its own IdleAnims stay in the vanilla Creatures\\Mirelurk folder the get-up idles point at),
DeathPoses.psa, the generated melee sets (build_creature.py: 1HM / 2HM = its claw attacks), the backward / side runs
(loco_mirelurk.py), furniture IdleAnims (eyebot_furniture.py ... mirelurk: it climbs onto the seat), Skeleton.nif
(build_skel_creature.py). Sneak = its standing gait: every standing movement file is copied as the sneak one (a crouch
would sink the body onto its four side legs). Its idle loop's own vox key (Enum: Idle) is dropped by the enum map.
Then Enum text keys -> Sound keys (enum_keys 'mirelurk'), then post_build (blocks: own guard), fill_updown, sneak_fix
(sneak copies of the groups without one), power_fill (the back power), power_legs.
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
# sneak = standing gait
ns = 0
for f in ['mtidle.kf'] + ['Locomotion/' + x for x in os.listdir(os.path.join(D, 'Locomotion')) if x.endswith('.kf')]:
    cp(os.path.join(D, f), os.path.join(D, 'sneak' + os.path.basename(f))); ns += 1
st = {}; nk = 0
for d, _, fs in os.walk(D):
    for f in fs:
        if not f.endswith('.kf'): continue
        r = EK.convert(os.path.join(d, f), EK.MAPS['mirelurk'])
        if not r: continue
        nf, s = r; open(os.path.join(d, f), 'wb').write(nf.to_bytes()); nk += 1
        for k, v in s.items(): st[k] = st.get(k, 0) + v
print(f'Mirelurk: own {n0}, sets {n1}, loco {n2}, furniture {n3}, sneak gait {ns}, enum-converted {nk} {st}, total files {sum(len(fs) for _, _, fs in os.walk(D))}')
H = os.path.dirname(os.path.abspath(__file__))
def py(*a):
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True, cwd=H)
    if r.returncode: sys.exit(r.stderr)
    print(' ', os.path.basename(a[0]), ' | '.join(r.stdout.strip().splitlines()[-4:]))
py(os.path.join(H, 'post_build.py'), D, 'Mirelurk')
py(os.path.join(H, 'fill_updown.py'), D)
py(os.path.join(H, 'sneak_fix.py'), D, '--apply')
py(os.path.join(H, 'power_fill.py'), os.path.dirname(D), '--apply')
py(os.path.join(H, 'power_legs.py'), D, '--apply')
print('files', sum(len(fs) for _, _, fs in os.walk(D)))
