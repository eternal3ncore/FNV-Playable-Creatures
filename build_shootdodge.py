"""PlayableCreatures_ShootDodge.esp - the optional Max Payne style dives (its own pack, loaded after the race packs).
The pack = this plugin + the dive animations (anim/dive.py: JumpLoop / JumpLand Left / Right / Backward, mt + sneakmt)
in the race's skeleton folder, overwriting the race's own directional jumps. Core (PlayableCreatures.dll, GhostMoves)
sees the dive spell through the race's DiveSpell= setting: when this plugin is loaded, strafe + jump (or back + jump with a
weapon drawn) casts it and jumps (the dive); without it, the race keeps its own move (Ghost People: Dead Money's hop).
Records (master FalloutNV.esm only):
  SCPT PCShootDodgeEffectSCRIPT 0x800 - copy of Ghostification's zGhostDodgeEffectSCRIPT (player.setghost 1 / 0)
  MGEF PCShootDodgeEffect       0x801 - copy of zGhostDodgeEffect, its script = 0x800
  SPEL PCShootDodgeSpell        0x802 - TurboEffect (slow motion) SLOWMO s, always (the Ghost hop's is combat only);
                                        crit +50 for SLOWMO s in combat; SetGhost 1 s
usage: python3 -P build_shootdodge.py <out.esp>"""
import struct, sys
sys.path.append('/home/claude/fnv')
from esm import Plugin

SLOWMO = 2                      # s: the dive in the air (~0.9 s) and the landing / get-up (1.0 s)
MOD = 1 << 24
SCPT, MGEF, SPEL = MOD | 0x800, MOD | 0x801, MOD | 0x802


def z(s): return s.encode('latin1') + b'\0'
def sub(t, data): return t.encode() + struct.pack('<H', len(data)) + data
def record(t, fid, subs, flags=0):
    body = b''.join(sub(k, v) for k, v in subs)
    return t.encode() + struct.pack('<IIIIHH', len(body), flags, fid, 0, 15, 0) + body
def group(label, recs):
    body = b''.join(recs)
    return b'GRUP' + struct.pack('<I4sIIHH', 24 + len(body), label.encode(), 0, 0, 0, 0) + body
u32 = lambda v: struct.pack('<I', v)
efit = lambda mag, dur, av: struct.pack('<IIIIi', mag, 0, dur, 0, av)
def ctda(func, comp, op=0, p1=0):
    return struct.pack('<B3sfHHIIII', op << 5, b'\0\0\0', float(comp), func, 0, p1, 0, 0, 0)

GT = Plugin('/home/claude/fnv/ghostif/GhostTrait.esp')
gt = {r.edid(): r for r in GT.recs if r.type != 'TES4'}
src = gt['zGhostDodgeEffectSCRIPT']
for k, v in src.subs():
    if k == 'SCRO': assert struct.unpack('<I', v)[0] >> 24 == 0          # FalloutNV forms only (the player)
scpt = record('SCPT', SCPT, [(k, z('PCShootDodgeEffectSCRIPT') if k == 'EDID' else v) for k, v in src.subs()])
def mg(k, v):
    if k == 'EDID': return z('PCShootDodgeEffect')
    if k == 'FULL': return z('Shootdodge')
    if k == 'DATA': v = bytearray(v); struct.pack_into('<I', v, 8, SCPT); return bytes(v)
    return v
mgef = record('MGEF', MGEF, [(k, mg(k, v)) for k, v in gt['zGhostDodgeEffect'].subs()])
spel = record('SPEL', SPEL, [('EDID', z('PCShootDodgeSpell')), ('FULL', z('Shootdodge')), ('SPIT', gt['zzGhostMove'].get('SPIT')),
    ('EFID', u32(0x120D80)), ('EFIT', efit(1, SLOWMO, 51)),                          # TurboEffect: slow motion, always
    ('EFID', u32(0x6AA5D)), ('EFIT', efit(50, SLOWMO, 14)), ('CTDA', ctda(289, 1)),  # crit +50 in combat (IsInCombat == 1)
    ('EFID', u32(MGEF)), ('EFIT', efit(0, 1, -1))])                                  # SetGhost 1 s
groups = [group('MGEF', [mgef]), group('SCPT', [scpt]), group('SPEL', [spel])]
tes4 = record('TES4', 0, [('HEDR', struct.pack('<fII', 1.34, 3 + len(groups), 0x803)), ('CNAM', z('i3ncore')),
    ('SNAM', z('Playable Creatures: Shootdodge - Max Payne style dives for human-skeleton races (Ghost People)')),
    ('MAST', z('FalloutNV.esm')), ('DATA', struct.pack('<Q', 0))])
open(sys.argv[1], 'wb').write(tes4 + b''.join(groups))
print('wrote', sys.argv[1], 'spell %08X' % SPEL)
