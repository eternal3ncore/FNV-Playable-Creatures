"""Rewrite-capable NIF (20.2.0.7 / bsver 34) container."""
import struct
from nif import Nif

class NifFile:
    def __init__(s, path):
        d = open(path, 'rb').read(); n = Nif(d); s.n = n
        # locate header prefix end = start of 'num block types'
        i = d.index(b'\n') + 1 + 4 + 1 + 12
        for _ in range(3):
            i += 1 + d[i]
        s.prefix = bytearray(d[:i])
        s.types = list(n.types)
        s.btype = list(n.btype)
        s.strings = list(n.strings)
        s.blocks = [bytes(d[o:o+sz]) for o, sz in zip(n.boff, n.bsize)]
        end = n.boff[-1] + n.bsize[-1]
        s.footer = d[end:]
        # groups
        s.groups = b'\0\0\0\0'
    def type_index(s, t):
        if t not in s.types: s.types.append(t)
        return s.types.index(t)
    def str_index(s, t):
        if t not in s.strings: s.strings.append(t)
        return s.strings.index(t)
    def add_block(s, tname, data):
        s.btype.append(s.type_index(tname)); s.blocks.append(bytes(data)); return len(s.blocks) - 1
    def to_bytes(s):
        out = bytearray(s.prefix)
        # patch num blocks in prefix
        vpos = s.prefix.index(b'\n') + 1
        struct.pack_into('<I', out, vpos + 4 + 1 + 4, len(s.blocks))
        out += struct.pack('<H', len(s.types))
        for t in s.types: out += struct.pack('<I', len(t)) + t.encode('latin1')
        out += struct.pack(f'<{len(s.btype)}H', *s.btype)
        out += struct.pack(f'<{len(s.blocks)}I', *[len(b) for b in s.blocks])
        out += struct.pack('<II', len(s.strings), max([len(x) for x in s.strings] + [0]))
        for t in s.strings: out += struct.pack('<I', len(t)) + t.encode('latin1')
        out += s.groups
        for b in s.blocks: out += b
        out += s.footer
        return bytes(out)
    # --- NiNode helpers (bsver 34 layout) ---
    @staticmethod
    def parse_node(b):
        i = 0; r = {}
        r['name'], ne = struct.unpack_from('<iI', b, i); i += 8
        r['extra'] = list(struct.unpack_from(f'<{ne}i', b, i)); i += 4 * ne
        r['ctrl'], r['flags'] = struct.unpack_from('<iI', b, i); i += 8
        r['trans'] = list(struct.unpack_from('<3f', b, i)); i += 12
        r['rot'] = list(struct.unpack_from('<9f', b, i)); i += 36
        r['scale'], = struct.unpack_from('<f', b, i); i += 4
        npr, = struct.unpack_from('<I', b, i); i += 4
        r['props'] = list(struct.unpack_from(f'<{npr}i', b, i)); i += 4 * npr
        r['coll'], = struct.unpack_from('<i', b, i); i += 4
        nc, = struct.unpack_from('<I', b, i); i += 4
        r['children'] = list(struct.unpack_from(f'<{nc}i', b, i)); i += 4 * nc
        nef, = struct.unpack_from('<I', b, i); i += 4
        r['effects'] = list(struct.unpack_from(f'<{nef}i', b, i)); i += 4 * nef
        assert i == len(b), (i, len(b))
        return r
    @staticmethod
    def build_node(r):
        b = struct.pack('<iI', r['name'], len(r['extra'])) + struct.pack(f'<{len(r["extra"])}i', *r['extra'])
        b += struct.pack('<iI', r['ctrl'], r['flags'])
        b += struct.pack('<3f', *r['trans']) + struct.pack('<9f', *r['rot']) + struct.pack('<f', r['scale'])
        b += struct.pack('<I', len(r['props'])) + struct.pack(f'<{len(r["props"])}i', *r['props'])
        b += struct.pack('<i', r['coll'])
        b += struct.pack('<I', len(r['children'])) + struct.pack(f'<{len(r["children"])}i', *r['children'])
        b += struct.pack('<I', len(r['effects'])) + struct.pack(f'<{len(r["effects"])}i', *r['effects'])
        return b
    def node(s, idx): return s.parse_node(s.blocks[idx])
    def set_node(s, idx, r): s.blocks[idx] = s.build_node(r)
    def find(s, name):
        for i, b in enumerate(s.blocks):
            if s.types[s.btype[i]] in ('NiNode', 'BSFadeNode'):
                r = s.parse_node(b)
                if 0 <= r['name'] < len(s.strings) and s.strings[r['name']] == name: return i
        return None
    def add_node(s, parent_idx, name, trans=(0, 0, 0), rot=(1, 0, 0, 0, 1, 0, 0, 0, 1), flags=0x0000000E):
        r = dict(name=s.str_index(name), extra=[], ctrl=-1, flags=flags, trans=list(trans), rot=list(rot),
                 scale=1.0, props=[], coll=-1, children=[], effects=[])
        idx = s.add_block('NiNode', s.build_node(r))
        p = s.node(parent_idx); p['children'].append(idx); s.set_node(parent_idx, p)
        return idx
