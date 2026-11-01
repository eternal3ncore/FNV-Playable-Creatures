"""Eyebot skeleton for Playable Creatures.
usage: python3 build_skel_eyebot.py <eyebot skeleton.nif> <out Skeleton.nif> <camera height>
The eyebot rig (Creatures\\Eyebot\\Skeleton.nif, 24 nodes) is a Bip01 rig whose biped names are reused for the sphere
parts: Bip01 Head = the sphere, Thighs / Calves / Feet = antennae (the laser emitter Dummy01_HeadLaser hangs under
R Foot), UpperArm / Forearm / Hand = fins. Added:
  * Camera3rd (child of Scene Root) at <camera height> above the feet, slightly behind - the 3rd-person view pivot;
  * PCSkeleton:Eyebot identification marker (read by PlayableCreatures.dll), HeadAnims under Bip01 Head;
  * Weapon and ProjectileNode under Dummy01_HeadLaser (the equip animation's own "Prn: Dummy01_HeadLaser"; the weapon
    model itself is never drawn - ini HideWeapon=1), ProjectileNode at the emitter tip like ProjectileNode_HeadLaser;
  * every other human node the engine / human-rigged gear may name, as zero-offset stand-ins on the closest existing
    parent (Pelvis / Spine chain under NonAccum, clavicles / pauldrons on the stand-in spine, twist bones, fingers,
    thumbs and toes on the fins / antennae) - nothing keys them, they only have to exist."""
import sys
import numpy as np                                    # before the fnv path (its dis.py shadows the stdlib one)
sys.path.insert(0, '/home/claude/fnv')
from nifedit import NifFile
from nif import Nif
SRC, OUT, CAMZ = sys.argv[1], sys.argv[2], float(sys.argv[3])
HUM = '/home/claude/fnv/ref_weap/skeleton.nif'
f = NifFile(SRC); h = NifFile(HUM)
added = []


def add(parent, name, trans=(0, 0, 0), rot=(1, 0, 0, 0, 1, 0, 0, 0, 1)):
    if f.find(name) is not None: return
    pi = f.find(parent); assert pi is not None, parent
    f.add_node(pi, name, trans, rot, flags=524302); added.append((parent, name))


hc = h.node(h.find('Camera3rd'))
add('Scene Root', 'Camera3rd', (0.0, hc['trans'][1], CAMZ), hc['rot'])
add('Scene Root', 'PCSkeleton:Eyebot')
add('Bip01 Head', 'HeadAnims')
tip = f.node(f.find('ProjectileNode_HeadLaser'))['trans']
add('Dummy01_HeadLaser ', 'Weapon') if f.find('Dummy01_HeadLaser ') is not None else add('Dummy01_HeadLaser', 'Weapon')
add('Dummy01_HeadLaser ' if f.find('Dummy01_HeadLaser ') is not None else 'Dummy01_HeadLaser', 'ProjectileNode', tip)
# projectile direction: a weapon fires along its projectile node's local +Y (vanilla gun NIFs: hunting
# rifle / flamer ProjectileNode Y = the barrel, weapon +X; missile launcher Y = its -Y barrel). The eyebot's
# ProjectileNode_HeadLaser has +Y pointing UP from the emitter (NPCs aim at their target, so it never mattered); the
# laser points along the emitter's +X. Both projectile nodes get the rifle convention (local Y = the emitter's X), so the
# player's shot leaves the tip forward instead of straight up.
BARREL_Y = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)      # columns X=(0,0,1) Y=(1,0,0) Z=(0,1,0)
# the stand-in Weapon node too: a thrown grenade / placed mine leaves from the weapon, so it points the same way
for pn in ('ProjectileNode_HeadLaser', 'ProjectileNode', 'Weapon'):
    i = f.find(pn); r = f.node(i)
    R = np.array(r['rot'], float).reshape(3, 3) @ BARREL_Y
    r['rot'] = tuple(float(x) for x in R.reshape(9)); f.set_node(i, r)
for n in ('Bip01 Pelvis', 'Bip01 Spine'): add('Bip01 NonAccum', n)
add('Bip01 Spine', 'Bip01 Spine1'); add('Bip01 Spine1', 'Bip01 Spine2'); add('Bip01 Spine2', 'Bip01 Neck')
for s in ('L', 'R'):
    add('Bip01 Neck', f'Bip01 {s} Clavicle'); add('Bip01 Spine2', f'Bip01 {s}Pauldron')
    add(f'Bip01 {s} Foot', f'Bip01 {s} Toe0')
    add(f'Bip01 {s} UpperArm', f'Bip01 {s}UpArmTwistBone'); add(f'Bip01 {s} Forearm', f'Bip01 {s} ForeTwist')
    add(f'Bip01 {s} Hand', f'Bip01 {s} Thumb1'); add(f'Bip01 {s} Thumb1', f'Bip01 {s} Thumb11'); add(f'Bip01 {s} Thumb11', f'Bip01 {s} Thumb12')
    for k in '1234':
        add(f'Bip01 {s} Hand', f'Bip01 {s} Finger{k}'); add(f'Bip01 {s} Finger{k}', f'Bip01 {s} Finger{k}1')
        add(f'Bip01 {s} Finger{k}1', f'Bip01 {s} Finger{k}2')
add('Bip01 R UpperArm', 'Bip01 R ForeTwistDriver')
import os; os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'wb').write(f.to_bytes())
print('added', len(added))
n = Nif(OUT); names = {x[3] for x in n.tree()}
hn = {x[3] for x in Nif(HUM).tree()}
print('human nodes missing:', sorted(x for x in hn - names if x))
for need in ('PCSkeleton:Eyebot', 'Camera3rd', 'HeadAnims', 'Weapon', 'ProjectileNode'): assert need in names, need
