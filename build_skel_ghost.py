"""Ghost People skeleton for Playable Creatures: the DLC's own skeleton + identification marker + HeadAnims
+ the ghosts' own gas FX grafted onto the bones they are parented to in game (Prn): breath at Bip01 Neck1,
leg sprays at the thighs; + the mask spray of the gas attack (off at rest, on Bip01 Head). BSXFlags gets the 'animated' bit so the particle controllers run."""
import struct, sys
import numpy as np
sys.path.insert(0, "/home/claude/fnv")
from nifedit import NifFile
from nif import Nif
from graft import graft, set_bsx_animated
G = 'ghost_src/meshes/nvdlc01/creatures/ghosts/'
SRC = G + 'skeleton.nif'
HUM = 'ref_weap/skeleton.nif'
OUT = 'build/meshes/PlayableCreatures/Ghost/Skeleton.nif'
f = NifFile(SRC); h = NifFile(HUM)
def add(parent, name, trans=(0, 0, 0), rot=(1, 0, 0, 0, 1, 0, 0, 0, 1)):
    if f.find(name) is not None: return
    f.add_node(f.find(parent), name, trans, rot, flags=524302); print('added', parent, '->', name)
add('Scene Root', 'PCSkeleton:Ghost')
r = h.node(h.find('HeadAnims')); add('Bip01 Head', 'HeadAnims', r['trans'], r['rot'])
FX = [('nvdlc01_ghostbreathe.nif', 'Bip01 Neck1', 'PCGhostBreath', [20]),       # AnimObject_SmokeRoot only
      ('nvdlc01_ghostleglftfx.nif', 'Bip01 L Thigh', 'PCGhostLegSprayL', None),
      ('nvdlc01_ghostlegrhtfx.nif', 'Bip01 R Thigh', 'PCGhostLegSprayR', None)]
for src, parent, name, keep in FX:
    idx, n = graft(f, parent, G + src, 0, name, keep_children=keep)
    print('grafted', src, '->', parent, 'as', name, n, 'blocks')
# The gas spray of the unarmed forward power attack (anim/ghost_spray.py): a third copy of the leg spray on Bip01 Head at
# the respirator - root PCGhostMaskSprayRoot at MASK (head space: +X up the neck, +Y the face, +Z left), its emitter
# node turned so the emitter's +Z (the emission axis, as the flamer's) points along MASK_DIR, particle system and
# emitter node renamed PCGhostMaskSpray / PCGhostMaskSpray-Emitter (the right leg's are SuperSpray01*), world-space
# particles, and OFF at rest: its own emitter track all off, birth rate 0 - the attack's KF switches it on (controlled
# blocks NiPSysEmitterCtlr NiPSysBoxEmitter:0 EmitterActive / BirthRate, as the Dead Money idle drives the breath).
# Tuned from the leg's slow puff to a short forward spray: 260 +- 60 u/s, cone 0.22 rad, size 20 +- 4 growing from 0.2
# over 0.25 s, life 0.55 +- 0.1 s, alpha 0.85, pool 64.

MASK = (2.5, 13.0, 0.0); MASK_DIR = np.array([-0.25, 1.0, 0.0]) / np.hypot(0.25, 1.0)
_b0 = len(f.blocks)
_root, _n = graft(f, 'Bip01 Head', G + 'nvdlc01_ghostlegrhtfx.nif', 4, 'PCGhostMaskSprayRoot')
_ren = {'SuperSpray01': 'PCGhostMaskSpray', 'SuperSpray01-Emitter': 'PCGhostMaskSpray-Emitter'}
_T = lambda i: f.types[f.btype[i]]
for i in range(_b0, _b0 + _n):
    t = _T(i); b = bytearray(f.blocks[i])
    if t in ('NiNode', 'NiParticleSystem'):
        nm = f.strings[struct.unpack_from('<i', b, 0)[0]]
        if nm in _ren: struct.pack_into('<i', b, 0, f.str_index(_ren[nm]))
    if t == 'NiParticleSystem':
        o = 8 + 4 * struct.unpack_from('<I', b, 4)[0] + 4 + 4 + 12 + 36 + 4      # name, extras, ctrl, flags, trans, rot, scale
        o += 4 + 4 * struct.unpack_from('<I', b, o)[0] + 4 + 8                        # properties, collision, data, skin
        o += 4 + 8 * struct.unpack_from('<I', b, o)[0] + 4 + 1                          # materials, active, needs update
        assert o + 1 + 4 + 4 * struct.unpack_from('<I', b, o + 1)[0] == len(b); b[o] = 1                      # world space
    if t == 'NiPSysBoxEmitter':
        struct.pack_into('<4f', b, 13, 260.0, 60.0, 0.0, 0.22); struct.pack_into('<4f', b, 53, 20.0, 4.0, 0.55, 0.10)
    if t == 'NiPSysGrowFadeModifier':
        struct.pack_into('<f', b, 13, 0.25); struct.pack_into('<f', b, 19, 0.25); struct.pack_into('<f', b, 25, 0.2)
    if t == 'NiMaterialProperty': struct.pack_into('<f', b, 40, 0.85)
    if t == 'NiPSysData': struct.pack_into('<H', b, 4, 64)
    if t == 'NiBoolData':                                                                # emitter track: off throughout
        nk, = struct.unpack_from('<I', b, 0)
        for k in range(nk): b[8 + 5 * k + 4] = 0
    if t == 'NiFloatInterpolator': struct.pack_into('<f', b, 0, 0.0)                     # birth rate 0
    f.blocks[i] = bytes(b)
_r = f.node(_root); _r['trans'] = list(MASK); _r['rot'] = [1, 0, 0, 0, 1, 0, 0, 0, 1]; _r['scale'] = 1.0; f.set_node(_root, _r)
_ei = next(i for i in range(_b0, _b0 + _n) if _T(i) == 'NiNode' and f.strings[struct.unpack_from('<i', f.blocks[i], 0)[0]] == 'PCGhostMaskSpray-Emitter')
_z = MASK_DIR; _x = np.cross([0.0, 0.0, 1.0], _z); _x /= np.linalg.norm(_x); _y = np.cross(_z, _x)
_e = f.node(_ei); _e['trans'] = [0.0, 0.0, 0.0]; _e['rot'] = list(np.column_stack([_x, _y, _z]).reshape(-1)); f.set_node(_ei, _e)
print('grafted mask spray on Bip01 Head:', _n, 'blocks, types', sorted({_T(i) for i in range(_b0, _b0 + _n)}))
print('BSXFlags', set_bsx_animated(f))
open(OUT, 'wb').write(f.to_bytes())
n = Nif(OUT); names = [nm for _, _, _, nm, _ in n.tree()]
for need in ('PCSkeleton:Ghost', 'Camera3rd', 'HeadAnims', 'PCGhostBreath', 'PCGhostLegSprayL', 'PCGhostLegSprayR', 'PCloud02Smoke',
             'PCGhostMaskSprayRoot', 'PCGhostMaskSpray-Emitter', 'PCGhostMaskSpray'):
    assert need in names, need
print('ok', n.nblocks, 'blocks')
