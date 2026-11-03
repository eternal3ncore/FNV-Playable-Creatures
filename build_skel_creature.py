"""Generic creature skeleton for Playable Creatures (Feral Ghoul, Super Mutant, ...).
usage: python3 build_skel_creature.py <tag> <source skeleton.nif> <out Skeleton.nif> <camera scale>
Adds to the creature's own skeleton:
  * Camera3rd (child of Scene Root, the human node's offset scaled by <camera scale> = creature / human head height
    in the creature's own idle) - the engine's 3rd-person camera anchor;
  * PCSkeleton:<tag> identification marker (read by PlayableCreatures.dll);
  * HeadAnims under Bip01 Head (facegen anim helper);
  * human-only bones as stand-ins (thumb chain from the creature's Finger0 chain, upper-arm / forearm twist bones,
    ForeTwistDriver, pauldrons, Neck1; Spine2 as a leaf under Spine1 when the creature has none, e.g. the trog),
    so human-rigged gear (Pip-Boy, hidden armor) finds every bone it names."""
import sys
sys.path.insert(0, '/home/claude/fnv')
from nifedit import NifFile
from nif import Nif
TAG, SRC, OUT, CAM = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
HUM = '/home/claude/fnv/ref_weap/skeleton.nif'
f = NifFile(SRC); h = NifFile(HUM)
added = []
def local(nf, name):
    r = nf.node(nf.find(name)); return r['trans'], r['rot']
def local_or(name, fallback):
    """a joint the creature lacks (the mirelurk's pincer is one joint, Finger0): the given joint's offset instead"""
    return local(f, name if f.find(name) is not None else fallback)
def tip(finger):
    """third joint of a finger chain; two-joint claws (deathclaw) repeat the second joint's offset"""
    return local_or(finger + '2' if f.find(finger + '2') is not None else finger + '1', finger)
def add(parent, name, trans=(0, 0, 0), rot=(1, 0, 0, 0, 1, 0, 0, 0, 1)):
    if f.find(name) is not None: return
    pi = f.find(parent); assert pi is not None, parent
    f.add_node(pi, name, trans, rot, flags=524302); added.append((parent, name))
t, r = local(h, 'Camera3rd'); add('Scene Root', 'Camera3rd', (t[0], t[1] * CAM, t[2] * CAM), r)
if f.find('Bip01 Spine2') is None:                    # e.g. the trog: leaf stand-in halfway to the neck
    t, r = local(f, 'Bip01 Neck'); add('Bip01 Spine1', 'Bip01 Spine2', [x * 0.5 for x in t])
add('Scene Root', f'PCSkeleton:{TAG}')
t, r = local(h, 'HeadAnims'); add('Bip01 Head', 'HeadAnims', t, r)
if f.find('Bip01 Neck1') is None:
    t, r = local(h, 'Bip01 Neck1'); add('Bip01 Neck', 'Bip01 Neck1', (t[0] * CAM, t[1] * CAM, t[2] * CAM), r)
for side in ('L', 'R'):
    if f.find(f'Bip01 {side} Finger0') is not None:
        t, r = local(f, f'Bip01 {side} Finger0'); add(f'Bip01 {side} Hand', f'Bip01 {side} Thumb1', t, r)
        t, r = local_or(f'Bip01 {side} Finger01', f'Bip01 {side} Finger0'); add(f'Bip01 {side} Thumb1', f'Bip01 {side} Thumb11', t, r)
        t, r = tip(f'Bip01 {side} Finger0'); add(f'Bip01 {side} Thumb11', f'Bip01 {side} Thumb12', t, r)
    for k in ('3', '4'):
        if f.find(f'Bip01 {side} Finger2') is not None:
            t, r = local(f, f'Bip01 {side} Finger2'); add(f'Bip01 {side} Hand', f'Bip01 {side} Finger{k}', t, r)
            t, r = local(f, f'Bip01 {side} Finger21'); add(f'Bip01 {side} Finger{k}', f'Bip01 {side} Finger{k}1', t, r)
            t, r = tip(f'Bip01 {side} Finger2'); add(f'Bip01 {side} Finger{k}1', f'Bip01 {side} Finger{k}2', t, r)
    for k in '1234':                                  # pincer claws (mirelurk: Finger0 only): finger stand-ins on its joint
        if f.find(f'Bip01 {side} Finger0') is not None and f.find(f'Bip01 {side} Finger{k}') is None:
            t, r = local(f, f'Bip01 {side} Finger0'); add(f'Bip01 {side} Hand', f'Bip01 {side} Finger{k}', t, r)
            add(f'Bip01 {side} Finger{k}', f'Bip01 {side} Finger{k}1', (2.0, 0, 0))
            add(f'Bip01 {side} Finger{k}1', f'Bip01 {side} Finger{k}2', (2.0, 0, 0))
    for k in '1234':                                  # two-joint claws: tip joint stand-ins
        if f.find(f'Bip01 {side} Finger{k}1') is not None and f.find(f'Bip01 {side} Finger{k}2') is None:
            t, r = local(f, f'Bip01 {side} Finger{k}1'); add(f'Bip01 {side} Finger{k}1', f'Bip01 {side} Finger{k}2', t, r)
    if f.find(f'Bip01 {side}UpArmTwist') is not None:
        t, r = local(f, f'Bip01 {side}UpArmTwist'); add(f'Bip01 {side} UpperArm', f'Bip01 {side}UpArmTwistBone', t, r)
    else:
        add(f'Bip01 {side} UpperArm', f'Bip01 {side}UpArmTwistBone')
    add(f'Bip01 {side} Forearm', f'Bip01 {side} ForeTwist')
    t, r = local(h, f'Bip01 {side}Pauldron'); add('Bip01 Spine2', f'Bip01 {side}Pauldron', [x * CAM for x in t], r)
t, r = local(f, 'Bip01 R Forearm'); add('Bip01 R UpperArm', 'Bip01 R ForeTwistDriver', t, r)
import os; os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'wb').write(f.to_bytes())
print('added', len(added)); [print('  ', p, '->', n) for p, n in added]
n = Nif(OUT); names = {x[3] for x in n.tree()}
hn = {x[3] for x in Nif(HUM).tree()}
print('human nodes missing:', sorted(x for x in hn - names if x))
for need in (f'PCSkeleton:{TAG}', 'Camera3rd', 'HeadAnims'): assert need in names, need
