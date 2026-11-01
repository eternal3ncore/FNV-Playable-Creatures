"""Graft a node subtree (incl. particle systems, controllers, properties) from one NIF (20.2.0.7/bsver 34)
into another, remapping block refs and string-table indices. Supports the block types used by the
Dead Money ghost FX nifs; anything else raises, so nothing is copied half-understood."""
import struct, sys
sys.path.insert(0, '/home/claude/fnv')
from nif import Nif
from nifedit import NifFile

u32 = lambda d, o: struct.unpack_from('<I', d, o)[0]
i32 = lambda d, o: struct.unpack_from('<i', d, o)[0]

def _objnet(d):
    n = u32(d, 4); refs = [8 + 4 * k for k in range(n)] + [8 + 4 * n]
    return [0], refs, 12 + 4 * n
def _avobj(d):
    strs, refs, o = _objnet(d)
    o += 4 + 12 + 36 + 4                      # flags, translation, rotation, scale
    n = u32(d, o); refs += [o + 4 + 4 * k for k in range(n)]; o += 4 + 4 * n
    refs.append(o); o += 4                    # collision object
    return strs, refs, o

def layout(t, d):
    """-> (string offsets, ref offsets) of block type t with bytes d"""
    if t in ('NiNode', 'BSFadeNode', 'NiBillboardNode'):
        s, r, o = _avobj(d)
        n = u32(d, o); r += [o + 4 + 4 * k for k in range(n)]; o += 4 + 4 * n
        n = u32(d, o); r += [o + 4 + 4 * k for k in range(n)]; o += 4 + 4 * n
        if t == 'NiBillboardNode': o += 2           # (Mr. Handy jet FX) billboard mode
        assert o == len(d), (t, o, len(d)); return s, r
    if t == 'NiParticleSystem':
        s, r, o = _avobj(d)
        r += [o, o + 4]; o += 8                   # data, skin instance
        nm = u32(d, o); o += 4 + 8 * nm           # material data: names + extra data
        o += 4 + 1                                # active material, material needs update
        o += 1                                    # world space
        n = u32(d, o); r += [o + 4 + 4 * k for k in range(n)]; o += 4 + 4 * n
        assert o == len(d), (t, o, len(d)); return s, r
    if t in ('NiAlphaProperty', 'NiMaterialProperty', 'BSShaderNoLightingProperty', 'NiStencilProperty'):
        s, r, o = _objnet(d); return s, r
    if t == 'NiTexturingProperty':
        s, r, o = _objnet(d)
        has_base = d[o + 6]
        assert has_base == 1, 'only base texture supported'
        p = o + 7 + 4 + 2                            # source ref, flags
        if d[p]: p += 1 + 8 + 8 + 4 + 4 + 8          # texture transform: translation, scale, rotation, method, center
        else: p += 1
        assert not any(d[p:]), 'only base texture supported'
        return s, r + [o + 7]
    # (securitron screen / voice box parts) geometry, its data, PP lighting shader, texture set, colour /
    # texture-transform controllers, point3 interpolators
    if t in ('NiTriStrips', 'NiTriShape'):
        s, r, o = _avobj(d)
        r += [o, o + 4]; o += 8                      # data, skin instance
        nm = u32(d, o); s += [o + 4 + 4 * k for k in range(nm)]; o += 4 + 8 * nm
        o += 4 + 1                                   # active material, material needs update
        assert o == len(d), (t, o, len(d)); return s, r
    if t in ('NiTriStripsData', 'NiTriShapeData'):
        o = 4; n = struct.unpack_from('<H', d, o)[0]; o += 2 + 2      # group id, vertices, keep / compress flags
        if d[o]: o += 12 * n
        o += 1
        vf = struct.unpack_from('<H', d, o)[0]; o += 2              # BS vector flags (UV sets, tangents)
        if d[o]:
            o += 12 * n
            if vf & 0x1000: o += 24 * n
        o += 1
        o += 16                                       # center, radius
        if d[o]: o += 16 * n
        o += 1
        o += 8 * n * (vf & 0x3F)
        o += 2                                        # consistency flags
        add = o; assert i32(d, add) == -1, 'geometry additional data'
        return [], []
    if t == 'BSShaderPPLightingProperty':
        s, r, o = _objnet(d); assert len(d) == o + 42, (t, len(d), o); return s, r + [o + 22]
    if t == 'BSShaderTextureSet': return [], []
    if t == 'NiPoint3Interpolator': return [], [12]
    if t in ('NiPosData',): return [], []
    if t == 'NiSourceTexture':
        s, r, o = _objnet(d); return s + [o + 1], r + [o + 5]
    if t in ('NiStringExtraData',): return [0, 4], []
    if t in ('NiFloatExtraData', 'BSXFlags', 'NiIntegerExtraData'): return [0], []
    TC = [0, 22]                                  # next controller, target
    if t == 'NiPSysUpdateCtlr': return [], TC
    if t in ('NiTransformController', 'NiVisController', 'NiAlphaController', 'NiMaterialColorController',
             'NiTextureTransformController', 'BSRefractionStrengthController',
             'BSMaterialEmittanceMultController'): return [], TC + [26]          # + robobrain BrainTalk
    if t in ('NiPSysModifierActiveCtlr',): return [30], TC + [26]
    if t == 'NiPSysEmitterCtlr': return [30], TC + [26, 34]
    if t == 'NiFloatExtraDataController': return [30], TC + [26]
    if t == 'NiTransformInterpolator': return [], [32]
    if t == 'NiFloatInterpolator': return [], [4]
    if t in ('NiBoolInterpolator', 'NiBoolTimelineInterpolator'): return [], [1]
    if t in ('NiTransformData', 'NiFloatData', 'NiBoolData'): return [], []
    if t == 'NiPSysData':
        assert i32(d, 31) == -1, 'NiPSysData additional data'; return [], []
    M = [0], [8]                                  # modifier: name, target particle system
    if t in ('NiPSysSpawnModifier', 'NiPSysGrowFadeModifier', 'BSPSysSimpleColorModifier',
             'NiPSysRotationModifier', 'NiPSysPositionModifier', 'NiPSysBoundUpdateModifier'): return M
    if t == 'NiPSysAgeDeathModifier': return [0], [8, 14]
    if t == 'NiPSysBoxEmitter': return [0], [8, 69]
    if t in ('NiPSysGravityModifier', 'NiPSysDragModifier'): return [0], [8, 13]
    raise NotImplementedError(t)

