"""Creature reload/jam animations built only from the creature's own data (Zetan: alien equip motion).
For each weapon type (1hp, 2hr) writes every group the engine can ask for, under its exact name, so no
runtime substitution is needed:
  Reload A..S (plain), Reload W..Z + W..Z Start (looping reloads; loop step has a 'Hit' key = one round),
  Jam A..S, W..Z.
Sequence: renamed, cycle CLAMP, stop time trimmed, text keys replaced (equip's prn/Attach/Enum keys removed so the
weapon stays in the hand)."""
import sys, struct, os
sys.path.insert(0, '/home/claude/fnv')
from nifedit import NifFile
from nif import Nif
SRC = 'assets/meshes/dlc05/creatures/alien'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'build/reload'
os.makedirs(OUT, exist_ok=True)
PLAIN = 'ABCDEFGHIJKLMNOPQRS'; LOOP = 'WXYZ'
def make(src, dst, seqname, length, keys):
    f = NifFile(src)
    bi = [i for i, t in enumerate(f.btype) if f.types[t] == 'NiControllerSequence'][0]
    b = bytearray(f.blocks[bi])
    ncb = struct.unpack_from('<I', b, 4)[0]
    struct.pack_into('<i', b, 0, f.str_index(seqname))
    off = 12 + 29 * ncb
    tk = struct.unpack_from('<i', b, off + 4)[0]
    struct.pack_into('<I', b, off + 8, 2)            # CLAMP
    struct.pack_into('<f', b, off + 20, length)     # stop time
    f.blocks[bi] = bytes(b)
    # text keys
    tb = bytearray(f.blocks[tk]); name = struct.unpack_from('<i', tb, 0)[0]
    nb = struct.pack('<iI', name, len(keys)) + b''.join(struct.pack('<fi', t, f.str_index(s)) for t, s in keys)
    f.blocks[tk] = nb
    open(dst, 'wb').write(f.to_bytes())
    Nif(dst)   # parse check
n = 0
for hp in ('1hp', '2hr'):
    src = f'{SRC}/{hp}equip.kf'
    for L in PLAIN:
        make(src, f'{OUT}/{hp}reload{L.lower()}.kf', f'Reload{L}', 1.6, [(0, 'start'), (0.03, 'Blend:3'), (1.6, 'end')]); n += 1
        make(src, f'{OUT}/{hp}jam{L.lower()}.kf', f'Jam{L}', 1.2, [(0, 'start'), (0.03, 'Blend:3'), (1.2, 'end')]); n += 1
    for L in LOOP:
        make(src, f'{OUT}/{hp}reload{L.lower()}start.kf', f'Reload{L}Start', 0.8, [(0, 'start'), (0.8, 'end')]); n += 1
        make(src, f'{OUT}/{hp}reload{L.lower()}.kf', f'Reload{L}', 0.9, [(0, 'start'), (0.45, 'Hit'), (0.9, 'end')]); n += 1
        make(src, f'{OUT}/{hp}jam{L.lower()}.kf', f'Jam{L}', 1.2, [(0, 'start'), (0.03, 'Blend:3'), (1.2, 'end')]); n += 1
print(n, 'files ->', OUT)
