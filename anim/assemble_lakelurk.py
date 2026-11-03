"""Assembles the Lakelurk skeleton folder (meshes\\PlayableCreatures\\Lakelurk\\): its own KFs (root + Locomotion +
Locomotion\\Hurt; its own IdleAnims stay in the vanilla Creatures\\MirelurkKing folder the get-up idles point at; the
specialanims walk variants are left out), the generated weapon sets (build_creature.py), locomotion completion +
crouched sneak (gen_loco_ttw ... crouch, its root-level strafes / turns as the sources), furniture IdleAnims
(retarget_idle_creature.py), Skeleton.nif (build_skel_creature.py). Its two power files are renamed to the regular
pattern (h2h_attackpower -> h2hattackpower) and copied to 1HM / 2HM; its idle loop's own vox keys are dropped (on the
player they sounded every ~4.6 s). Then Enum text keys -> Sound keys (enum_keys 'lakelurk'), then the post passes:
lakelurk_shriek (guns = its shriek from the mouth, gun and melee weapons hidden, ProjectileNode added to the skeleton),
post_build (blocks: own guard; fist / melee aims raised to 23; priorities), fill_updown, sneak_fix, the forward power
lunge's sneak copies back to the standing lunge, power_fill, power_legs, lakelurk_shriek --hide again.
usage: python3 assemble_lakelurk.py <deploy root>"""
import sys, os, shutil, glob, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enum_keys as EK
from nifedit import NifFile
from sound_keys import text_keys
SRC = '/home/claude/fnv/creature_src_lurk/meshes/creatures/mirelurkking'
B = '/home/claude/fnv/build/lakelurk'
RENAME = {'h2h_attackpower.kf': 'h2hattackpower.kf', 'h2h_attackforwardpower.kf': 'h2hattackforwardpower.kf'}
def cp(a, b):
    os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copyfile(a, b)
root = sys.argv[1]
D = os.path.join(root, 'meshes', 'PlayableCreatures', 'Lakelurk')
if os.path.isdir(D): shutil.rmtree(D)
n0 = 0
for f in glob.glob(SRC + '/*.kf'):
    b = os.path.basename(f); cp(f, os.path.join(D, RENAME.get(b, b))); n0 += 1
for f in glob.glob(SRC + '/locomotion/*.kf'): cp(f, os.path.join(D, 'Locomotion', os.path.basename(f))); n0 += 1
for f in glob.glob(SRC + '/locomotion/hurt/*.kf'): cp(f, os.path.join(D, 'Locomotion', 'Hurt', os.path.basename(f))); n0 += 1
for T in ('1hm', '2hm'):
    for b in RENAME.values(): cp(os.path.join(D, b), os.path.join(D, T + b[3:]))
n1 = 0
for f in os.listdir(B + '/anims'):
    if f.endswith('.kf'): cp(f'{B}/anims/{f}', os.path.join(D, f)); n1 += 1
n2 = 0
for d, _, fs in os.walk(B + '/loco'):
    for f in fs: cp(os.path.join(d, f), os.path.join(D, os.path.relpath(os.path.join(d, f), B + '/loco'))); n2 += 1
n3 = 0
for f in os.listdir(B + '/idle'): cp(f'{B}/idle/{f}', os.path.join(D, 'IdleAnims', f)); n3 += 1
cp(B + '/Skeleton.nif', os.path.join(D, 'Skeleton.nif'))
# idle loop vox (Sound: NPCMirelurkIdle) dropped from the idle and its sneak copy
for fn in ('mtidle.kf', 'sneakmtidle.kf'):
    p = os.path.join(D, fn); f = NifFile(p); i, name, keys = text_keys(f)
    out = [(t, s) for t, s in keys if not s.strip().lower().startswith('sound: npcmirelurkidle')]
    f.blocks[i] = struct.pack('<iI', name, len(out)) + b''.join(struct.pack('<fi', t, f.str_index(s)) for t, s in out)
    open(p, 'wb').write(f.to_bytes())
st = {}; nk = 0
for d, _, fs in os.walk(D):
    for f in fs:
        if not f.endswith('.kf'): continue
        r = EK.convert(os.path.join(d, f), EK.MAPS['lakelurk'])
        if not r: continue
        nf, s = r; open(os.path.join(d, f), 'wb').write(nf.to_bytes()); nk += 1
        for k, v in s.items(): st[k] = st.get(k, 0) + v
total = sum(len(fs) for _, _, fs in os.walk(D))
print(f'Lakelurk: own {n0}, sets {n1}, loco/sneak {n2}, furniture {n3}, enum-converted {nk} {st}, total files {total}')

H = os.path.dirname(os.path.abspath(__file__))
def py(*a):
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True, cwd=H)
    if r.returncode: sys.exit(r.stderr)
    print(' ', os.path.basename(a[0]), ' | '.join(r.stdout.strip().splitlines()[-6:]))
py(os.path.join(H, 'lakelurk_shriek.py'), D, os.path.join(D, 'Skeleton.nif'))
py(os.path.join(H, 'post_build.py'), D, 'Lakelurk')
py(os.path.join(H, 'fill_updown.py'), D)
# its own standing power has no sneak file (sneak_fix only adds sneak copies of the groups it lists): copied, then crouched
shutil.copyfile(os.path.join(D, 'h2hattackpower.kf'), os.path.join(D, 'sneakh2hattackpower.kf'))
py(os.path.join(H, 'sneak_fix.py'), D, '--apply')
for T in ('h2h', '1hm', '2hm'): shutil.copyfile(os.path.join(D, T + 'attackforwardpower.kf'), os.path.join(D, 'sneak' + T + 'attackforwardpower.kf'))
py(os.path.join(H, 'power_fill.py'), os.path.dirname(D), '--apply')
py(os.path.join(H, 'power_legs.py'), D, '--apply')
py(os.path.join(H, 'lakelurk_shriek.py'), D, os.path.join(D, 'Skeleton.nif'), '--hide')
print('files', sum(len(fs) for _, _, fs in os.walk(D)))
