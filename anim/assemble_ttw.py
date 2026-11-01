"""Assembles the deployable skeleton folders of the TTW creature races (meshes\\PlayableCreatures\\<Folder>\\):
own KFs (root + Locomotion + Locomotion\\Hurt; the own IdleAnims stay in the vanilla folders the idle trees point at),
generated weapon sets, locomotion completion + sneak (overrides the builder's crouched sneak locomotion), furniture
IdleAnims, Skeleton.nif (+ DeathPoses.psa); then Enum text keys -> Sound keys.
usage: python3 assemble_ttw.py <deploy root>"""
import sys, os, shutil, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enum_keys as EK
from nifedit import NifFile
B = '/home/claude/fnv/build/ttw'; S = '/home/claude/fnv/creature_src_ttw'
JOBS = [('swampfolk', 'Swampfolk', 'Swampfolk', 'swampfolk'), ('hillfolk1', 'Hillfolk', 'Hillfolk', 'swampfolk'), ('trog', 'Trog', 'Trog', 'trog')]
def cp(a, b):
    os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copyfile(a, b)
root = sys.argv[1]
for cfg, folder, skel, emap in JOBS:
    D = os.path.join(root, 'meshes', 'PlayableCreatures', folder)
    if os.path.isdir(D): shutil.rmtree(D)
    src = os.path.join(S, cfg); n0 = 0
    for f in glob.glob(src + '/*.kf'): cp(f, os.path.join(D, os.path.basename(f))); n0 += 1
    for f in glob.glob(src + '/locomotion/*.kf'): cp(f, os.path.join(D, 'Locomotion', os.path.basename(f))); n0 += 1
    for f in glob.glob(src + '/locomotion/hurt/*.kf'): cp(f, os.path.join(D, 'Locomotion', 'Hurt', os.path.basename(f))); n0 += 1
    if os.path.exists(src + '/deathposes.psa'): cp(src + '/deathposes.psa', os.path.join(D, 'DeathPoses.psa'))
    n1 = 0
    for f in os.listdir(f'{B}/{cfg}_sets'): cp(f'{B}/{cfg}_sets/{f}', os.path.join(D, f)); n1 += 1
    n2 = 0
    for d, _, fs in os.walk(f'{B}/{cfg}_loco'):
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), f'{B}/{cfg}_loco'); cp(os.path.join(d, f), os.path.join(D, rel)); n2 += 1
    n3 = 0
    for f in os.listdir(f'{B}/{cfg}_idle'): cp(f'{B}/{cfg}_idle/{f}', os.path.join(D, 'IdleAnims', f)); n3 += 1
    cp(f'{B}/skel/{skel}_Skeleton.nif', os.path.join(D, 'Skeleton.nif'))
    # Enum -> Sound keys (trog: run steps for the run-derived files)
    st = {}; nk = 0
    for d, _, fs in os.walk(D):
        for f in fs:
            if not f.endswith('.kf'): continue
            m = EK.MAPS['trogrun' if emap == 'trog' and 'fast' in f.lower() else emap]
            r = EK.convert(os.path.join(d, f), m)
            if not r: continue
            nf, s = r; open(os.path.join(d, f), 'wb').write(nf.to_bytes()); nk += 1
            for k, v in s.items(): st[k] = st.get(k, 0) + v
    total = sum(len(fs) for _, _, fs in os.walk(D))
    print(f'{folder}: own {n0}, sets {n1}, loco/sneak {n2}, furniture {n3}, enum-converted {nk} {st}, total files {total}')
