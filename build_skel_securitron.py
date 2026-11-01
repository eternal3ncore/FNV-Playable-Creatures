"""Securitron skeletons for Playable Creatures.
usage: python3 -P build_skel_securitron.py <nvsecuritron src dir> <out dir> <camera height>
Two skeletons in one folder (same animations / idle tree), one per race, differing only in the face screen:
  Skeleton.nif      (Mk I,  marker PCSkeleton:Securitron)       police screen   (nvsecuritronpolicescreen01.nif)
  SkeletonMkII.nif  (Mk II, marker PCSkeleton:SecuritronMkII)   infantry screen (nvsecuritroninfantryscreen01.nif)
From the vanilla Creatures\\NVSecuritron\\Skeleton.nif (wheel, fork, body, two arms; Weapon under Bip01 RHand):
  * Camera3rd (child of Scene Root) at <camera height> above the ground, the human's y offset;
  * the marker, HeadAnims under Bip01 Head;
  * ragdoll head bone: the screen's hinged body moved onto Bip01 Head (the player's ragdoll needs a 'Bip01 Head' bone);
  * the creature's extra model parts, which a creature gets from its NIFZ list and an NPC race can't carry, grafted
    under the skeleton nodes of the same name: face screen -> Screen01Root, screen static -> ScreenStaticRoot, voice
    box -> VoiceBox_Root (BSXFlags 'animated' so their controllers run). The smoke trail (damage FX) is left out;
  * projectile direction: a weapon fires along its projectile node's local +Y; the securitron's four
    ProjectileNode_* (machine gun, gatling laser, launcher, missiles) point their barrel along local +X (NPCs aim at
    their target, so it never mattered). Each is turned so local +Y = its old +X (rifle convention, as the eyebot);
  * ProjectileNode under Weapon (identity): the animations re-parent Weapon (prn keys) onto the projectile node of
    the arm that fires the equipped weapon type, so any gun's shot / thrown item leaves from that arm's muzzle;
  * every other human node, as zero-offset stand-ins: spine / neck on the body, clavicle / upper arm / forearm / hand
    on the matching arm segment (R Hand on Bip01 RHand), fingers / thumbs / twists under those, legs on the pelvis."""
import os, struct, sys
import numpy as np
sys.path.insert(0, '/home/claude/fnv')
from nifedit import NifFile
from nif import Nif
from graft import graft, set_bsx_animated

SRC, OUT, CAMZ = sys.argv[1], sys.argv[2], float(sys.argv[3])
HUM = '/home/claude/fnv/ref_weap/skeleton.nif'
BARREL_Y = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)      # columns X=(0,0,1) Y=(1,0,0) Z=(0,1,0)
PNODES = ('ProjectileNode_MachineGun', 'ProjectileNode_GatlingLaser', 'ProjectileNode_Launcher', 'ProjectileNode_Missle')
# human node -> securitron node it stands in on (when the human parent has no better match)
PLACE = {'Bip01 Spine': 'Bip01 Pelvis', 'Bip01 Spine2': 'Bip01 Spin02', 'Bip01 Neck': 'Bip01 Body',
         'Bip01 R Clavicle': 'Bip01 RShoulder', 'Bip01 R UpperArm': 'Bip01 RArm01', 'Bip01 R Forearm': 'Bip01 RArm03',
         'Bip01 R Hand': 'Bip01 RHand', 'Bip01 L Clavicle': 'Bip01 LShoulder', 'Bip01 L UpperArm': 'Bip01 LArm01',
         'Bip01 L Forearm': 'Bip01 LArm03', 'Bip01 L Hand': 'Bip01 LHand',
         'Bip01 LPauldron': 'Bip01 Body', 'Bip01 RPauldron': 'Bip01 Body'}
# every vanilla face screen is grafted, one node each ('PCFace:<name>'); the DLL shows the one of the
# player's Eyes choice (race menu) and hides the rest. In the file only the race's default face is visible.
FACES = ['police', 'infantry', 'victor', 'yesman', 'mrhouse', 'jane', 'marilyn', 'blank']
VARIANTS = [('Skeleton.nif', 'PCSkeleton:Securitron', 'police'),
            ('SkeletonMkII.nif', 'PCSkeleton:SecuritronMkII', 'infantry')]


def build(out_name, marker, screen):
    f = NifFile(os.path.join(SRC, 'skeleton.nif')); h = Nif(HUM)
    added = []

    def add(parent, name, trans=(0, 0, 0), rot=(1, 0, 0, 0, 1, 0, 0, 0, 1)):
        if f.find(name) is not None: return
        pi = f.find(parent); assert pi is not None, parent
        f.add_node(pi, name, trans, rot, flags=524302); added.append((parent, name))

    # the player now uses the securitron's own body part data (DLL NVSecuritronBodyPartData, head part
    # node 'Bip01 Screen01'), so the ragdoll's head bone is Screen01 again, where the vanilla skeleton has its hinged
    # body: the move below is skipped (PC_SEC_HEADMOVE=1 applies it).
    if os.environ.get('PC_SEC_HEADMOVE') == '1': move_head_body(f)
    hn = {x[3]: x for x in h.tree()}
    finish(f, h, hn, added, add, out_name, marker, screen)


