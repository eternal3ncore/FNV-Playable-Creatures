import sys, struct, math
sys.path.insert(0, '/home/claude/fnv')
from nifedit import NifFile
SRC = 'assets/meshes/dlc05/creatures/alien/skeleton.nif'
HUM = 'assets/meshes/characters/_male/skeleton.nif'
OUT = 'build/meshes/PlayableCreatures/Zetan/Skeleton.nif'
f = NifFile(SRC); h = NifFile(HUM)
ratio = 63.86 / 67.77
def local(nf, name):
    r = nf.node(nf.find(name)); return r['trans'], r['rot']
added = []
def add(parent, name, trans, rot=(1,0,0,0,1,0,0,0,1)):
    if f.find(name) is not None: return
    pi = f.find(parent); assert pi is not None, parent
    f.add_node(pi, name, trans, rot, flags=524302); added.append((parent, name))
# 3rd-person camera node (child of Scene Root, like the human skeleton)
t, r = local(h, 'Camera3rd'); add('Scene Root', 'Camera3rd', (t[0], t[1] * ratio, t[2] * ratio), r)
# identification marker (read by the DLL to know which skeleton the player currently has)
add('Scene Root', 'PCSkeleton:Zetan', (0, 0, 0))
# HeadAnims (human facegen anim helper) under head
t, r = local(h, 'HeadAnims'); add('Bip01 Head', 'HeadAnims', t, r)
# human-only bones as stand-ins so human-rigged gear finds every bone it references
for side in ('L', 'R'):
    # thumb chain modelled on the alien's Finger0 chain
    t, r = local(f, f'Bip01 {side} Finger0'); add(f'Bip01 {side} Hand', f'Bip01 {side} Thumb1', t, r)
    t, r = local(f, f'Bip01 {side} Finger01'); add(f'Bip01 {side} Thumb1', f'Bip01 {side} Thumb11', t, r)
    t, r = local(f, f'Bip01 {side} Finger02'); add(f'Bip01 {side} Thumb11', f'Bip01 {side} Thumb12', t, r)
    # fingers 3 and 4 modelled on the alien's Finger2 chain
    for k in ('3', '4'):
        t, r = local(f, f'Bip01 {side} Finger2'); add(f'Bip01 {side} Hand', f'Bip01 {side} Finger{k}', t, r)
        t, r = local(f, f'Bip01 {side} Finger21'); add(f'Bip01 {side} Finger{k}', f'Bip01 {side} Finger{k}1', t, r)
        t, r = local(f, f'Bip01 {side} Finger22'); add(f'Bip01 {side} Finger{k}1', f'Bip01 {side} Finger{k}2', t, r)
    # upper-arm twist bone (human name) mirrors the alien's own twist bone
    t, r = local(f, f'Bip01 {side}UpArmTwist'); add(f'Bip01 {side} UpperArm', f'Bip01 {side}UpArmTwistBone', t, r)
    t, r = local(h, f'Bip01 {side}Pauldron'); add('Bip01 Spine2', f'Bip01 {side}Pauldron', [x * ratio for x in t], r)
t, r = local(f, 'Bip01 R Forearm'); add('Bip01 R UpperArm', 'Bip01 R ForeTwistDriver', t, r)
open(OUT, 'wb').write(f.to_bytes())
print('added', len(added)); [print('  ', p, '->', n) for p, n in added]
# verify
from nif import Nif
n = Nif(OUT); names = {x[3] for x in n.tree()}
hn = {x[3] for x in Nif(HUM).tree()}
print('human nodes missing from Zetan skeleton:', sorted(x for x in hn - names if x))
