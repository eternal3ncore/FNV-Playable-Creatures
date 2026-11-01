"""Ghost People skeleton for Playable Creatures: the DLC's own skeleton + identification marker + HeadAnims
+ the ghosts' own gas FX grafted onto the bones they are parented to in game (Prn): breath at Bip01 Neck1,
leg sprays at the thighs. BSXFlags gets the 'animated' bit so the particle controllers run."""
import sys; sys.path.insert(0, '/home/claude/fnv')
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
print('BSXFlags', set_bsx_animated(f))
open(OUT, 'wb').write(f.to_bytes())
n = Nif(OUT); names = [nm for _, _, _, nm, _ in n.tree()]
for need in ('PCSkeleton:Ghost', 'Camera3rd', 'HeadAnims', 'PCGhostBreath', 'PCGhostLegSprayL', 'PCGhostLegSprayR', 'PCloud02Smoke'):
    assert need in names, need
print('ok', n.nblocks, 'blocks')
