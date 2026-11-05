"""Ghost Gas weapon model: the vanilla Flamer (meshes\\weapons\\2handhandle\\flamer.nif, Fallout - Misc.bsa) without its
fuel tank. The Flamer's tank is the root's child node 'Backpack' (mesh Backpack:0, its own collision), which the engine
moves onto the wearer's Bip01 Spine2 when the weapon is drawn (its NiStringExtraData 'UPB' = 'Bip01 Spine2'), so it
hangs on the back whatever the hand animations do. Here it is unlinked from the root (the gun ##FlamerGun with its
ProjectileNode, and the rest, untouched); the unreferenced blocks stay in the file and are dropped at load.
The Ghost's palm-cast 2HH animations hide the gun itself (Weapon node at scale 0.001).
usage: python3 -P build_ghost_gas_weapon_nif.py <flamer.nif> <out GhostGas.nif>"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nifedit import NifFile


def build(src, out):
    f = NifFile(src)
    bp = f.find('Backpack'); assert bp is not None, 'no Backpack node'
    root = f.node(0); assert bp in root['children'], 'Backpack is not a child of the root'
    root['children'].remove(bp); f.set_node(0, root)
    open(out, 'wb').write(f.to_bytes())
    print('wrote', out, 'root children', root['children'])


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