def move_head_body(f):
    # ragdoll head bone. The player's ragdoll setup (0x87E130 -> 0xC7DE60 -> 0xC79340) looks up the
    # body-part data's head node ("Bip01 Head", human BPTD) among the ragdoll's bones and needs it with a parent; the
    # securitron's Bip01 Head has no rigid body, so its pose matching was never set up and the eye-position lookup read
    # an uninitialised pose (crash 0xCDA8F8; log: head -1, pose54 0). Its face screen's hinged body (Bip01
    # Screen01: bhkRigidBodyT + limited hinge to Bip01 Body) is moved onto Bip01 Head: collision object + blend
    # controller re-targeted; ragdoll bone "Bip01 Head" with parent Bip01 Body.
    si = f.find('Bip01 Screen01'); hi = f.find('Bip01 Head')
    sr = f.node(si); hr = f.node(hi); coll = sr['coll']; assert coll >= 0 and hr['coll'] < 0
    blend = None; c = sr['ctrl']
    while c >= 0:                                     # unlink the bhkBlendController from Screen01's controller chain
        nxt = struct.unpack_from('<i', f.blocks[c], 0)[0]
        if nxt >= 0 and f.types[f.btype[nxt]] == 'bhkBlendController':
            blend = nxt; d = bytearray(f.blocks[c]); struct.pack_into('<i', d, 0, struct.unpack_from('<i', f.blocks[nxt], 0)[0]); f.blocks[c] = bytes(d); break
        c = nxt
    assert blend is not None
    sr['coll'] = -1; f.set_node(si, sr)
    d = bytearray(f.blocks[coll]); struct.pack_into('<i', d, 0, hi); f.blocks[coll] = bytes(d)          # collision target
    d = bytearray(f.blocks[blend]); struct.pack_into('<i', d, 0, -1); struct.pack_into('<i', d, 22, hi); f.blocks[blend] = bytes(d)
    c = hr['ctrl']
    if c < 0: hr['ctrl'] = blend
    else:
        while struct.unpack_from('<i', f.blocks[c], 0)[0] >= 0: c = struct.unpack_from('<i', f.blocks[c], 0)[0]
        d = bytearray(f.blocks[c]); struct.pack_into('<i', d, 0, blend); f.blocks[c] = bytes(d)
    hr['coll'] = coll; f.set_node(hi, hr)


def finish(f, h, hn, added, add, out_name, marker, screen):
    hc = hn['Camera3rd'][4]
    add('Scene Root', 'Camera3rd', (0.0, hc['trans'][1], CAMZ), hc['rot'])
    add('Scene Root', marker)
    add('Bip01 Head', 'HeadAnims')
    for pn in PNODES:
        i = f.find(pn); r = f.node(i)
        R = np.array(r['rot'], float).reshape(3, 3) @ BARREL_Y
        r['rot'] = [float(x) for x in R.reshape(9)]; f.set_node(i, r)
    add('Weapon', 'ProjectileNode')
    # human stand-ins in the human tree order (parents first)
    tree = h.tree(); stack = []
    for d, b, t, nm, r in tree:
        while stack and stack[-1][0] >= d: stack.pop()
        par = stack[-1][1] if stack else None
        stack.append((d, nm))
        if r is None or nm in ('Scene Root', 'Camera3rd') or f.find(nm) is not None: continue
        parent = PLACE.get(nm) or par
        while parent is not None and f.find(parent) is None: parent = PLACE.get(parent, 'Bip01 Body')
        add(parent, nm)
    for face in FACES:
        idx, n = graft(f, 'Screen01Root', os.path.join(SRC, 'nvsecuritron%sscreen01.nif' % face), 0, 'PCFace:' + face)
        if face != screen:
            r = f.node(idx); r['flags'] |= 1; f.set_node(idx, r)          # hidden (NiAVObject flag 1)
        print('grafted face', face, n, 'blocks', '(shown)' if face == screen else '(hidden)')
    for src, node, name in (('nvsecuritronscreenstatic.nif', 'ScreenStaticRoot', 'PCScreenStatic'),
                            ('nvsecuritronvoicebox.nif', 'VoiceBox_Root', 'PCVoiceBox')):
        idx, n = graft(f, node, os.path.join(SRC, src), 0, name)
        print('grafted', src, '->', node, 'as', name, n, 'blocks')
    print('BSXFlags', set_bsx_animated(f))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, out_name); open(p, 'wb').write(f.to_bytes())
    n = Nif(p); names = {x[3] for x in n.tree()}
    missing = sorted(x for x in set(hn) - names if x)
    print(out_name, 'added', len(added), 'stand-ins / nodes; human nodes missing:', missing)
    for need in (marker, 'Camera3rd', 'HeadAnims', 'Weapon', 'ProjectileNode', 'PCScreenStatic', 'PCVoiceBox') + tuple('PCFace:' + x for x in FACES): assert need in names, need


for v in VARIANTS: build(*v)
