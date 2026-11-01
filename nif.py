"""Minimal FO3/FNV NIF (20.2.0.7, bsver 34) reader: header, strings, node tree."""
import struct, sys

class Nif:
    def __init__(s, path_or_bytes):
        d = open(path_or_bytes, 'rb').read() if isinstance(path_or_bytes, str) else path_or_bytes
        s.d = d
        i = d.index(b'\n') + 1
        s.ver, = struct.unpack_from('<I', d, i); i += 4
        i += 1  # endian
        s.uver, s.nblocks, s.bsver = struct.unpack_from('<III', d, i); i += 12
        s.export = []
        for _ in range(3):
            n = d[i]; s.export.append(d[i+1:i+1+n].rstrip(b'\0').decode('latin1')); i += 1 + n
        nt, = struct.unpack_from('<H', d, i); i += 2
        s.types = []
        for _ in range(nt):
            n, = struct.unpack_from('<I', d, i); s.types.append(d[i+4:i+4+n].decode('latin1')); i += 4 + n
        s.btype = list(struct.unpack_from(f'<{s.nblocks}H', d, i)); i += 2 * s.nblocks
        s.bsize = list(struct.unpack_from(f'<{s.nblocks}I', d, i)); i += 4 * s.nblocks
        ns, maxl = struct.unpack_from('<II', d, i); i += 8
        s.strings = []
        for _ in range(ns):
            n, = struct.unpack_from('<I', d, i); s.strings.append(d[i+4:i+4+n].decode('latin1')); i += 4 + n
        ng, = struct.unpack_from('<I', d, i); i += 4 + 4 * ng
        s.boff = []
        for sz in s.bsize:
            s.boff.append(i); i += sz
    def tname(s, b): return s.types[s.btype[b] & 0x7FFF]
    def str(s, idx): return s.strings[idx] if 0 <= idx < len(s.strings) else None
    def objnet(s, b):
        """Parse NiObjectNET + NiAVObject for node-like blocks. returns dict and offset after."""
        d = s.d; i = s.boff[b]
        name, = struct.unpack_from('<i', d, i); i += 4
        ne, = struct.unpack_from('<I', d, i); i += 4
        extra = list(struct.unpack_from(f'<{ne}i', d, i)); i += 4 * ne
        ctrl, = struct.unpack_from('<i', d, i); i += 4
        r = dict(name=s.str(name), extra=extra, ctrl=ctrl)
        return r, i
    def avobj(s, b):
        d = s.d
        r, i = s.objnet(b)
        flags, = struct.unpack_from('<I', d, i); i += 4
        t = struct.unpack_from('<3f', d, i); i += 12
        rot = struct.unpack_from('<9f', d, i); i += 36
        sc, = struct.unpack_from('<f', d, i); i += 4
        np_, = struct.unpack_from('<I', d, i); i += 4
        props = list(struct.unpack_from(f'<{np_}i', d, i)); i += 4 * np_
        coll, = struct.unpack_from('<i', d, i); i += 4
        r.update(flags=flags, trans=t, rot=rot, scale=sc, props=props, coll=coll)
        return r, i
    def node(s, b):
        d = s.d
        r, i = s.avobj(b)
        nc, = struct.unpack_from('<I', d, i); i += 4
        r['children'] = list(struct.unpack_from(f'<{nc}i', d, i)); i += 4 * nc
        return r
    NODE_TYPES = {'NiNode', 'BSFadeNode', 'NiBillboardNode', 'BSOrderedNode', 'BSMultiBoundNode', 'BSBlastNode', 'BSDamageStage', 'BSValueNode', 'NiSwitchNode', 'NiLODNode'}
    def tree(s, b=0, depth=0, out=None):
        if out is None: out = []
        t = s.tname(b)
        if t in s.NODE_TYPES:
            r = s.node(b); out.append((depth, b, t, r['name'], r))
            for c in r['children']:
                if c >= 0: s.tree(c, depth + 1, out)
        else:
            try:
                r, _ = s.objnet(b); nm = r['name']
            except Exception: nm = '?'
            out.append((depth, b, t, nm, None))
        return out

if __name__ == '__main__':
    n = Nif(sys.argv[1])
    print('ver', hex(n.ver), 'uver', n.uver, 'bsver', n.bsver, 'blocks', n.nblocks, n.export)
    for depth, b, t, nm, r in n.tree():
        extra = ''
        if r: extra = ' T=(%.2f,%.2f,%.2f) s=%.3f' % (*r['trans'], r['scale'])
        print('  ' * depth + f'[{b}] {t} "{nm}"' + extra)
