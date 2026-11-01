import sys; sys.path.insert(0, '/home/claude/fnv')
from nifedit import NifFile
import struct
f = NifFile('assets/meshes/dlc05/creatures/alien/skeleton.nif')
f.types = []; f.btype = []; f.blocks = []; f.strings = []
root = dict(name=f.str_index('Scene Root'), extra=[], ctrl=-1, flags=0x0008000E, trans=[0,0,0], rot=[1,0,0,0,1,0,0,0,1],
            scale=1.0, props=[], coll=-1, children=[], effects=[])
f.add_block('NiNode', NifFile.build_node(root))
f.footer = struct.pack('<Ii', 1, 0)
out = 'build/meshes/PlayableCreatures/Zetan/Empty.nif'
open(out, 'wb').write(f.to_bytes())
from nif import Nif
n = Nif(out); print(n.nblocks, n.types, n.strings, [x[3] for x in n.tree()], len(open(out,'rb').read()))