def graft(dst, dst_parent, src_path, src_root, new_name, keep_children=None, drop_root_extras=True, drop_root_ctrl=True):
    """dst: NifFile (modified in place). Returns the new root block index in dst."""
    s = Nif(src_path)
    blocks = {i: bytearray(s.d[s.boff[i]:s.boff[i] + s.bsize[i]]) for i in range(s.nblocks)}
    # root edits: keep only chosen children, optionally drop extras / controller
    root = blocks[src_root]
    rn = NifFile.parse_node(bytes(root))
    if keep_children is not None: rn['children'] = [c for c in rn['children'] if c in keep_children]
    if drop_root_extras: rn['extra'] = []
    if drop_root_ctrl: rn['ctrl'] = -1
    blocks[src_root] = bytearray(NifFile.build_node(rn))
    # collect reachable blocks
    order, seen, stack = [], set(), [src_root]
    while stack:
        b = stack.pop()
        if b < 0 or b in seen: continue
        seen.add(b); order.append(b)
        _, refs = layout(s.tname(b), blocks[b])
        for o in refs:
            r = i32(blocks[b], o)
            if r >= 0 and r not in seen: stack.append(r)
    order.sort()
    newidx = {b: len(dst.blocks) + k for k, b in enumerate(order)}
    for b in order:
        d = blocks[b]; t = s.tname(b)
        strs, refs = layout(t, d)
        for o in refs:
            r = i32(d, o)
            if r >= 0:
                assert r in newidx, (t, b, o, r)
                struct.pack_into('<i', d, o, newidx[r])
        for o in strs:
            si = i32(d, o)
            if si >= 0:
                val = s.strings[si]
                if b == src_root and o == 0: val = new_name
                struct.pack_into('<i', d, o, dst.str_index(val))
        dst.btype.append(dst.type_index(t)); dst.blocks.append(bytes(d))
    pi = dst.find(dst_parent); assert pi is not None, dst_parent
    p = dst.node(pi); p['children'].append(newidx[src_root]); dst.set_node(pi, p)
    return newidx[src_root], len(order)

def set_bsx_animated(dst):
    for i, b in enumerate(dst.blocks):
        if dst.types[dst.btype[i]] == 'BSXFlags':
            v = u32(b, 4)
            if not v & 1:
                bb = bytearray(b); struct.pack_into('<I', bb, 4, v | 1); dst.blocks[i] = bytes(bb)
            return v, v | 1
