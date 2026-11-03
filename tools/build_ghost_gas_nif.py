"""Ghost Gas projectile model: the Dead Money ghost leg gas spray (nvdlc01_ghostlegrhtfx.nif: billboard particle system,
textures\\nvdlc01\\effects\\FXGhostLegFX.dds, its colour / alpha / rotation) as a flame-type projectile model, laid out as
the vanilla flamer's (Projectiles\\FlamerFlame01.NIF): root + BSX copied from it, the spray subtree grafted under the root,
the emitter node turned as the flamer's (emits along the projectile's +Y), world-space particles, the emitter tuned
from the leg's slow puff to a spray that carries over the flamer's reach, and the emitter switched on as the flamer's:
the leg's emitter-active track only puffs from 0.25 to 0.37 s of a 1.75 s loop, longer than a projectile lives (nothing
was drawn), so its controller timing and on / off keys are the flamer's (on from 0 to 0.33 s).
usage: python3 -P build_ghost_gas_nif.py <flamerflame01.nif> <nvdlc01_ghostlegrhtfx.nif> <out.nif>"""
import os, sys, struct
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nifedit import NifFile
from graft import graft

SPEED, SPEED_VAR = 2200.0, 600.0       # units / s (flamer 3300 +- 990, the leg puff 90)
DECL_VAR = 0.20                        # cone half-angle, rad (flamer 0.07, leg 0.14)
RADIUS, RADIUS_VAR = 40.0, 12.0        # particle radius (leg 20)
LIFE, LIFE_VAR = 0.40, 0.08            # s (flamer 0.37 +- 0.07)
BIRTH = 40.0                           # particles / s per projectile (leg 60, flamer 30)
MAXP = 32                              # particle pool per projectile (leg 3000, flamer 12)
GROW, FADE, BASE = 0.12, 0.20, 0.30    # grow-from / fade-out times, start size (leg 0.33 / 0.33 / 0.25)

flame, leg, out = sys.argv[1:4]
dst = NifFile(flame)
emit_rot = dst.node(dst.find('FireStrips01-Emitter'))['rot']
_fl = lambda t: [b for i, b in enumerate(dst.blocks) if dst.types[dst.btype[i]] == t]
FLAME_CTLR_TIMING = _fl('NiPSysEmitterCtlr')[0][4:22]      # flags, frequency, phase, start, stop
FLAME_ACTIVE = _fl('NiBoolData')[0]                         # emitter on at 0, off at the stop time
# keep only the flamer's root + its BSX flags
dst.blocks = dst.blocks[:2]; dst.btype = dst.btype[:2]
assert dst.types[dst.btype[1]] == 'BSXFlags'
r = dst.node(0); r['children'] = []; r['effects'] = []; r['extra'] = [1]; r['name'] = dst.str_index('GhostGasProjectile')
dst.set_node(0, r)
dst.strings = [dst.strings[i] if i in (r['name'], 1) else dst.strings[i] for i in range(len(dst.strings))]
spray, n = graft(dst, 'GhostGasProjectile', leg, 4, 'GhostGasSpray')
sp = dst.node(spray); sp['trans'] = [0, 0, 0]; sp['rot'] = [1, 0, 0, 0, 1, 0, 0, 0, 1]; sp['scale'] = 1.0; dst.set_node(spray, sp)
ei = dst.find('SuperSpray01-Emitter')
e = dst.node(ei); e['trans'] = [0, 0, 0]; e['rot'] = list(emit_rot); dst.set_node(ei, e)

def blocks_of(t): return [i for i, b in enumerate(dst.btype) if dst.types[b] == t]
for i in blocks_of('NiPSysBoxEmitter'):
    b = bytearray(dst.blocks[i])
    struct.pack_into('<4f', b, 13, SPEED, SPEED_VAR, 0.0, DECL_VAR)
    struct.pack_into('<4f', b, 53, RADIUS, RADIUS_VAR, LIFE, LIFE_VAR)
    dst.blocks[i] = bytes(b)
for i in blocks_of('NiPSysGrowFadeModifier'):
    b = bytearray(dst.blocks[i]); struct.pack_into('<f', b, 13, GROW); struct.pack_into('<f', b, 19, FADE); struct.pack_into('<f', b, 25, BASE)
    dst.blocks[i] = bytes(b)
for i in blocks_of('NiPSysData'):
    b = bytearray(dst.blocks[i]); struct.pack_into('<H', b, 4, MAXP); dst.blocks[i] = bytes(b)
for i in blocks_of('NiPSysEmitterCtlr'):
    c = bytearray(dst.blocks[i]); c[4:22] = FLAME_CTLR_TIMING; dst.blocks[i] = bytes(c)
    fi = struct.unpack_from('<i', c, 26)[0]
    b = bytearray(dst.blocks[fi]); struct.pack_into('<f', b, 0, BIRTH); dst.blocks[fi] = bytes(b)
    vi = struct.unpack_from('<i', c, 34)[0]                                    # emitter-active bool interpolator
    di = struct.unpack_from('<i', dst.blocks[vi], 1)[0]; dst.blocks[di] = FLAME_ACTIVE
# drop strings no block uses any more is not needed (an unused string table entry is harmless)
open(out, 'wb').write(dst.to_bytes())
print('wrote', out, len(dst.blocks), 'blocks,', n, 'grafted')
